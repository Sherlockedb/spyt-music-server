from typing import Any
from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.auth import get_current_user
from app.services.user_service import UserService
from app.core.deps import get_user_service
from jose import jwt, JWTError

router = APIRouter()

@router.post("/login")
async def login_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    user_service: UserService = Depends(get_user_service)
) -> Any:
    """
    OAuth2 兼容令牌登录，获取访问令牌
    """
    user = await user_service.authenticate_user(
        username=form_data.username,
        password=form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_service.create_tokens(user["_id"])

@router.post("/refresh")
async def refresh_token(
    refresh_token: str = Body(...),
    user_service: UserService = Depends(get_user_service)
) -> Any:
    """
    通过刷新令牌获取新的访问令牌
    """
    try:
        from app.core.config import settings

        payload = jwt.decode(
            refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )

        # 验证是否是刷新令牌
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的刷新令牌",
            )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的刷新令牌",
            )

        # 检查用户是否存在
        user = await user_service.get_user(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户不存在",
            )

        # 创建新令牌
        return {
            "access_token": user_service.create_tokens(user_id),
            "token_type": "bearer"
        }

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新令牌",
        )

@router.post("/test-token")
async def test_token(current_user: dict = Depends(get_current_user)) -> Any:
    """
    测试访问令牌是否有效
    """
    return {"username": current_user["username"]}