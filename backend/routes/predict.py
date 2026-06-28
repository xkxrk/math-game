"""预测相关路由。"""
import logging

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

import config
import models
from database import get_db
from predictor import Predictor
from evaluator import Evaluator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["predict"])


def _persist_predictions(db: Session, based_on: str, predictions: list, meta: dict, seq_offset: int = 0) -> list:
    """持久化预测记录，返回前端展示用的列表。

    Args:
        seq_offset: 序号偏移量（多模型时用于避免唯一约束冲突，每个模型用 100 的倍数）
    """
    used_llm = meta.get("used_llm", False)
    saved = []
    for idx, p in enumerate(predictions):
        seq = seq_offset + idx
        rec = models.PredictionRecord(
            lottery_type=config.LOTTERY_TYPE,
            based_on_issue=based_on,
            sequence=seq,
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
                "sequence": seq,
                "used_llm": used_llm,
                "llm_model": meta.get("model"),
            }
        )
    db.commit()
    return saved


@router.post("/predict")
def predict(
    count: int = Query(1, ge=1, le=10),
    model_names: str = Query("", alias="models", description="逗号分隔的模型列表，空则用全局配置"),
    db: Session = Depends(get_db),
):
    """生成预测并持久化。支持单/多模型。

    返回结构：
    - 单模型（或未指定）：保持原结构 {analysis, predictions, meta, based_on_issue}
    - 多模型：{multi: true, results: [{model, analysis, predictions, meta, based_on_issue, error?}]}
    """
    # 解析模型列表
    model_list = [m.strip() for m in model_names.split(",") if m.strip()] if model_names else []

    predictor = Predictor(db)

    # 获取最新期号作为 based_on
    latest = (
        db.query(models.LotteryRecord)
        .filter_by(lottery_type=config.LOTTERY_TYPE)
        .order_by(models.LotteryRecord.issue.desc())
        .first()
    )
    based_on = latest.issue if latest else ""

    # 多模型分支
    if len(model_list) > 1:
        # 清除同一期未评估的旧预测，避免唯一约束冲突
        db.query(models.PredictionRecord).filter(
            models.PredictionRecord.lottery_type == config.LOTTERY_TYPE,
            models.PredictionRecord.based_on_issue == based_on,
            models.PredictionRecord.evaluated == False,
        ).delete()
        db.commit()

        results = []
        for m_idx, m in enumerate(model_list):
            try:
                result = predictor.predict(count=count, model=m)
            except Exception as e:
                logger.error(f"模型 {m} 预测异常: {e}")
                results.append({
                    "model": m,
                    "error": f"预测失败: {e}",
                    "analysis": "",
                    "predictions": [],
                    "meta": {"used_llm": False, "model": m},
                    "based_on_issue": based_on,
                })
                continue

            if "error" in result:
                results.append({
                    "model": m,
                    "error": result["error"],
                    "analysis": "",
                    "predictions": [],
                    "meta": result.get("meta") or {"used_llm": False, "model": m},
                    "based_on_issue": based_on,
                })
                continue

            meta = result.get("meta") or {"used_llm": False, "model": m}
            # 多模型时用偏移量避免 sequence 唯一约束冲突
            saved = _persist_predictions(db, based_on, result.get("predictions", []), meta, seq_offset=m_idx * 100)
            results.append({
                "model": m,
                "analysis": result.get("analysis", ""),
                "predictions": saved,
                "meta": meta,
                "based_on_issue": based_on,
            })

        # 尝试评估历史预测
        evaluator = Evaluator(db)
        evaluator.evaluate_pending()

        return {"multi": True, "results": results, "based_on_issue": based_on}

    # 单模型分支（保持向后兼容）
    single_model = model_list[0] if model_list else ""
    result = predictor.predict(count=count, model=single_model)

    if "error" in result:
        return result

    meta = result.get("meta") or {}

    # 清除同一期未评估的旧预测，避免唯一约束冲突
    db.query(models.PredictionRecord).filter(
        models.PredictionRecord.lottery_type == config.LOTTERY_TYPE,
        models.PredictionRecord.based_on_issue == based_on,
        models.PredictionRecord.evaluated == False,
    ).delete()
    db.commit()

    saved = _persist_predictions(db, based_on, result.get("predictions", []), meta)

    # 尝试评估历史预测
    evaluator = Evaluator(db)
    evaluator.evaluate_pending()

    return {
        "analysis": result.get("analysis", ""),
        "predictions": saved,
        "meta": meta,
        "based_on_issue": based_on,
    }


class RankItem(BaseModel):
    red_balls: list[str] = []
    blue_balls: list[str] = []
    reason: str = ""
    source_model: str = ""


class RankRequest(BaseModel):
    model: str
    predictions: list[RankItem]


@router.post("/predict/rank")
def predict_rank(req: RankRequest, db: Session = Depends(get_db)):
    """二次预测排序：让指定模型对所有候选号码组合打分排序。

    返回 {ranking: [{index, score, comment}, ...], model} 按推荐度降序。
    """
    predictor = Predictor(db)
    preds = [p.model_dump() for p in req.predictions]
    return predictor.rank_predictions(preds, req.model)


@router.get("/predictions")
def list_predictions(
    limit: int = Query(20, ge=1, le=200),
    llm_model: str = Query("", description="按模型筛选"),
    db: Session = Depends(get_db),
):
    """获取历史预测记录，可按模型筛选。"""
    q = db.query(models.PredictionRecord).filter_by(lottery_type=config.LOTTERY_TYPE)
    if llm_model:
        q = q.filter(models.PredictionRecord.llm_model == llm_model)
    rows = q.order_by(models.PredictionRecord.created_at.desc()).limit(limit).all()
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


@router.get("/predictions/models")
def list_prediction_models(db: Session = Depends(get_db)):
    """获取预测记录中使用过的所有模型列表（用于筛选）。"""
    rows = (
        db.query(models.PredictionRecord.llm_model)
        .filter(
            models.PredictionRecord.lottery_type == config.LOTTERY_TYPE,
            models.PredictionRecord.llm_model.isnot(None),
        )
        .distinct()
        .all()
    )
    models_list = sorted({r[0] for r in rows if r[0]})
    return {"models": models_list}


@router.post("/evaluate")
def evaluate(db: Session = Depends(get_db)):
    """手动触发回测评估。"""
    evaluator = Evaluator(db)
    return evaluator.evaluate_pending()
