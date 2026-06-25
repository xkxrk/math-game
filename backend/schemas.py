"""Pydantic 响应模型。"""
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class BallSet(BaseModel):
    red_balls: list[str] = []
    blue_balls: list[str] = []


class PredictionItem(BallSet):
    based_on_issue: Optional[str] = None
    target_issue: Optional[str] = None
    sequence: int = 0
    used_llm: bool = False
    llm_model: Optional[str] = None
    created_at: Optional[datetime] = None
    evaluated: bool = False
    red_hits: Optional[int] = None
    blue_hits: Optional[int] = None
    total_hits: Optional[int] = None


class PredictionResult(BaseModel):
    analysis: str = ""
    predictions: list[PredictionItem] = []
    meta: dict = {}


class LotteryHistoryItem(BaseModel):
    issue: str
    date: Optional[date] = None
    red_balls: str
    blue_balls: str
    sales: Optional[str] = None
    pool: Optional[str] = None


class ScrapeResult(BaseModel):
    added: int
    updated: int
    seen: int


class StatsResult(BaseModel):
    red_frequency: list[dict] = []
    blue_frequency: list[dict] = []
    total_draws: int = 0
    hit_summary: dict = {}


class AdminStatus(BaseModel):
    configured: bool
    llm_model: Optional[str] = None
    llm_base_url: Optional[str] = None
    has_api_key: bool = False
