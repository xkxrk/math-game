"""后台定时任务：自动抓取 + 回测评估。"""
import logging
import threading
from datetime import datetime, timedelta

from database import SessionLocal
from scraper import DltScraper
from evaluator import Evaluator
import config

logger = logging.getLogger(__name__)

# 全局定时器引用
_timer: threading.Timer | None = None
_lock = threading.RLock()


def _next_draw_time(now: datetime) -> datetime:
    """计算下一次大乐透开奖时间（周一/三/六 21:30）。"""
    base = now.replace(hour=21, minute=30, second=0, microsecond=0)
    # 如果今天开奖且还没到 21:30，就是今天
    if now.weekday() in config.DRAW_WEEKDAYS and now < base:
        return base
    # 否则找下一个开奖日
    delta = 1
    while True:
        candidate = base + timedelta(days=delta)
        if candidate.weekday() in config.DRAW_WEEKDAYS:
            return candidate
        delta += 1


def _evaluate_user_bets(db):
    """自动评估用户采纳的投注。"""
    import models
    import prize
    from datetime import datetime as dt

    pending = (
        db.query(models.UserBet)
        .filter(
            models.UserBet.lottery_type == config.LOTTERY_TYPE,
            models.UserBet.evaluated == False,
        )
        .all()
    )
    if not pending:
        return

    evaluated = 0
    for bet in pending:
        draw = (
            db.query(models.LotteryRecord)
            .filter(
                models.LotteryRecord.lottery_type == config.LOTTERY_TYPE,
                models.LotteryRecord.issue == bet.target_issue,
            )
            .first()
        )
        if not draw:
            continue

        result = prize.calc_prize(
            bet.red_balls.split(","),
            bet.blue_balls.split(","),
            draw.red_balls.split(","),
            draw.blue_balls.split(","),
            draw.first_prize_amount or "",
            draw.second_prize_amount or "",
            draw.prize_pool or "",
            issue=draw.issue,
        )
        bet.evaluated = True
        bet.actual_red_balls = draw.red_balls
        bet.actual_blue_balls = draw.blue_balls
        bet.red_hits = result["red_hits"]
        bet.blue_hits = result["blue_hits"]
        bet.prize_level = result["level"]
        bet.prize_amount = result["amount"]
        bet.prize_desc = result["desc"]
        bet.evaluated_at = dt.utcnow()
        evaluated += 1

    if evaluated:
        db.commit()
        logger.info(f"用户投注自动评估: {evaluated} 条")


def _run_once():
    """执行一次抓取 + 评估。"""
    db = SessionLocal()
    try:
        scraper = DltScraper(db)
        result = scraper.scrape(limit=200, upsert=True)
        logger.info(f"定时抓取完成: {result}")

        evaluator = Evaluator(db)
        eva = evaluator.evaluate_pending()
        logger.info(f"定时回测完成: {eva}")

        # 自动评估用户采纳的投注
        _evaluate_user_bets(db)
    except Exception as e:
        logger.error(f"定时任务异常: {e}")
    finally:
        db.close()


def _schedule_loop():
    """计算下次执行时间并设定时器。"""
    global _timer
    now = datetime.now()
    next_run = _next_draw_time(now)
    # 开奖后 10 分钟再抓（确保数据已更新）
    next_run = next_run + timedelta(minutes=10)
    delay = (next_run - now).total_seconds()
    if delay < 60:
        delay = 60  # 至少 1 分钟后执行

    logger.info(f"下次定时任务: {next_run.strftime('%Y-%m-%d %H:%M:%S')}（{int(delay)}s 后）")

    def _fire():
        _run_once()
        # 重新调度
        with _lock:
            _schedule_loop()

    with _lock:
        _timer = threading.Timer(delay, _fire)
        _timer.daemon = True
        _timer.start()


def start_scheduler():
    """启动定时调度。"""
    with _lock:
        if _timer is not None:
            logger.info("定时任务已在运行，跳过")
            return
        logger.info("启动定时调度...")
        _schedule_loop()


def stop_scheduler():
    """停止定时调度。"""
    global _timer
    with _lock:
        if _timer:
            _timer.cancel()
            _timer = None
            logger.info("定时调度已停止")
