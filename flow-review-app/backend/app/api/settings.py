"""
后端配置管理 API

前端可以通过此接口读写 LLM 配置，不再依赖 localStorage
"""
import json
import os
from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel
from app.core.config import settings


router = APIRouter(prefix="/settings", tags=["settings"])

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "data", "runtime_settings.json")


class SettingsUpdate(BaseModel):
    LLM_PROVIDER: Optional[str] = None
    LLM_API_KEY: Optional[str] = None
    LLM_MODEL: Optional[str] = None
    LLM_BASE_URL: Optional[str] = None
    AI_CONFIDENCE_THRESHOLD: Optional[float] = None


def _load_runtime() -> dict:
    """加载运行时配置"""
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    return {}


def _save_runtime(data: dict):
    """保存运行时配置"""
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_effective_settings() -> dict:
    """获取当前生效的配置（运行时覆盖 + 环境变量）"""
    runtime = _load_runtime()
    return {
        "LLM_PROVIDER": runtime.get("LLM_PROVIDER", settings.LLM_PROVIDER),
        "LLM_API_KEY": "已配置" if (runtime.get("LLM_API_KEY") or settings.LLM_API_KEY) else "",
        "LLM_MODEL": runtime.get("LLM_MODEL", settings.LLM_MODEL),
        "LLM_BASE_URL": runtime.get("LLM_BASE_URL", settings.LLM_BASE_URL),
        "AI_CONFIDENCE_THRESHOLD": runtime.get("AI_CONFIDENCE_THRESHOLD", settings.AI_CONFIDENCE_THRESHOLD),
    }


@router.get("")
async def get_settings():
    """获取当前配置"""
    return get_effective_settings()


@router.put("")
async def update_settings(body: SettingsUpdate):
    """更新配置（保存到运行时文件）"""
    runtime = _load_runtime()
    update = body.model_dump(exclude_none=True)
    runtime.update(update)
    _save_runtime(runtime)

    # 同时更新 settings 对象中的值（热更新）
    if "LLM_API_KEY" in update and update["LLM_API_KEY"]:
        settings.LLM_API_KEY = update["LLM_API_KEY"]
    if "LLM_MODEL" in update and update["LLM_MODEL"]:
        settings.LLM_MODEL = update["LLM_MODEL"]
    if "LLM_BASE_URL" in update and update["LLM_BASE_URL"]:
        settings.LLM_BASE_URL = update["LLM_BASE_URL"]
    if "LLM_PROVIDER" in update and update["LLM_PROVIDER"]:
        settings.LLM_PROVIDER = update["LLM_PROVIDER"]

    return {"message": "配置已保存", "settings": get_effective_settings()}
