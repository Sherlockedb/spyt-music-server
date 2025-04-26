from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from bson import ObjectId

from app.db.base_repository import BaseRepository
from app.db.schemas import USERS_COLLECTION

class UserRepository(BaseRepository):
    """
    用户数据仓库，处理用户相关操作
    """
    
    def __init__(self, db):
        """初始化仓库"""
        super().__init__(db, USERS_COLLECTION)
    
    async def create_user(self, username: str, email: str, hashed_password: str, 
                          full_name: str = None, role: str = "user") -> str:
        """
        创建新用户
        
        参数:
            username: 用户名
            email: 电子邮件
            hashed_password: 哈希后的密码
            full_name: 全名（可选）
            role: 角色（默认为user）
            
        返回:
            用户ID
        """
        user = {
            "username": username,
            "email": email,
            "hashed_password": hashed_password,
            "full_name": full_name,
            "disabled": False,
            "role": role,
            "preferences": {
                "theme": "light",
                "quality": "high"
            },
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        
        return await self.insert_one(user)
    
    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """通过用户名获取用户"""
        return await self.find_one({"username": username})
    
    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """通过电子邮件获取用户"""
        return await self.find_one({"email": email})
    
    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """通过ID获取用户"""
        return await self.find_one({"_id": ObjectId(user_id)})
    
    async def update_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """更新用户偏好设置"""
        return await self.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"preferences": preferences}}
        )
    
    async def update_user_password(self, user_id: str, hashed_password: str) -> Optional[Dict[str, Any]]:
        """更新用户密码"""
        return await self.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"hashed_password": hashed_password}}
        )