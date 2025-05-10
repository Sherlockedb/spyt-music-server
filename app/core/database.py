from typing import Generator
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import settings

# 全局变量，用于保存数据库连接
mongodb_client: AsyncIOMotorClient = None
database: AsyncIOMotorDatabase = None

async def connect_to_mongo():
    """连接MongoDB数据库"""
    global mongodb_client, database
    mongodb_client = AsyncIOMotorClient(settings.MONGODB_URL)
    database = mongodb_client[settings.MONGODB_DB]

async def close_mongo_connection():
    """关闭MongoDB连接"""
    global mongodb_client
    if mongodb_client:
        mongodb_client.close()

async def get_db() -> AsyncIOMotorDatabase:
    """获取数据库连接"""
    return database