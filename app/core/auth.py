from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import ValidationError
from app.core.config import settings
from app.db.repositories.users import UserRepository
from app.models.user import UserInDB
from app.models.auth import TokenData
from app.core.deps import get_user_repository
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm, HTTPBasic, HTTPBasicCredentials
from fastapi.security.utils import get_authorization_scheme_param

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

# 标准OAuth2Bearer模式（必需）
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login"
)

# 创建可选的OAuth2Bearer依赖
class OAuth2PasswordBearerOptional(OAuth2PasswordBearer):
    """可选的OAuth2Bearer依赖"""

    async def __call__(self, request: Request) -> Optional[str]:
        authorization = request.headers.get("Authorization")
        scheme, param = get_authorization_scheme_param(authorization)
        if not authorization or scheme.lower() != "bearer":
            return None
        return param

oauth2_scheme_optional = OAuth2PasswordBearerOptional(
    tokenUrl="/api/v1/auth/login"
)

async def get_optional_user(
    token: str = Depends(oauth2_scheme_optional),
    user_repo: UserRepository = Depends(get_user_repository)
):
    """
    获取当前用户，如果未提供有效令牌则返回None
    """
    if not token:
        return None

    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        token_data = TokenData(user_id=user_id)
    except JWTError:
        return None

    user = await user_repo.get_user_by_id(token_data.user_id)
    if user is None:
        return None

    return user