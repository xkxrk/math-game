"""超级大乐透预测辅助系统 —— FastAPI 入口。

启动：python -m uvicorn main:app --reload --host 0.0.0.0 --port 8888
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import config
from database import init_db, SessionLocal
from routes import lottery, predict, admin, sse, backtest, bets, analyze
from routes import llm_settings
from scraper import DltScraper
from scheduler import start_scheduler, stop_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _auto_init_data():
    """首次启动自动抓取历史数据。"""
    db = SessionLocal()
    try:
        import models

        count = (
            db.query(models.LotteryRecord)
            .filter_by(lottery_type=config.LOTTERY_TYPE)
            .count()
        )
        if count == 0:
            logger.info("数据库为空，开始自动抓取历史数据...")
            scraper = DltScraper(db)
            result = scraper.scrape(limit=200, upsert=True)
            logger.info(f"自动初始化完成: {result}")
        else:
            logger.info(f"已有 {count} 条历史记录，跳过自动初始化")
    except Exception as e:
        logger.error(f"自动初始化失败: {e}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化 + 调度，关闭时清理。"""
    logger.info("=== 超级大乐透预测辅助系统启动 ===")
    init_db()
    _auto_init_data()
    start_scheduler()
    yield
    stop_scheduler()
    logger.info("=== 系统已停止 ===")


app = FastAPI(
    title="超级大乐透预测辅助系统",
    description="基于历史数据抓取与 LLM 分析的大乐透预测辅助",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS（开发期前端独立端口）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载路由
app.include_router(lottery.router)
app.include_router(predict.router)
app.include_router(admin.router)
app.include_router(sse.router)
app.include_router(backtest.router)
app.include_router(bets.router)
app.include_router(analyze.router)
app.include_router(llm_settings.router)


@app.get("/api/health")
def health():
    return {"ok": True, "service": config.LOTTERY_NAME, "version": "1.0.0"}


@app.get("/api/rules")
def rules():
    """大乐透规则说明。"""
    return {
        "name": config.LOTTERY_NAME,
        "type": config.LOTTERY_TYPE,
        "red": {"max": config.RED_MAX, "pick": config.RED_PICK, "label": "前区"},
        "blue": {"max": config.BLUE_MAX, "pick": config.BLUE_PICK, "label": "后区"},
        "draw_weekdays": ["周一", "周三", "周六"],
    }


# 生产环境：挂载前端静态文件（Docker 构建产物）
_frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if _frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="frontend")
else:
    @app.get("/")
    def root():
        return {
            "message": "超级大乐透预测辅助系统 API",
            "frontend": "未构建前端，请运行 cd frontend && npm run dev",
            "docs": "/docs",
        }
