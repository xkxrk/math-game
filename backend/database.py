"""数据库连接：SQLite + SQLAlchemy。"""
import os
import sqlite3
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

import config

# 优先使用 DATABASE_URL，否则用 DB_PATH
if config.DATABASE_URL:
    SQLALCHEMY_DATABASE_URL = config.DATABASE_URL
else:
    db_path = config.DB_PATH
    # 确保目录存在
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    if db_path.startswith("sqlite:"):
        SQLALCHEMY_DATABASE_URL = db_path
    elif os.path.isabs(db_path):
        SQLALCHEMY_DATABASE_URL = f"sqlite:///{db_path}"
    else:
        SQLALCHEMY_DATABASE_URL = f"sqlite:///./{db_path.lstrip('./')}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI 依赖：每请求一个 session。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """建表 + 迁移新列 + 初始化默认配置 + 首次写入管理员密码。"""
    import models  # noqa: avoid circular import at module load

    Base.metadata.create_all(bind=engine)
    _migrate_columns()
    _seed_defaults()
    _seed_admin_password()


def _migrate_columns():
    """为已有表添加新列（SQLite ALTER TABLE ADD COLUMN）。"""
    from sqlalchemy import text, inspect

    inspector = inspect(engine)
    table_cols = {
        "lottery_records": {
            "prize_pool": "TEXT",
            "first_prize_count": "TEXT",
            "first_prize_amount": "TEXT",
            "second_prize_count": "TEXT",
            "second_prize_amount": "TEXT",
        },
        "user_bets": {
            "llm_model": "TEXT",
        },
    }
    with engine.connect() as conn:
        for table, cols in table_cols.items():
            if table not in inspector.get_table_names():
                continue
            existing = {c["name"] for c in inspector.get_columns(table)}
            for col, col_type in cols.items():
                if col not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"))
                    conn.commit()


def _seed_defaults():
    """写入默认 LLM 配置（仅当不存在时）。"""
    from models import AppSettings

    db = SessionLocal()
    try:
        defaults = {
            "llm_base_url": config.DEFAULT_LLM_BASE_URL,
            "llm_model": config.DEFAULT_LLM_MODEL,
        }
        for key, value in defaults.items():
            existing = db.query(AppSettings).filter_by(key=key).first()
            if not existing:
                db.add(AppSettings(key=key, value=value))
        db.commit()
    finally:
        db.close()


def _seed_admin_password():
    """首次启动写入管理员密码（之后以数据库为准）。"""
    from models import AppSettings

    db = SessionLocal()
    try:
        existing = db.query(AppSettings).filter_by(key="admin_password").first()
        if not existing:
            db.add(AppSettings(key="admin_password", value=config.ADMIN_PASSWORD))
        db.commit()
    finally:
        db.close()
