from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from bson.errors import InvalidId

from app.db.repositories.users import UserRepository
from app.core.security import get_password_hash, create_access_token, create_refresh_token
from app.core.config import settings

class UserService:
    """用户服务，处理用户相关业务逻辑"""

    def __init__(self, user_repo: UserRepository):
        """初始化服务"""
        self.user_repo = user_repo

    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户信息"""
        try:
            return await self.user_repo.get_user_by_id(user_id)
        except InvalidId:
            return None

    async def create_user(self, username: str, email: str, password: str,
                         full_name: str = None, role: str = "user") -> Dict[str, Any]:
        """创建新用户"""
        # 检查用户名是否已存在
        existing_user = await self.user_repo.get_user_by_username(username)
        if existing_user:
            raise ValueError(f"用户名 '{username}' 已被使用")

        # 检查邮箱是否已存在
        existing_email = await self.user_repo.get_user_by_email(email)
        if existing_email:
            raise ValueError(f"邮箱 '{email}' 已被注册")

        # 哈希密码
        hashed_password = get_password_hash(password)

        # 创建用户
        user_id = await self.user_repo.create_user(
            username=username,
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            role=role
        )

        # 获取创建的用户
        return await self.user_repo.get_user_by_id(user_id)

    async def update_user(self, user_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """更新用户信息"""
        # 确保用户存在
        user = await self.user_repo.get_user_by_id(user_id)
        if not user:
            return None

        # 检查用户名是否冲突
        if "username" in update_data and update_data["username"] != user["username"]:
            existing_user = await self.user_repo.get_user_by_username(update_data["username"])
            if existing_user:
                raise ValueError(f"用户名 '{update_data['username']}' 已被使用")

        # 检查邮箱是否冲突
        if "email" in update_data and update_data["email"] != user["email"]:
            existing_email = await self.user_repo.get_user_by_email(update_data["email"])
            if existing_email:
                raise ValueError(f"邮箱 '{update_data['email']}' 已被注册")

        # 处理密码更新
        if "password" in update_data:
            hashed_password = get_password_hash(update_data.pop("password"))
            await self.user_repo.update_user_password(user_id, hashed_password)

        # 处理偏好设置更新
        if "preferences" in update_data:
            await self.user_repo.update_user_preferences(user_id, update_data.pop("preferences"))

        # 更新其他用户信息
        if update_data:
            await self.user_repo.update_user(user_id, update_data)

        # 返回更新后的用户信息
        return await self.user_repo.get_user_by_id(user_id)

    async def delete_user(self, user_id: str) -> bool:
        """删除用户"""
        try:
            return await self.user_repo.delete_user(user_id)
        except InvalidId:
            return False

    async def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """用户认证"""
        return await self.user_repo.authenticate_user(username, password)

    def create_tokens(self, user_id: str) -> Dict[str, str]:
        """创建访问令牌和刷新令牌"""
        access_token = create_access_token(
            subject=user_id,
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )

        refresh_token = create_refresh_token(subject=user_id)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }

    async def search_users(self, query: str, skip: int = 0, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索用户"""
        return await self.user_repo.search_users(query, skip=skip, limit=limit)

    async def update_user_role(self, user_id: str, role: str) -> Optional[Dict[str, Any]]:
        """更新用户角色（仅管理员可用）"""
        user = await self.user_repo.get_user_by_id(user_id)
        if not user:
            return None

        return await self.user_repo.update_user(user_id, {"role": role})