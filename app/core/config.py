import secrets
from typing import Any, Dict, List, Optional, Union

from pydantic import AnyHttpUrl, HttpUrl, Field, field_validator, model_validator
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    """
    应用配置，从环境变量和 .env 文件加载
    """
    # API 配置
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "spyt-music-server"
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # CORS 配置
    BACKEND_CORS_ORIGINS: List[str] = []

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # 安全配置
    SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # MongoDB 配置
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB: str = "spyt_music"

    # Spotify API 配置
    SPOTIFY_CLIENT_ID: Optional[str] = None
    SPOTIFY_CLIENT_SECRET: Optional[str] = None

    # 文件存储配置
    MUSIC_LIBRARY_PATH: str = str(Path.home() / "spyt_music_library")
    TEMP_DOWNLOAD_PATH: str = str(Path.home() / "spyt_temp_downloads")

    @field_validator("MUSIC_LIBRARY_PATH", "TEMP_DOWNLOAD_PATH")
    @classmethod
    def create_directories(cls, v: str) -> str:
        path = Path(v)
        path.mkdir(parents=True, exist_ok=True)
        return str(path)

    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Optional[str] = "logs/spyt-music-server.log"

    # 工作进程配置
    WORKER_CONCURRENCY: int = 2
    WORKER_POLL_INTERVAL: int = 5

    @field_validator("WORKER_POLL_INTERVAL", mode="before")
    @classmethod
    def parse_poll_interval(cls, v: Any) -> int:
        if isinstance(v, str):
            # 移除注释
            v = v.split('#')[0].strip()
        try:
            return int(v)
        except (ValueError, TypeError):
            raise ValueError(f"无法将 {v} 解析为整数")

    class Config:
        case_sensitive = True
        env_file = ".env"


# 创建全局设置对象
settings = Settings()