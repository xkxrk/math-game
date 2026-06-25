"""号码分析路由：组合诊断 + 历史规律可视化数据。"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

import analyzer
import config
import models
from database import SessionLocal

router = APIRouter(prefix="/api/analyze", tags=["analyze"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _load_records(db: Session, limit: int = 200):
    """加载历史记录（升序，旧→新）。"""
    rows = (
        db.query(models.LotteryRecord)
        .filter(models.LotteryRecord.lottery_type == config.LOTTERY_TYPE)
        .order_by(models.LotteryRecord.issue.asc())
        .limit(limit)
        .all()
    )
    if not rows:
        raise HTTPException(404, "无历史数据，请先抓取")
    return rows


# ------------------------------------------------------------------ #
# 1. 号码组合诊断器
# ------------------------------------------------------------------ #

class ComboDiagnoseRequest(BaseModel):
    red_balls: list[str]  # ["01","05","12","20","30"]
    blue_balls: list[str]  # ["03","08"]


@router.post("/combo")
def diagnose_combo(req: ComboDiagnoseRequest, db: Session = Depends(get_db)):
    """号码组合体检报告：形态指标 + 历史分位 + 评分 + 提示。"""
    if len(req.red_balls) != 5 or len(req.blue_balls) != 2:
        raise HTTPException(400, "前区需5个号码，后区需2个号码")

    records = _load_records(db, limit=200)
    prev_reds = None
    if records:
        prev_reds = records[-1].red_balls.split(",")

    return analyzer.diagnose_combo(req.red_balls, req.blue_balls, records, prev_reds)


# ------------------------------------------------------------------ #
# 2. 遗漏值排行
# ------------------------------------------------------------------ #

@router.get("/miss")
def miss_ranking(num_type: str = "red", limit: int = 200, db: Session = Depends(get_db)):
    """号码遗漏值排行（按遗漏期数降序）。"""
    if num_type not in ("red", "blue"):
        raise HTTPException(400, "num_type 必须为 red 或 blue")

    records = _load_records(db, limit=limit)
    miss = analyzer.miss_values(records, num_type)
    # 排序
    result = [{"num": k, "miss": v} for k, v in miss.items()]
    result.sort(key=lambda x: x["miss"], reverse=True)
    return {
        "num_type": num_type,
        "total_draws": len(records),
        "ranking": result,
    }


# ------------------------------------------------------------------ #
# 3. 号码频率统计（含遗漏值合并展示）
# ------------------------------------------------------------------ #

@router.get("/frequency")
def frequency(num_type: str = "red", limit: int = 200, db: Session = Depends(get_db)):
    """号码频率 + 遗漏值合并统计。"""
    if num_type not in ("red", "blue"):
        raise HTTPException(400, "num_type 必须为 red 或 blue")

    records = _load_records(db, limit=limit)
    freq = analyzer.frequency_stats(records, num_type)
    miss = analyzer.miss_values(records, num_type)
    # 合并
    for item in freq:
        item["miss"] = miss.get(item["num"], 0)
    return {
        "num_type": num_type,
        "total_draws": len(records),
        "stats": freq,
    }


# ------------------------------------------------------------------ #
# 4. 和值分布
# ------------------------------------------------------------------ #

@router.get("/sum-distribution")
def sum_dist(limit: int = 200, db: Session = Depends(get_db)):
    """前区和值历史分布。"""
    records = _load_records(db, limit=limit)
    return analyzer.sum_distribution(records)


# ------------------------------------------------------------------ #
# 5. 奇偶/大小比分布
# ------------------------------------------------------------------ #

@router.get("/ratio")
def ratio_dist(ratio_type: str = "odd_even", limit: int = 200, db: Session = Depends(get_db)):
    """奇偶比或大小比历史分布。"""
    if ratio_type not in ("odd_even", "big_small"):
        raise HTTPException(400, "ratio_type 必须为 odd_even 或 big_small")

    records = _load_records(db, limit=limit)
    dist = analyzer.ratio_distribution(records, ratio_type)
    # 按次数降序排序
    sorted_dist = sorted(dist.items(), key=lambda x: x[1], reverse=True)
    return {
        "ratio_type": ratio_type,
        "total_draws": len(records),
        "distribution": [{"ratio": k, "count": v} for k, v in sorted_dist],
    }


# ------------------------------------------------------------------ #
# 6. 跨度分布
# ------------------------------------------------------------------ #

@router.get("/span")
def span_dist(limit: int = 200, db: Session = Depends(get_db)):
    """跨度分布。"""
    records = _load_records(db, limit=limit)
    return analyzer.span_distribution(records)


# ------------------------------------------------------------------ #
# 7. 奖池趋势
# ------------------------------------------------------------------ #

@router.get("/pool-trend")
def pool_trend(limit: int = 100, db: Session = Depends(get_db)):
    """奖池金额趋势（按期号升序）。"""
    records = _load_records(db, limit=limit)
    trend = analyzer.pool_trend(records)
    # 过滤 None
    valid = [t for t in trend if t["pool"] is not None]
    return {
        "total": len(trend),
        "valid_count": len(valid),
        "trend": trend,
    }


# ------------------------------------------------------------------ #
# 8. 综合仪表盘（一次性返回所有分析数据）
# ------------------------------------------------------------------ #

@router.get("/dashboard")
def dashboard(limit: int = 200, db: Session = Depends(get_db)):
    """综合分析仪表盘：遗漏值/频率/和值/奇偶/大小/跨度/奖池趋势。"""
    records = _load_records(db, limit=limit)
    prev_reds = records[-1].red_balls.split(",") if records else None

    return {
        "total_draws": len(records),
        "red_miss": analyzer.miss_values(records, "red"),
        "blue_miss": analyzer.miss_values(records, "blue"),
        "red_frequency": analyzer.frequency_stats(records, "red"),
        "blue_frequency": analyzer.frequency_stats(records, "blue"),
        "sum_distribution": analyzer.sum_distribution(records),
        "odd_even_distribution": analyzer.ratio_distribution(records, "odd_even"),
        "big_small_distribution": analyzer.ratio_distribution(records, "big_small"),
        "span_distribution": analyzer.span_distribution(records),
        "pool_trend": analyzer.pool_trend(records),
    }


# ================================================================== #
# 9. 奖金期望值计算器（#9）
# ================================================================== #

@router.get("/expected-value")
def expected_value_route(limit: int = 100, db: Session = Depends(get_db)):
    """奖金期望值：一等奖单注期望 = 当前奖池 / 总组合数。"""
    return analyzer.expected_value(db, config.LOTTERY_TYPE, limit=limit)


# ================================================================== #
# 10. 回测策略对比（#5）
# ================================================================== #

@router.get("/strategy-compare")
def strategy_compare_route(limit: int = 100, db: Session = Depends(get_db)):
    """4 种策略(热号/冷号/随机/均衡)在最近 limit 期上的命中率/ROI 对比。"""
    return analyzer.strategy_compare(db, config.LOTTERY_TYPE, limit=limit)


# ================================================================== #
# 11. 历史复盘工具（#7）
# ================================================================== #

@router.get("/review/issues")
def review_issues(limit: int = 50, db: Session = Depends(get_db)):
    """返回最近 limit 期列表（仅 issue + date，不含开奖号码，供复盘选期）。"""
    rows = (
        db.query(models.LotteryRecord)
        .filter(models.LotteryRecord.lottery_type == config.LOTTERY_TYPE)
        .order_by(models.LotteryRecord.issue.desc())
        .limit(limit)
        .all()
    )
    return [
        {"issue": r.issue, "date": r.date.isoformat() if r.date else None}
        for r in rows
    ]


class ReviewRevealRequest(BaseModel):
    issue: str


@router.post("/review/reveal")
def review_reveal(req: ReviewRevealRequest, db: Session = Depends(get_db)):
    """揭晓指定期号完整开奖信息 + 形态统计。"""
    rec = (
        db.query(models.LotteryRecord)
        .filter(
            models.LotteryRecord.lottery_type == config.LOTTERY_TYPE,
            models.LotteryRecord.issue == req.issue,
        )
        .first()
    )
    if not rec:
        raise HTTPException(404, f"期号 {req.issue} 不存在")

    reds = rec.red_balls.split(",")
    blues = rec.blue_balls.split(",")
    stats = analyzer.combo_stats(reds, blues)
    return {
        "issue": rec.issue,
        "date": rec.date.isoformat() if rec.date else None,
        "red_balls": reds,
        "blue_balls": blues,
        "prize_pool": rec.prize_pool,
        "first_prize_amount": rec.first_prize_amount,
        "second_prize_amount": rec.second_prize_amount,
        "stats": stats,
    }


class ReviewScoreRequest(BaseModel):
    issue: str
    red_balls: list[str]
    blue_balls: list[str]


@router.post("/review/score")
def review_score(req: ReviewScoreRequest, db: Session = Depends(get_db)):
    """对比用户号码与实际开奖，返回命中/形态对比/综合评分。"""
    if len(req.red_balls) != 5 or len(req.blue_balls) != 2:
        raise HTTPException(400, "前区需5个号码，后区需2个号码")

    rec = (
        db.query(models.LotteryRecord)
        .filter(
            models.LotteryRecord.lottery_type == config.LOTTERY_TYPE,
            models.LotteryRecord.issue == req.issue,
        )
        .first()
    )
    if not rec:
        raise HTTPException(404, f"期号 {req.issue} 不存在")

    return analyzer.review_score(rec, req.red_balls, req.blue_balls)


# ================================================================== #
# 12. 自定义策略沙盒（#8）
# ================================================================== #

class SandboxRules(BaseModel):
    sum_min: int = 0
    sum_max: int = 999
    odd_even: list[str] = []
    big_small: list[str] = []
    span_min: int = 0
    span_max: int = 999
    consecutive: bool = True
    combo_count: int = 5


@router.post("/sandbox")
def sandbox_simulate(req: SandboxRules, limit: int = 100, db: Session = Depends(get_db)):
    """自定义策略沙盒：按规则生成多注号码并模拟购买统计。"""
    rules_dict = req.model_dump()
    # 空列表视为不限制
    if not rules_dict["odd_even"]:
        rules_dict["odd_even"] = ["5:0", "4:1", "3:2", "2:3", "1:4", "0:5"]
    if not rules_dict["big_small"]:
        rules_dict["big_small"] = ["5:0", "4:1", "3:2", "2:3", "1:4", "0:5"]
    return analyzer.sandbox_simulate(db, config.LOTTERY_TYPE, rules_dict, limit=limit)
