"""后台管理路由：登录 / LLM 配置 / 连通性测试。"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from itsdangerous import URLSafeSerializer, BadSignature

import config
import models
from database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["admin"])

_serializer = URLSafeSerializer(config.SESSION_SECRET, salt="admin-session")
_COOKIE_NAME = "dlt_admin_session"


def _set_session(response: Response, username: str):
    token = _serializer.dumps({"u": username})
    response.set_cookie(_COOKIE_NAME, token, httponly=True, samesite="lax", max_age=86400 * 7)


def _get_session(request: Request) -> str | None:
    token = request.cookies.get(_COOKIE_NAME)
    if not token:
        return None
    try:
        data = _serializer.loads(token)
        return data.get("u")
    except BadSignature:
        return None


def require_auth(request: Request):
    """依赖：校验后台登录。"""
    user = _get_session(request)
    if not user:
        raise HTTPException(status_code=401, detail="未登录")
    return user


class LoginRequest(BaseModel):
    username: str
    password: str


class LlmConfigRequest(BaseModel):
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_model: str = ""


class PasswordRequest(BaseModel):
    old_password: str
    new_password: str


@router.post("/login")
def login(body: LoginRequest, response: Response, db: Session = Depends(get_db)):
    """后台登录。"""
    stored_pw = db.query(models.AppSettings).filter_by(key="admin_password").first()
    expected = stored_pw.value if stored_pw else config.ADMIN_PASSWORD
    if body.username != config.ADMIN_USERNAME or body.password != expected:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    _set_session(response, body.username)
    return {"ok": True, "username": body.username}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(_COOKIE_NAME)
    return {"ok": True}


@router.get("/status")
def admin_status(request: Request, db: Session = Depends(get_db)):
    """后台状态（含登录态 + LLM 配置概况）。"""
    logged_in = _get_session(request) is not None
    api_key = db.query(models.AppSettings).filter_by(key="llm_api_key").first()
    base_url = db.query(models.AppSettings).filter_by(key="llm_base_url").first()
    model = db.query(models.AppSettings).filter_by(key="llm_model").first()
    return {
        "logged_in": logged_in,
        "has_api_key": bool(api_key and api_key.value),
        "llm_base_url": base_url.value if base_url else config.DEFAULT_LLM_BASE_URL,
        "llm_model": model.value if model else config.DEFAULT_LLM_MODEL,
    }


@router.post("/llm-config")
def save_llm_config(body: LlmConfigRequest, request: Request, db: Session = Depends(get_db)):
    """保存 LLM 配置（需登录）。"""
    require_auth(request)
    mapping = {
        "llm_api_key": body.llm_api_key,
        "llm_base_url": body.llm_base_url,
        "llm_model": body.llm_model,
    }
    for key, value in mapping.items():
        if value is None:
            continue
        existing = db.query(models.AppSettings).filter_by(key=key).first()
        if existing:
            existing.value = value
        else:
            db.add(models.AppSettings(key=key, value=value))
    db.commit()
    return {"ok": True}


@router.post("/change-password")
def change_password(body: PasswordRequest, request: Request, db: Session = Depends(get_db)):
    """修改后台密码（需登录）。"""
    require_auth(request)
    stored = db.query(models.AppSettings).filter_by(key="admin_password").first()
    expected = stored.value if stored else config.ADMIN_PASSWORD
    if body.old_password != expected:
        raise HTTPException(status_code=400, detail="旧密码错误")
    if not body.new_password or len(body.new_password) < 4:
        raise HTTPException(status_code=400, detail="新密码至少 4 位")
    if stored:
        stored.value = body.new_password
    else:
        db.add(models.AppSettings(key="admin_password", value=body.new_password))
    db.commit()
    return {"ok": True}


@router.post("/test-llm")
def test_llm(request: Request, db: Session = Depends(get_db)):
    """测试 LLM 连通性（需登录）。"""
    require_auth(request)
    api_key = (db.query(models.AppSettings).filter_by(key="llm_api_key").first() or models.AppSettings()).value or ""
    if not api_key:
        return {"ok": False, "error": "未配置 API Key"}
    # 复用 predictor 做一次轻量预测
    from predictor import Predictor

    predictor = Predictor(db)
    result = predictor.predict(count=1)
    if "error" in result:
        return {"ok": False, "error": result["error"]}
    return {"ok": True, "meta": result.get("meta")}
