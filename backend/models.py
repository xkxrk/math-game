"""SQLAlchemy 数据模型。"""
from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Date,
    DateTime,
    Text,
    Boolean,
    UniqueConstraint,
)

from database import Base


class LotteryRecord(Base):
    """开奖历史记录。"""

    __tablename__ = "lottery_records"
    __table_args__ = (
        UniqueConstraint("lottery_type", "issue", name="uix_lottery_type_issue"),
    )

    id = Column(Integer, primary_key=True, index=True)
    lottery_type = Column(String, index=True)  # 'dlt'
    issue = Column(String, index=True)  # 期号
    date = Column(Date)  # 开奖日期
    red_balls = Column(String)  # 前区，逗号分隔
    blue_balls = Column(String)  # 后区，逗号分隔
    sales = Column(String, nullable=True)  # 销售额(元)
    pool = Column(String, nullable=True)  # 奖池(旧字段，保留兼容)
    prize_pool = Column(String, nullable=True)  # 奖池滚存金额(元)
    first_prize_count = Column(String, nullable=True)  # 一等奖中奖注数
    first_prize_amount = Column(String, nullable=True)  # 一等奖单注奖金(元)
    second_prize_count = Column(String, nullable=True)  # 二等奖中奖注数
    second_prize_amount = Column(String, nullable=True)  # 二等奖单注奖金(元)


class AppSettings(Base):
    """应用配置（LLM key / 后台密码等）。"""

    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True)
    value = Column(Text)


class PredictionRecord(Base):
    """预测记录 + 命中回测。"""

    __tablename__ = "prediction_records"
    __table_args__ = (
        UniqueConstraint(
            "lottery_type", "based_on_issue", "sequence", name="uix_pred_cycle_seq"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    lottery_type = Column(String, index=True)
    based_on_issue = Column(String, index=True)  # 基于哪一期数据预测
    target_issue = Column(String, index=True, nullable=True)  # 预测目标期号
    sequence = Column(Integer, nullable=False, default=0)  # 同周期内序号
    red_balls = Column(String)
    blue_balls = Column(String)
    used_llm = Column(Boolean, default=False, index=True)
    llm_model = Column(String, nullable=True)
    llm_latency_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    # 回测字段
    evaluated = Column(Boolean, default=False, index=True)
    actual_issue = Column(String, nullable=True)
    actual_red_balls = Column(String, nullable=True)
    actual_blue_balls = Column(String, nullable=True)
    red_hits = Column(Integer, nullable=True)
    blue_hits = Column(Integer, nullable=True)
    total_hits = Column(Integer, nullable=True)


class AiGenerationLog(Base):
    """LLM 调用日志（prompt + 原始返回）。"""

    __tablename__ = "ai_generation_logs"

    id = Column(Integer, primary_key=True, index=True)
    lottery_type = Column(String, index=True)
    based_on_issue = Column(String, index=True)
    llm_model = Column(String, nullable=True)
    llm_base_url = Column(String, nullable=True)
    llm_latency_ms = Column(Integer, nullable=True)
    prompt = Column(Text, nullable=True)
    raw_content = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class UserBet(Base):
    """用户采纳的投注记录。"""

    __tablename__ = "user_bets"

    id = Column(Integer, primary_key=True, index=True)
    lottery_type = Column(String, index=True)
    red_balls = Column(String)  # 逗号分隔
    blue_balls = Column(String)  # 逗号分隔
    target_issue = Column(String, index=True)  # 目标期号
    source = Column(String, nullable=True)  # 来源: ai_predict / manual / backtest
    reason = Column(Text, nullable=True)  # 选号理由(来自AI预测)
    cost = Column(Integer, default=2)  # 每注2元
    note = Column(Text, nullable=True)  # 用户备注
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    # 开奖后自动填充
    evaluated = Column(Boolean, default=False, index=True)
    actual_red_balls = Column(String, nullable=True)
    actual_blue_balls = Column(String, nullable=True)
    red_hits = Column(Integer, nullable=True)
    blue_hits = Column(Integer, nullable=True)
    prize_level = Column(Integer, default=0)  # 0=未中, 1-8
    prize_amount = Column(Integer, default=0)
    prize_desc = Column(String, nullable=True)
    evaluated_at = Column(DateTime, nullable=True)
