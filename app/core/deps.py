from typing import Generator
from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorClient

from app.db.repositories.users import UserRepository
from app.services.user_service import UserService
from app.core.database import get_db

# 获取用户仓库
async def get_user_repository(db=Depends(get_db)) -> UserRepository:
    return UserRepository(db)

# 获取用户服务
async def get_user_service(
    user_repo: UserRepository = Depends(get_user_repository)
) -> UserService:
    return UserService(user_repo)