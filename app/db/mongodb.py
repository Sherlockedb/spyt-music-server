import logging
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ServerSelectionTimeoutError

from app.core.config import settings
from app.db.schemas import init_db

class Database:
    client: AsyncIOMotorClient = None
    db = None

db = Database()

async def connect_to_mongo():
    """连接到 MongoDB 数据库"""
    logging.info("正在连接到 MongoDB...")
    db.client = AsyncIOMotorClient(settings.MONGODB_URL)
    db.db = db.client[settings.MONGODB_DB]
    
    try:
        # 验证连接
        await db.client.admin.command('ping')
        logging.info("成功连接到 MongoDB")
        
        # 初始化数据库模式
        await init_db(db.db)
        logging.info("数据库模式初始化完成")
    except ServerSelectionTimeoutError:
        logging.error("无法连接到 MongoDB 服务器，请检查您的配置")
        raise

async def close_mongo_connection():
    """关闭与 MongoDB 的连接"""
    if db.client:
        db.client.close()
        logging.info("MongoDB 连接已关闭")

def get_database():
    """获取数据库对象"""
    return db.db