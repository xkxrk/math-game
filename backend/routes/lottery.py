"""开奖数据相关路由：历史列表 / 统计 / 手动抓取。"""
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

import config
import models
from database import get_db
from scraper import DltScraper
from evaluator import Evaluator

router = APIRouter(prefix="/api", tags=["lottery"])


@router.get("/history")
def get_history(
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """获取历史开奖记录（按期号倒序）。"""
    rows = (
        db.query(models.LotteryRecord)
        .filter_by(lottery_type=config.LOTTERY_TYPE)
        .order_by(models.LotteryRecord.issue.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "issue": r.issue,
            "date": r.date.isoformat() if r.date else None,
            "red_balls": r.red_balls,
            "blue_balls": r.blue_balls,
            "sales": r.sales,
            "prize_pool": r.prize_pool,
            "first_prize_count": r.first_prize_count,
            "first_prize_amount": r.first_prize_amount,
            "second_prize_count": r.second_prize_count,
            "second_prize_amount": r.second_prize_amount,
        }
        for r in rows
    ]


@router.get("/latest")
def get_latest(db: Session = Depends(get_db)):
    """获取最新一期开奖。"""
    r = (
        db.query(models.LotteryRecord)
        .filter_by(lottery_type=config.LOTTERY_TYPE)
        .order_by(models.LotteryRecord.issue.desc())
        .first()
    )
    if not r:
        return {"issue": None}
    return {
        "issue": r.issue,
        "date": r.date.isoformat() if r.date else None,
        "red_balls": r.red_balls,
        "blue_balls": r.blue_balls,
    }


@router.get("/stats")
def get_stats(
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """号码频率统计 + 命中率汇总。"""
    rows = (
        db.query(models.LotteryRecord)
        .filter_by(lottery_type=config.LOTTERY_TYPE)
        .order_by(models.LotteryRecord.issue.desc())
        .limit(limit)
        .all()
    )

    red_freq = {i: 0 for i in range(1, config.RED_MAX + 1)}
    blue_freq = {i: 0 for i in range(1, config.BLUE_MAX + 1)}
    for r in rows:
        for n in _parse(r.red_balls):
            if 1 <= n <= config.RED_MAX:
                red_freq[n] += 1
        for n in _parse(r.blue_balls):
            if 1 <= n <= config.BLUE_MAX:
                blue_freq[n] += 1

    red_list = [
        {"num": f"{k:02d}", "count": v}
        for k, v in sorted(red_freq.items(), key=lambda x: x[1], reverse=True)
    ]
    blue_list = [
        {"num": f"{k:02d}", "count": v}
        for k, v in sorted(blue_freq.items(), key=lambda x: x[1], reverse=True)
    ]

    evaluator = Evaluator(db)
    hit = evaluator.hit_summary()

    return {
        "red_frequency": red_list,
        "blue_frequency": blue_list,
        "total_draws": len(rows),
        "hit_summary": hit,
    }


@router.post("/scrape")
def trigger_scrape(
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """手动触发抓取。"""
    scraper = DltScraper(db)
    result = scraper.scrape(limit=limit, upsert=True)
    # 抓取后顺便评估
    evaluator = Evaluator(db)
    eva = evaluator.evaluate_pending()
    return {"scrape": result, "evaluate": eva, "time": datetime.now().isoformat()}


def _parse(s) -> list[int]:
    if not s:
        return []
    return [int(x.strip()) for x in str(s).split(",") if x.strip().isdigit()]
