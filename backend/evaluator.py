"""预测命中率回测评估。"""
import logging

from sqlalchemy.orm import Session

import config
import models

logger = logging.getLogger(__name__)


class Evaluator:
    """将历史预测与实际开奖对比，计算命中数。"""

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _parse_nums(s) -> set[int]:
        if not s:
            return set()
        return {int(x.strip()) for x in str(s).split(",") if x.strip().isdigit()}

    def evaluate_pending(self) -> dict:
        """评估所有未评估且已有开奖结果的预测。"""
        # 取所有未评估预测
        pending = (
            self.db.query(models.PredictionRecord)
            .filter_by(evaluated=False, lottery_type=config.LOTTERY_TYPE)
            .all()
        )
        if not pending:
            return {"evaluated": 0, "skipped": 0}

        # 构建期号 -> 开奖结果 的索引
        issues = {p.based_on_issue for p in pending if p.based_on_issue}
        draws = {}
        if issues:
            rows = (
                self.db.query(models.LotteryRecord)
                .filter(
                    models.LotteryRecord.lottery_type == config.LOTTERY_TYPE,
                    models.LotteryRecord.issue.in_(issues),
                )
                .all()
            )
            draws = {r.issue: r for r in rows}

        evaluated = 0
        skipped = 0
        for pred in pending:
            # 找到 based_on_issue 的下一期开奖作为 actual
            based = draws.get(pred.based_on_issue)
            if not based:
                skipped += 1
                continue
            # 下一期 = 期号 +1（大乐透期号连续递增）
            try:
                next_issue = str(int(based.issue) + 1)
            except (ValueError, TypeError):
                skipped += 1
                continue
            actual = (
                self.db.query(models.LotteryRecord)
                .filter_by(lottery_type=config.LOTTERY_TYPE, issue=next_issue)
                .first()
            )
            if not actual:
                skipped += 1
                continue

            pred_red = self._parse_nums(pred.red_balls)
            pred_blue = self._parse_nums(pred.blue_balls)
            act_red = self._parse_nums(actual.red_balls)
            act_blue = self._parse_nums(actual.blue_balls)

            red_hits = len(pred_red & act_red)
            blue_hits = len(pred_blue & act_blue)

            pred.evaluated = True
            pred.actual_issue = actual.issue
            pred.actual_red_balls = actual.red_balls
            pred.actual_blue_balls = actual.blue_balls
            pred.red_hits = red_hits
            pred.blue_hits = blue_hits
            pred.total_hits = red_hits + blue_hits
            evaluated += 1

        if evaluated:
            self.db.commit()
        return {"evaluated": evaluated, "skipped": skipped}

    def hit_summary(self, limit: int = 100) -> dict:
        """汇总命中率统计。"""
        rows = (
            self.db.query(models.PredictionRecord)
            .filter_by(lottery_type=config.LOTTERY_TYPE, evaluated=True)
            .order_by(models.PredictionRecord.created_at.desc())
            .limit(limit)
            .all()
        )
        if not rows:
            return {"total": 0, "avg_red": 0, "avg_blue": 0, "avg_total": 0, "best": 0}

        total = len(rows)
        avg_red = sum(r.red_hits or 0 for r in rows) / total
        avg_blue = sum(r.blue_hits or 0 for r in rows) / total
        avg_total = sum(r.total_hits or 0 for r in rows) / total
        best = max(r.total_hits or 0 for r in rows)
        return {
            "total": total,
            "avg_red": round(avg_red, 2),
            "avg_blue": round(avg_blue, 2),
            "avg_total": round(avg_total, 2),
            "best": best,
        }
