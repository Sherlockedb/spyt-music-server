from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.environment import get_settings
from app.core.logging import setup_logging


def init_app(app: FastAPI) -> None:
    """
    初始化 FastAPI 应用
    """
    settings = get_settings()
    
    # 设置日志
    setup_logging()
    
    # 设置 CORS
    if settings.BACKEND_CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    # 这里可以添加其他初始化代码，如数据库连接等