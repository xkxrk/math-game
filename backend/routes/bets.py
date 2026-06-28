"""用户投注采纳路由。"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

import config
import models
import prize
from database import SessionLocal

router = APIRouter(prefix="/api/bets", tags=["bets"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ------------------------------------------------------------------ #
# 采纳投注
# ------------------------------------------------------------------ #

class AdoptRequest(BaseModel):
    red_balls: list[str]  # ["01","05","12","20","30"]
    blue_balls: list[str]  # ["03","08"]
    target_issue: str = ""  # 目标期号(空=下一期)
    source: str = "manual"  # ai_predict / manual / backtest
    reason: str = ""  # 选号理由
    llm_model: str = ""  # 生成该号码时使用的模型
    note: str = ""  # 用户备注


@router.post("/adopt")
def adopt_bet(req: AdoptRequest, db: Session = Depends(get_db)):
    """采纳一组号码，记录到用户投注表。"""
    if len(req.red_balls) != 5 or len(req.blue_balls) != 2:
        raise HTTPException(400, "前区需5个号码，后区需2个号码")

    # 如果未指定目标期号，自动推断下一期
    target_issue = req.target_issue
    if not target_issue:
        latest = (
            db.query(models.LotteryRecord)
            .filter(models.LotteryRecord.lottery_type == config.LOTTERY_TYPE)
            .order_by(models.LotteryRecord.issue.desc())
            .first()
        )
        if latest:
            target_issue = str(int(latest.issue) + 1).zfill(len(latest.issue))
        else:
            target_issue = "未知"

    bet = models.UserBet(
        lottery_type=config.LOTTERY_TYPE,
        red_balls=",".join(req.red_balls),
        blue_balls=",".join(req.blue_balls),
        target_issue=target_issue,
        source=req.source,
        reason=req.reason or None,
        llm_model=req.llm_model or None,
        note=req.note or None,
        cost=prize.BET_COST,
    )
    db.add(bet)
    db.commit()
    db.refresh(bet)

    return {
        "id": bet.id,
        "message": f"已采纳号码，目标期号 {target_issue}",
        "target_issue": target_issue,
    }


# ------------------------------------------------------------------ #
# 投注列表
# ------------------------------------------------------------------ #

@router.get("")
def list_bets(
    status: str = "all",  # all / pending / evaluated
    llm_model: str = "",  # 按模型筛选
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """获取用户投注列表。"""
    q = db.query(models.UserBet).filter(
        models.UserBet.lottery_type == config.LOTTERY_TYPE
    )
    if status == "pending":
        q = q.filter(models.UserBet.evaluated == False)
    elif status == "evaluated":
        q = q.filter(models.UserBet.evaluated == True)
    if llm_model:
        q = q.filter(models.UserBet.llm_model == llm_model)
    rows = q.order_by(models.UserBet.created_at.desc()).limit(limit).all()

    return [
        {
            "id": r.id,
            "red_balls": r.red_balls.split(","),
            "blue_balls": r.blue_balls.split(","),
            "target_issue": r.target_issue,
            "source": r.source,
            "reason": r.reason,
            "note": r.note,
            "cost": r.cost,
            "llm_model": r.llm_model,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "evaluated": r.evaluated,
            "actual_red_balls": r.actual_red_balls.split(",") if r.actual_red_balls else None,
            "actual_blue_balls": r.actual_blue_balls.split(",") if r.actual_blue_balls else None,
            "red_hits": r.red_hits,
            "blue_hits": r.blue_hits,
            "prize_level": r.prize_level,
            "prize_amount": r.prize_amount,
            "prize_desc": r.prize_desc,
            "evaluated_at": r.evaluated_at.isoformat() if r.evaluated_at else None,
        }
        for r in rows
    ]


@router.get("/models")
def list_bet_models(db: Session = Depends(get_db)):
    """获取投注记录中使用过的所有模型列表（用于筛选）。"""
    rows = (
        db.query(models.UserBet.llm_model)
        .filter(
            models.UserBet.lottery_type == config.LOTTERY_TYPE,
            models.UserBet.llm_model.isnot(None),
        )
        .distinct()
        .all()
    )
    models_list = sorted({r[0] for r in rows if r[0]})
    return {"models": models_list}


# ------------------------------------------------------------------ #
# 汇总统计
# ------------------------------------------------------------------ #

@router.get("/summary")
def bets_summary(db: Session = Depends(get_db)):
    """汇总：总投注数、总花费、总中奖、净收益。"""
    rows = (
        db.query(models.UserBet)
        .filter(models.UserBet.lottery_type == config.LOTTERY_TYPE)
        .all()
    )
    total_bets = len(rows)
    total_cost = sum(r.cost for r in rows)
    total_winnings = sum(r.prize_amount for r in rows)
    evaluated_count = sum(1 for r in rows if r.evaluated)
    won_count = sum(1 for r in rows if r.prize_level and r.prize_level > 0)
    pending_count = total_bets - evaluated_count

    return {
        "total_bets": total_bets,
        "total_cost": total_cost,
        "total_winnings": total_winnings,
        "net_profit": total_winnings - total_cost,
        "evaluated_count": evaluated_count,
        "pending_count": pending_count,
        "won_count": won_count,
        "win_rate": round(won_count / evaluated_count * 100, 2) if evaluated_count else 0,
    }


# ------------------------------------------------------------------ #
# 删除投注
# ------------------------------------------------------------------ #

@router.delete("/{bet_id}")
def delete_bet(bet_id: int, db: Session = Depends(get_db)):
    """删除一条投注记录。"""
    bet = db.query(models.UserBet).filter(models.UserBet.id == bet_id).first()
    if not bet:
        raise HTTPException(404, "投注记录不存在")
    db.delete(bet)
    db.commit()
    return {"message": "已删除"}


# ------------------------------------------------------------------ #
# 手动触发评估
# ------------------------------------------------------------------ #

@router.post("/evaluate")
def evaluate_bets(db: Session = Depends(get_db)):
    """评估所有待评估的投注：查找目标期号的开奖结果，计算奖金。"""
    pending = (
        db.query(models.UserBet)
        .filter(
            models.UserBet.lottery_type == config.LOTTERY_TYPE,
            models.UserBet.evaluated == False,
        )
        .all()
    )

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
            continue  # 该期还没开奖

        actual_reds = draw.red_balls.split(",")
        actual_blues = draw.blue_balls.split(",")
        pred_reds = bet.red_balls.split(",")
        pred_blues = bet.blue_balls.split(",")

        result = prize.calc_prize(
            pred_reds,
            pred_blues,
            actual_reds,
            actual_blues,
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
        bet.evaluated_at = datetime.utcnow()
        evaluated += 1

    if evaluated:
        db.commit()

    return {
        "evaluated": evaluated,
        "pending": len(pending) - evaluated,
        "message": f"已评估 {evaluated} 条，剩余 {len(pending) - evaluated} 条待开奖",
    }
