"""预测相关路由。"""
import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

import config
import models
from database import get_db
from predictor import Predictor
from evaluator import Evaluator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["predict"])


@router.post("/predict")
def predict(
    count: int = Query(1, ge=1, le=10),
    db: Session = Depends(get_db),
):
    """生成预测并持久化。"""
    predictor = Predictor(db)
    result = predictor.predict(count=count)

    if "error" in result:
        return result

    # 持久化预测记录
    latest = (
        db.query(models.LotteryRecord)
        .filter_by(lottery_type=config.LOTTERY_TYPE)
        .order_by(models.LotteryRecord.issue.desc())
        .first()
    )
    based_on = latest.issue if latest else ""
    meta = result.get("meta") or {}
    used_llm = meta.get("used_llm", False)

    # 清除同一期未评估的旧预测，避免唯一约束冲突
    db.query(models.PredictionRecord).filter(
        models.PredictionRecord.lottery_type == config.LOTTERY_TYPE,
        models.PredictionRecord.based_on_issue == based_on,
        models.PredictionRecord.evaluated == False,
    ).delete()
    db.commit()

    saved = []
    for idx, p in enumerate(result.get("predictions", [])):
        rec = models.PredictionRecord(
            lottery_type=config.LOTTERY_TYPE,
            based_on_issue=based_on,
            sequence=idx,
            red_balls=",".join(p.get("red_balls", [])),
            blue_balls=",".join(p.get("blue_balls", [])),
            used_llm=used_llm,
            llm_model=meta.get("model"),
            llm_latency_ms=meta.get("latency_ms"),
        )
        db.add(rec)
        saved.append(
            {
                "red_balls": p.get("red_balls", []),
                "blue_balls": p.get("blue_balls", []),
                "reason": p.get("reason", ""),
                "based_on_issue": based_on,
                "sequence": idx,
                "used_llm": used_llm,
                "llm_model": meta.get("model"),
            }
        )
    db.commit()

    # 尝试评估历史预测
    evaluator = Evaluator(db)
    evaluator.evaluate_pending()

    return {
        "analysis": result.get("analysis", ""),
        "predictions": saved,
        "meta": meta,
        "based_on_issue": based_on,
    }


@router.get("/predictions")
def list_predictions(
    limit: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """获取历史预测记录。"""
    rows = (
        db.query(models.PredictionRecord)
        .filter_by(lottery_type=config.LOTTERY_TYPE)
        .order_by(models.PredictionRecord.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "based_on_issue": r.based_on_issue,
            "red_balls": (r.red_balls or "").split(",") if r.red_balls else [],
            "blue_balls": (r.blue_balls or "").split(",") if r.blue_balls else [],
            "used_llm": r.used_llm,
            "llm_model": r.llm_model,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "evaluated": r.evaluated,
            "actual_issue": r.actual_issue,
            "actual_red_balls": (r.actual_red_balls or "").split(",") if r.actual_red_balls else [],
            "actual_blue_balls": (r.actual_blue_balls or "").split(",") if r.actual_blue_balls else [],
            "red_hits": r.red_hits,
            "blue_hits": r.blue_hits,
            "total_hits": r.total_hits,
        }
        for r in rows
    ]


@router.post("/evaluate")
def evaluate(db: Session = Depends(get_db)):
    """手动触发回测评估。"""
    evaluator = Evaluator(db)
    return evaluator.evaluate_pending()
