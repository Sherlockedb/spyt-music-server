from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from bson import ObjectId

from app.db.base_repository import BaseRepository
from app.db.schemas import USERS_COLLECTION
from app.core.security import get_password_hash, verify_password
from bson.errors import InvalidId

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
            用户ID (_id 字段值)
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

        # insert_one返回的是MongoDB生成的_id值（ObjectId类型）
        return await self.insert_one(user)

    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """通过用户名获取用户"""
        return await self.find_one({"username": username})

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """通过电子邮件获取用户"""
        return await self.find_one({"email": email})

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """通过ID获取用户"""
        try:
            return await self.find_one({"_id": ObjectId(user_id)})
        except InvalidId:
            return None

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

    async def update_user(self, user_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """更新用户信息"""
        update_data["updated_at"] = datetime.now(timezone.utc)

        return await self.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_data}
        )

    async def delete_user(self, user_id: str) -> bool:
        """删除用户"""
        return await self.delete_one({"_id": ObjectId(user_id)})

    async def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """验证用户凭据"""
        user = await self.get_user_by_username(username)

        if not user or user.get("disabled", False):
            return None

        if not verify_password(password, user["hashed_password"]):
            return None

        # 更新最后登录时间
        await self.update_one(
            {"_id": user["_id"]},
            {"$set": {"last_login": datetime.now(timezone.utc)}}
        )

        return user

    async def search_users(self, query: str, skip: int = 0, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索用户"""
        search_query = {
            "$or": [
                {"username": {"$regex": query, "$options": "i"}},
                {"full_name": {"$regex": query, "$options": "i"}},
                {"email": {"$regex": query, "$options": "i"}}
            ]
        }

        return await self.find(search_query, skip=skip, limit=limit)