"""
应用配置管理
"""
import os
from pydantic_settings import BaseSettings
from pathlib import Path

# 项目根目录（backend/ 目录）
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class Settings(BaseSettings):
    """应用配置"""
    # 数据库
    DATABASE_URL: str = "sqlite:///./data/sqlite/flow_review.db"

    # 文件存储
    UPLOAD_DIR: str = "./data/uploads"
    MAX_FILE_SIZE: int = 10485760  # 10MB

    # 大模型配置
    LLM_PROVIDER: str = "deepseek"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "deepseek-chat"
    LLM_BASE_URL: str = "https://api.deepseek.com"

    # 评审参数
    REVIEW_TIMEOUT: int = 300
    DEFAULT_TEMPERATURE: float = 0.0
    MAX_RETRIES: int = 3
    AI_CONFIDENCE_THRESHOLD: float = 0.7

    # 支持的文件类型
    ALLOWED_EXTENSIONS: set = {
        ".md", ".docx", ".bpmn", ".vsdx",
        ".png", ".jpg", ".jpeg", ".xlsx", ".csv"
    }

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

# 确保上传目录存在（解析相对路径为绝对路径）
_upload_dir = settings.UPLOAD_DIR
if not os.path.isabs(_upload_dir):
    _upload_dir = os.path.abspath(os.path.join(_BACKEND_DIR, _upload_dir))
Path(_upload_dir).mkdir(parents=True, exist_ok=True)
settings.UPLOAD_DIR = _upload_dir
