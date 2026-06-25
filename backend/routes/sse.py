"""SSE 实时推送：开奖/预测更新通知 + 遗漏预警。"""
import asyncio
import datetime as _dt
import json
import logging

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse, JSONResponse

import analyzer
import config
import models
import prize
from database import SessionLocal

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["sse"])

# 简易事件总线：所有连接共享
_subscribers: set[asyncio.Queue] = set()


def broadcast(event: str, data: dict):
    """向所有 SSE 订阅者推送事件。"""
    message = json.dumps({"event": event, "data": data}, ensure_ascii=False)
    for q in list(_subscribers):
        try:
            q.put_nowait(message)
        except asyncio.QueueFull:
            pass


@router.get("/stream")
async def sse_stream(request: Request):
    """SSE 端点。"""
    queue: asyncio.Queue = asyncio.Queue(maxsize=64)
    _subscribers.add(queue)

    async def event_generator():
        try:
            # 首条 hello
            yield f"data: {json.dumps({'event': 'connected', 'data': {'ok': True}})}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=15)
                    yield f"data: {message}\n\n"
                except asyncio.TimeoutError:
                    # 心跳
                    yield f"data: {json.dumps({'event': 'ping', 'data': {}})}\n\n"
        finally:
            _subscribers.discard(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ------------------------------------------------------------------ #
# 遗漏预警实时推送
# ------------------------------------------------------------------ #

# 预警阈值：前区遗漏≥15期、后区遗漏≥10期进入预警列表
HIGH_MISS_RED_THRESHOLD = 15
HIGH_MISS_BLUE_THRESHOLD = 10
# 推送间隔（秒）
ALERT_PUSH_INTERVAL = 30


def _load_records_for_alerts(db, limit: int = 200):
    """加载历史记录（升序，旧→新），用于遗漏值计算。"""
    return (
        db.query(models.LotteryRecord)
        .filter(models.LotteryRecord.lottery_type == config.LOTTERY_TYPE)
        .order_by(models.LotteryRecord.issue.asc())
        .limit(limit)
        .all()
    )


def _build_alert_payload(db) -> dict:
    """构建一次预警快照 payload。

    返回结构:
    {
        "timestamp": "2026-06-25T15:30:00",
        "high_miss_red": [{"number": 5, "miss": 32}, ...],   # 前区遗漏≥15期
        "high_miss_blue": [{"number": 8, "miss": 25}, ...],  # 后区遗漏≥10期
        "pool_status": {
            "current_pool": 802000000,
            "is_high_pool": true,
            "threshold": 800000000,
            "message": "奖池8.02亿，已达8亿阈值，固定奖金上浮"
        },
        "latest_issue": "26070"
    }
    """
    records = _load_records_for_alerts(db, limit=200)

    # 无数据时返回空快照
    if not records:
        return {
            "timestamp": _dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "high_miss_red": [],
            "high_miss_blue": [],
            "pool_status": {
                "current_pool": None,
                "is_high_pool": False,
                "threshold": prize.HIGH_POOL_THRESHOLD,
                "message": "暂无历史数据",
            },
            "latest_issue": None,
        }

    # 遗漏值（miss_values 返回 {"05": 期数} 形式）
    red_miss = analyzer.miss_values(records, "red")
    blue_miss = analyzer.miss_values(records, "blue")

    # 筛选高遗漏号码并按遗漏值降序
    high_miss_red = sorted(
        ({"number": int(num), "miss": m} for num, m in red_miss.items()
         if m >= HIGH_MISS_RED_THRESHOLD),
        key=lambda x: x["miss"], reverse=True,
    )
    high_miss_blue = sorted(
        ({"number": int(num), "miss": m} for num, m in blue_miss.items()
         if m >= HIGH_MISS_BLUE_THRESHOLD),
        key=lambda x: x["miss"], reverse=True,
    )

    # 奖池状态：取最新一期的 prize_pool
    latest = records[-1]
    latest_issue = latest.issue
    current_pool = analyzer._parse_amount(latest.prize_pool)

    is_high_pool = (
        current_pool is not None
        and current_pool >= prize.HIGH_POOL_THRESHOLD
    )
    threshold = prize.HIGH_POOL_THRESHOLD

    if current_pool is not None:
        pool_yi = current_pool / 1_0000_0000
        if is_high_pool:
            message = f"奖池{pool_yi:.2f}亿，已达8亿阈值，固定奖金上浮"
        else:
            remain = (threshold - current_pool) / 1_0000_0000
            message = f"奖池{pool_yi:.2f}亿，距8亿阈值还有{remain:.2f}亿"
    else:
        message = "暂无奖池数据"

    return {
        "timestamp": _dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "high_miss_red": high_miss_red,
        "high_miss_blue": high_miss_blue,
        "pool_status": {
            "current_pool": current_pool,
            "is_high_pool": is_high_pool,
            "threshold": threshold,
            "message": message,
        },
        "latest_issue": latest_issue,
    }


@router.get("/sse/alerts")
async def sse_alerts(request: Request):
    """遗漏预警实时推送端点。

    客户端连接时立即推送一次预警快照，之后每隔 30 秒推送一次最新预警。
    每条消息格式: ``data: {payload_json}\\n\\n``
    """
    async def event_generator():
        try:
            # 连接时立即推送一次当前预警快照
            with SessionLocal() as db:
                yield f"data: {json.dumps(_build_alert_payload(db), ensure_ascii=False)}\n\n"

            # 之后每隔 30 秒推送一次
            while True:
                # 等待前先检查客户端是否已断开
                if await request.is_disconnected():
                    break
                await asyncio.sleep(ALERT_PUSH_INTERVAL)
                # 推送前再次检查，避免向已断开连接写入
                if await request.is_disconnected():
                    break
                with SessionLocal() as db:
                    payload = _build_alert_payload(db)
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
        except asyncio.CancelledError:
            # 客户端断开导致任务取消
            raise
        except Exception:
            # 其他异常退出循环，避免空响应
            logger.exception("SSE alerts 推送异常，退出循环")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/sse/alerts/snapshot")
def alerts_snapshot():
    """预警快照（一次性，非流式）：供前端在 SSE 不可用时降级取数。"""
    with SessionLocal() as db:
        return _build_alert_payload(db)
