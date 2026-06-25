"""应用配置：通过环境变量注入，带合理默认值。"""
import os
from pathlib import Path

# 项目根目录（backend 的上一级）
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent

# 时区
TZ = os.getenv("TZ", "Asia/Shanghai")

# 数据库
DATABASE_URL = os.getenv("DATABASE_URL", "")
DB_PATH = os.getenv("DB_PATH", str(PROJECT_DIR / "data" / "dlt.db"))

# 后台账号
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")
SESSION_SECRET = os.getenv("SESSION_SECRET", "dev-secret-change-me")

# LLM 默认值（可在后台覆盖）
DEFAULT_LLM_BASE_URL = "https://api.siliconflow.cn/v1"
DEFAULT_LLM_MODEL = "deepseek-ai/DeepSeek-R1"

# 大乐透规则
LOTTERY_TYPE = "dlt"
LOTTERY_NAME = "超级大乐透"
RED_MAX = 35
RED_PICK = 5
BLUE_MAX = 12
BLUE_PICK = 2

# 大乐透开奖日（周一/三/六）
DRAW_WEEKDAYS = (0, 2, 5)  # Monday=0 ... Sunday=6

# 抓取来源
SCRAPER_URLS = [
    "https://datachart.500.com/dlt/history/newinc/history.php?limit={limit}&sort=0",
    "https://datachart.500.com/dlt/history/newinc/history.php?limit={limit}&sort=1",
]
SCRAPER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}
