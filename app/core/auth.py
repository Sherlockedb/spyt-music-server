from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import ValidationError
from app.core.config import settings
from app.db.repositories.users import UserRepository
from app.models.user import UserInDB
from app.core.deps import get_user_repository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    user_repo: UserRepository = Depends(get_user_repository)  # 将在应用启动时注入
) -> Dict[str, Any]:
    """
    验证令牌并获取当前用户
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception

        token_type = payload.get("type")
        if token_type == "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="不能使用刷新令牌访问",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except (JWTError, ValidationError):
        raise credentials_exception

    user = await user_repo.get_user_by_id(user_id)
    if user is None:
        raise credentials_exception

    if user.get("disabled", False):
        raise HTTPException(status_code=400, detail="用户账户已禁用")

    return user

async def get_current_active_user(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    获取当前活跃用户
    """
    if current_user.get("disabled", False):
        raise HTTPException(status_code=400, detail="用户账户已禁用")
    return current_user

async def get_current_admin_user(
    current_user: Dict[str, Any] = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """
    获取当前管理员用户
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足，需要管理员权限",
        )
    return current_user