"""模型配置路由：轻量化，无需登录（本地工具）。"""
import threading
import subprocess
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

import config
import models
from database import get_db

router = APIRouter(prefix="/api/settings", tags=["settings"])

# 模型拉取状态：{model_name: {"status": "pulling"/"done"/"error", "progress": "...", "log": []}}
_pull_status: dict = {}
_pull_lock = threading.Lock()


class LlmConfig(BaseModel):
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_model: str = ""


def _get_setting(db: Session, key: str) -> str:
    row = db.query(models.AppSettings).filter_by(key=key).first()
    return row.value if row else ""


def _set_setting(db: Session, key: str, value: str):
    row = db.query(models.AppSettings).filter_by(key=key).first()
    if row:
        row.value = value
    else:
        db.add(models.AppSettings(key=key, value=value))


@router.get("/llm")
def get_llm_config(db: Session = Depends(get_db)):
    """获取当前 LLM 配置。"""
    return {
        "llm_api_key": _get_setting(db, "llm_api_key"),
        "llm_base_url": _get_setting(db, "llm_base_url") or config.DEFAULT_LLM_BASE_URL,
        "llm_model": _get_setting(db, "llm_model") or config.DEFAULT_LLM_MODEL,
        "defaults": {
            "llm_base_url": config.DEFAULT_LLM_BASE_URL,
            "llm_model": config.DEFAULT_LLM_MODEL,
        },
    }


@router.post("/llm")
def save_llm_config(body: LlmConfig, db: Session = Depends(get_db)):
    """保存 LLM 配置（空值跳过，不覆盖已有配置）。"""
    if body.llm_api_key is not None and body.llm_api_key != "":
        _set_setting(db, "llm_api_key", body.llm_api_key)
    if body.llm_base_url:
        _set_setting(db, "llm_base_url", body.llm_base_url)
    if body.llm_model:
        _set_setting(db, "llm_model", body.llm_model)
    db.commit()
    return {"ok": True, "message": "配置已保存"}


@router.post("/test")
def test_llm(db: Session = Depends(get_db)):
    """测试 LLM 连通性，实际跑一次轻量预测。"""
    api_key = _get_setting(db, "llm_api_key")
    if not api_key:
        return {"ok": False, "error": "未配置 API Key"}
    from predictor import Predictor

    predictor = Predictor(db)
    result = predictor.predict(count=1)
    if "error" in result:
        return {"ok": False, "error": result["error"]}
    meta = result.get("meta") or {"used_llm": True}
    pred = result.get("predictions", [{}])[0] if result.get("predictions") else {}
    return {
        "ok": True,
        "used_llm": meta.get("used_llm", False),
        "model": meta.get("model", ""),
        "sample": {
            "red_balls": pred.get("red_balls", []),
            "blue_balls": pred.get("blue_balls", []),
        },
    }


# ------------------------------------------------------------------ #
# Ollama 模型管理
# ------------------------------------------------------------------ #

@router.get("/models")
def list_ollama_models():
    """获取 Ollama 已安装的模型列表。"""
    import urllib.request
    import json as _json

    try:
        req = urllib.request.Request("http://localhost:11434/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = _json.loads(resp.read().decode())
        models_list = [
            {
                "name": m.get("name", ""),
                "size": m.get("size", 0),
                "details": m.get("details", {}),
            }
            for m in data.get("models", [])
        ]
        return {"ok": True, "models": models_list}
    except Exception as e:
        return {"ok": False, "error": str(e), "models": []}


class PullModelRequest(BaseModel):
    model_name: str


@router.post("/pull-model")
def pull_model(req: PullModelRequest):
    """异步拉取 Ollama 模型（ollama pull <model>）。"""
    model = req.model_name.strip()
    if not model:
        return {"ok": False, "error": "模型名不能为空"}

    with _pull_lock:
        existing = _pull_status.get(model)
        if existing and existing["status"] == "pulling":
            return {"ok": False, "error": f"正在拉取 {model}，请等待完成"}

    # 启动后台线程执行 ollama pull
    def _do_pull():
        with _pull_lock:
            _pull_status[model] = {
                "status": "pulling",
                "progress": "starting...",
                "log": [],
            }
        try:
            proc = subprocess.Popen(
                ["ollama", "pull", model],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            for line in proc.stdout:
                line = line.strip()
                if not line:
                    continue
                with _pull_lock:
                    s = _pull_status.get(model, {})
                    s["progress"] = line
                    s["log"].append(line)
                    # 保留最近 50 行
                    if len(s["log"]) > 50:
                        s["log"] = s["log"][-50:]
            proc.wait()
            with _pull_lock:
                s = _pull_status.get(model, {})
                if proc.returncode == 0:
                    s["status"] = "done"
                    s["progress"] = "done"
                else:
                    s["status"] = "error"
                    s["progress"] = f"exit code {proc.returncode}"
        except Exception as e:
            with _pull_lock:
                _pull_status[model] = {
                    "status": "error",
                    "progress": str(e),
                    "log": [str(e)],
                }

    t = threading.Thread(target=_do_pull, daemon=True)
    t.start()
    return {"ok": True, "message": f"开始拉取 {model}"}


@router.get("/pull-status")
def get_pull_status(model: str = ""):
    """查询模型拉取状态。"""
    with _pull_lock:
        if model:
            return {"ok": True, "status": _pull_status.get(model, {"status": "idle", "progress": "", "log": []})}
        return {"ok": True, "all": dict(_pull_status)}
