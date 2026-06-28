"""回测路由：AI 预测回测 + 固定号码长期模拟。"""

from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

import config
import models
import prize
from database import SessionLocal
from predictor import Predictor

router = APIRouter(prefix="/api/backtest", tags=["backtest"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ------------------------------------------------------------------ #
# 1. AI 预测回测
# ------------------------------------------------------------------ #

class BacktestRequest(BaseModel):
    issue: str  # 回测目标期号，如 "26070"
    count: int = 1  # 生成注数(1/3/5/10)
    models: list[str] = []  # 指定模型列表(空=用全局配置)


def _backtest_single(predictor, history, target, count, model=""):
    """对单个模型执行回测，返回结果字典。"""
    result = predictor.predict(count=count, history=history, model=model)
    meta = result.get("meta") or {}
    predictions = result.get("predictions") or []

    if not predictions:
        return {
            "model": model or meta.get("model", ""),
            "error": result.get("error", "预测生成失败"),
            "predictions": [],
            "total_winnings": 0,
            "total_cost": count * prize.BET_COST,
            "net_profit": -count * prize.BET_COST,
            "best_level": 0,
            "analysis": result.get("analysis", ""),
            "used_llm": meta.get("used_llm", False),
            "llm_model": meta.get("model"),
        }

    actual_reds = target.red_balls.split(",")
    actual_blues = target.blue_balls.split(",")

    pred_results = []
    total_winnings = 0
    best_level = 0
    for prediction in predictions:
        prize_result = prize.calc_prize(
            prediction["red_balls"],
            prediction["blue_balls"],
            actual_reds,
            actual_blues,
            target.first_prize_amount or "",
            target.second_prize_amount or "",
            target.prize_pool or "",
            issue=target.issue,
        )
        total_winnings += prize_result["amount"]
        if prize_result["level"] > 0 and (best_level == 0 or prize_result["level"] < best_level):
            best_level = prize_result["level"]
        pred_results.append({
            "red_balls": prediction["red_balls"],
            "blue_balls": prediction["blue_balls"],
            "reason": prediction.get("reason", ""),
            "prize": prize_result,
        })

    total_cost = count * prize.BET_COST
    return {
        "model": meta.get("model", model or ""),
        "predictions": pred_results,
        "best_level": best_level,
        "total_cost": total_cost,
        "total_winnings": total_winnings,
        "net_profit": total_winnings - total_cost,
        "analysis": result.get("analysis", ""),
        "used_llm": meta.get("used_llm", False),
        "llm_model": meta.get("model"),
    }


@router.post("/predict")
def backtest_predict(req: BacktestRequest, db: Session = Depends(get_db)):
    """基于选定期的历史数据生成多注预测，与该期实际开奖对比，分别计算每注奖金。

    支持多模型：传入 models 列表时返回 {multi: true, results: [...]}。
    """
    if req.count < 1 or req.count > 10:
        raise HTTPException(400, "注数需在 1-10 之间")

    # 1. 找到目标期
    target = (
        db.query(models.LotteryRecord)
        .filter(
            models.LotteryRecord.lottery_type == config.LOTTERY_TYPE,
            models.LotteryRecord.issue == req.issue,
        )
        .first()
    )
    if not target:
        raise HTTPException(404, f"期号 {req.issue} 不存在，请先抓取数据")

    # 2. 获取该期之前的所有历史(按期号降序，取最近30条)
    history = (
        db.query(models.LotteryRecord)
        .filter(
            models.LotteryRecord.lottery_type == config.LOTTERY_TYPE,
            models.LotteryRecord.issue < req.issue,
        )
        .order_by(models.LotteryRecord.issue.desc())
        .limit(50)
        .all()
    )
    if len(history) < 5:
        raise HTTPException(400, "历史数据不足，至少需要5期")

    actual_reds = target.red_balls.split(",")
    actual_blues = target.blue_balls.split(",")
    predictor = Predictor(db)

    # 多模型分支
    if len(req.models) > 1:
        results = []
        for m in req.models:
            results.append(_backtest_single(predictor, history, target, req.count, m))
        return {
            "multi": True,
            "target_issue": req.issue,
            "target_date": target.date.isoformat() if target.date else None,
            "actual_red_balls": actual_reds,
            "actual_blue_balls": actual_blues,
            "bet_count": req.count,
            "results": results,
        }

    # 单模型分支（保持向后兼容）
    single_model = req.models[0] if req.models else ""
    r = _backtest_single(predictor, history, target, req.count, single_model)
    if "error" in r:
        raise HTTPException(500, r["error"])

    return {
        "target_issue": req.issue,
        "target_date": target.date.isoformat() if target.date else None,
        "actual_red_balls": actual_reds,
        "actual_blue_balls": actual_blues,
        "bet_count": req.count,
        "predictions": r["predictions"],
        "best_level": r["best_level"],
        "total_cost": r["total_cost"],
        "total_winnings": r["total_winnings"],
        "net_profit": r["net_profit"],
        "analysis": r["analysis"],
        "used_llm": r["used_llm"],
        "llm_model": r["llm_model"],
    }


# ------------------------------------------------------------------ #
# 2. 固定号码长期购买模拟
# ------------------------------------------------------------------ #

class SimulateRequest(BaseModel):
    red_balls: list[str]  # ["01","05","12","20","30"]
    blue_balls: list[str]  # ["03","08"]
    start_issue: str = ""  # 起始期号(空=最早)
    end_issue: str = ""  # 结束期号(空=最新)


@router.post("/simulate")
def simulate_fixed(req: SimulateRequest, db: Session = Depends(get_db)):
    """模拟固定号码长期购买，统计中奖概率和收益。"""
    if len(req.red_balls) != 5 or len(req.blue_balls) != 2:
        raise HTTPException(400, "前区需5个号码，后区需2个号码")

    # 查询范围内的所有开奖记录
    q = db.query(models.LotteryRecord).filter(
        models.LotteryRecord.lottery_type == config.LOTTERY_TYPE
    )
    if req.start_issue:
        q = q.filter(models.LotteryRecord.issue >= req.start_issue)
    if req.end_issue:
        q = q.filter(models.LotteryRecord.issue <= req.end_issue)
    draws = q.order_by(models.LotteryRecord.issue.asc()).all()

    if not draws:
        raise HTTPException(404, "范围内无开奖记录")

    total_cost = 0
    total_winnings = 0
    win_count = 0
    results = []

    for draw in draws:
        total_cost += prize.BET_COST
        actual_reds = draw.red_balls.split(",")
        actual_blues = draw.blue_balls.split(",")
        p = prize.calc_prize(
            req.red_balls,
            req.blue_balls,
            actual_reds,
            actual_blues,
            draw.first_prize_amount or "",
            draw.second_prize_amount or "",
            draw.prize_pool or "",
            issue=draw.issue,
        )
        total_winnings += p["amount"]
        if p["level"] > 0:
            win_count += 1
        results.append({
            "issue": draw.issue,
            "date": draw.date.isoformat() if draw.date else None,
            "actual_red_balls": actual_reds,
            "actual_blue_balls": actual_blues,
            "red_hits": p["red_hits"],
            "blue_hits": p["blue_hits"],
            "level": p["level"],
            "desc": p["desc"],
            "amount": p["amount"],
        })

    total_bets = len(draws)
    roi = ((total_winnings - total_cost) / total_cost * 100) if total_cost else 0
    win_rate = (win_count / total_bets * 100) if total_bets else 0

    # 统计各等级中奖次数
    level_stats = {}
    for r in results:
        if r["level"] > 0:
            level_stats[r["desc"]] = level_stats.get(r["desc"], 0) + 1

    return {
        "red_balls": req.red_balls,
        "blue_balls": req.blue_balls,
        "total_bets": total_bets,
        "total_cost": total_cost,
        "total_winnings": total_winnings,
        "net_profit": total_winnings - total_cost,
        "roi": round(roi, 2),
        "win_count": win_count,
        "win_rate": round(win_rate, 2),
        "level_stats": level_stats,
        "draws": results,
        "range": {
            "start_issue": draws[0].issue,
            "end_issue": draws[-1].issue,
        },
    }


# ------------------------------------------------------------------ #
# 3. AI 预测 + 长期固定购买模拟
# ------------------------------------------------------------------ #

class AiSimulateRequest(BaseModel):
    issue: str  # AI 基于此期号之前的数据生成预测，然后从该期开始一直买到最新
    count: int = 1  # 生成注数(1/3/5/10)
    models: list[str] = []  # 指定模型列表(空=用全局配置)


def _ai_simulate_single(predictor, history, draws, count, model=""):
    """对单个模型执行 AI 长期模拟，返回结果字典。"""
    result = predictor.predict(count=count, history=history, model=model)
    meta = result.get("meta") or {}
    predictions = result.get("predictions") or []

    if not predictions:
        return {
            "model": model or meta.get("model", ""),
            "error": result.get("error", "预测生成失败"),
            "predictions": [],
            "analysis": result.get("analysis", ""),
            "simulation": None,
        }

    bet_list = [
        {
            "red_balls": p["red_balls"],
            "blue_balls": p["blue_balls"],
            "reason": p.get("reason", ""),
        }
        for p in predictions
    ]

    bet_count = len(bet_list)
    total_cost = 0
    total_winnings = 0
    win_count = 0
    sim_draws = []

    for draw in draws:
        total_cost += prize.BET_COST * bet_count
        actual_reds = draw.red_balls.split(",")
        actual_blues = draw.blue_balls.split(",")

        period_amount = 0
        period_best_level = 0
        period_best_desc = "未中奖"
        bet_details = []

        for bet in bet_list:
            p = prize.calc_prize(
                bet["red_balls"],
                bet["blue_balls"],
                actual_reds,
                actual_blues,
                draw.first_prize_amount or "",
                draw.second_prize_amount or "",
                draw.prize_pool or "",
                issue=draw.issue,
            )
            period_amount += p["amount"]
            if p["level"] > 0 and (period_best_level == 0 or p["level"] < period_best_level):
                period_best_level = p["level"]
                period_best_desc = p["desc"]
            bet_details.append({
                "red_hits": p["red_hits"],
                "blue_hits": p["blue_hits"],
                "level": p["level"],
                "desc": p["desc"],
                "amount": p["amount"],
            })

        total_winnings += period_amount
        if period_best_level > 0:
            win_count += 1

        sim_draws.append({
            "issue": draw.issue,
            "date": draw.date.isoformat() if draw.date else None,
            "actual_red_balls": actual_reds,
            "actual_blue_balls": actual_blues,
            "best_level": period_best_level,
            "best_desc": period_best_desc,
            "amount": period_amount,
            "bet_count": bet_count,
            "bet_details": bet_details,
        })

    total_bets = len(draws)
    total_bet_count = total_bets * bet_count
    roi = ((total_winnings - total_cost) / total_cost * 100) if total_cost else 0
    win_rate = (win_count / total_bets * 100) if total_bets else 0

    level_stats = {}
    for r in sim_draws:
        if r["best_level"] > 0:
            level_stats[r["best_desc"]] = level_stats.get(r["best_desc"], 0) + 1

    return {
        "model": meta.get("model", model or ""),
        "predictions": [
            {
                "red_balls": b["red_balls"],
                "blue_balls": b["blue_balls"],
                "reason": b["reason"],
                "used_llm": meta.get("used_llm", False),
                "llm_model": meta.get("model"),
            }
            for b in bet_list
        ],
        "analysis": result.get("analysis", ""),
        "simulation": {
            "total_bets": total_bets,
            "total_bet_count": total_bet_count,
            "bet_per_period": bet_count,
            "total_cost": total_cost,
            "total_winnings": total_winnings,
            "net_profit": total_winnings - total_cost,
            "roi": round(roi, 2),
            "win_count": win_count,
            "win_rate": round(win_rate, 2),
            "level_stats": level_stats,
            "draws": sim_draws,
            "range": {
                "start_issue": draws[0].issue,
                "end_issue": draws[-1].issue,
            },
        },
    }


@router.post("/ai-simulate")
def ai_simulate(req: AiSimulateRequest, db: Session = Depends(get_db)):
    """AI 基于指定期号前的历史生成多注号码，然后用这些号码从该期一直买到最新。

    每期购买全部 count 注，总成本 = count × 2 × 期数。
    支持多模型：传入 models 列表时返回 {multi: true, results: [...]}。
    """
    if req.count < 1 or req.count > 10:
        raise HTTPException(400, "注数需在 1-10 之间")

    # 1. 找到起始期
    start = (
        db.query(models.LotteryRecord)
        .filter(
            models.LotteryRecord.lottery_type == config.LOTTERY_TYPE,
            models.LotteryRecord.issue == req.issue,
        )
        .first()
    )
    if not start:
        raise HTTPException(404, f"期号 {req.issue} 不存在")

    # 2. 获取该期之前的历史(取最近50条)
    history = (
        db.query(models.LotteryRecord)
        .filter(
            models.LotteryRecord.lottery_type == config.LOTTERY_TYPE,
            models.LotteryRecord.issue < req.issue,
        )
        .order_by(models.LotteryRecord.issue.desc())
        .limit(50)
        .all()
    )
    if len(history) < 5:
        raise HTTPException(400, "历史数据不足，至少需要5期")

    # 3. 获取模拟范围的开奖记录
    draws = (
        db.query(models.LotteryRecord)
        .filter(
            models.LotteryRecord.lottery_type == config.LOTTERY_TYPE,
            models.LotteryRecord.issue >= req.issue,
        )
        .order_by(models.LotteryRecord.issue.asc())
        .all()
    )
    if not draws:
        raise HTTPException(404, "范围内无开奖记录")

    predictor = Predictor(db)

    # 多模型分支
    if len(req.models) > 1:
        results = []
        for m in req.models:
            results.append(_ai_simulate_single(predictor, history, draws, req.count, m))
        return {
            "multi": True,
            "start_issue": req.issue,
            "results": results,
        }

    # 单模型分支（保持向后兼容）
    single_model = req.models[0] if req.models else ""
    r = _ai_simulate_single(predictor, history, draws, req.count, single_model)
    if "error" in r:
        raise HTTPException(500, r["error"])

    return {
        "start_issue": req.issue,
        "bet_count": r["simulation"]["bet_per_period"],
        "predictions": r["predictions"],
        "analysis": r["analysis"],
        "simulation": r["simulation"],
    }


# ------------------------------------------------------------------ #
# 4. 可用期号列表(供前端下拉选择)
# ------------------------------------------------------------------ #

@router.get("/issues")
def list_issues(limit: int = 100, db: Session = Depends(get_db)):
    """返回可用期号列表，供回测选择。"""
    rows = (
        db.query(models.LotteryRecord)
        .filter(models.LotteryRecord.lottery_type == config.LOTTERY_TYPE)
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
        }
        for r in rows
    ]
