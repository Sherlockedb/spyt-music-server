import os
from enum import Enum
from functools import lru_cache
from pydantic import field_validator
from typing import Dict, Any, Optional

from app.core.config import Settings


class Environment(str, Enum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class DevelopmentSettings(Settings):
    """开发环境配置"""
    # 开发数据库
    MONGODB_DB: str = "spyt_music_dev"

    LOG_LEVEL: str = "DEBUG"

    # 开发环境特定配置
    DEBUG: bool = True


class TestingSettings(Settings):
    """测试环境配置"""
    # 测试数据库
    MONGODB_DB: str = "spyt_music_test"

    # 测试配置
    TESTING: bool = True


class ProductionSettings(Settings):
    """生产环境配置"""
    # 生产环境特定配置
    DEBUG: bool = False

    # 更严格的安全设置
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15

    @field_validator("SECRET_KEY")
    @classmethod
    def secret_key_must_be_set(cls, v: str) -> str:
        if not v or v == "your-secret-key-here":
            raise ValueError("SECRET_KEY must be set in production")
        return v

    @field_validator("SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET")
    @classmethod
    def spotify_credentials_must_be_set(cls, v: Optional[str]) -> str:
        if not v:
            raise ValueError("Spotify credentials must be set in production")
        return v


@lru_cache()
def get_settings() -> Settings:
    """
    获取当前环境的配置
    使用 APP_ENV 环境变量确定环境，默认为开发环境
    """
    environment = os.getenv("APP_ENV", Environment.DEVELOPMENT)

    settings_map: Dict[str, Any] = {
        Environment.DEVELOPMENT: DevelopmentSettings,
        Environment.TESTING: TestingSettings,
        Environment.PRODUCTION: ProductionSettings,
    }

    settings_class = settings_map.get(environment, DevelopmentSettings)
    return settings_class()
