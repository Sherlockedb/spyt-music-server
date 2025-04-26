import logging
import sys
from pathlib import Path
from typing import Optional

from loguru import logger

from app.core.environment import get_settings


class InterceptHandler(logging.Handler):
    """
    拦截标准库日志并重定向到 loguru
    """
    def emit(self, record):
        # 获取对应的 loguru 级别
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # 查找调用者
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logging():
    """
    配置日志系统
    """
    settings = get_settings()
    
    # 移除所有默认处理器
    logger.remove()
    
    # 添加控制台处理器
    logger.add(
        sys.stdout,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        level=settings.LOG_LEVEL,
        colorize=True,
    )
    
    # 添加文件处理器（如果配置了日志文件）
    if settings.LOG_FILE:
        log_file = Path(settings.LOG_FILE)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        logger.add(
            str(log_file),
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
            level=settings.LOG_LEVEL,
            rotation="10 MB",  # 日志文件大小达到10MB时轮转
            retention="1 month",  # 保留1个月的日志
        )
    
    # 拦截标准库日志
    logging.basicConfig(handlers=[InterceptHandler()], level=0)
    
    # 拦截第三方库日志
    for logger_name in ("uvicorn", "uvicorn.error", "fastapi"):
        logging_logger = logging.getLogger(logger_name)
        logging_logger.handlers = [InterceptHandler()]
    
    logger.info(f"Logging initialized. Level: {settings.LOG_LEVEL}")
    logger.info(f"Environment: {settings.Config.env_file}")