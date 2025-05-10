from typing import Any, List, Optional
from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder

from app.models.user import UserCreate, UserUpdate, UserResponse
from app.services.user_service import UserService
from app.core.auth import get_current_user, get_current_admin_user
from app.core.deps import get_user_service

router = APIRouter()

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_in: UserCreate,
    user_service: UserService = Depends(get_user_service)
) -> Any:
    """
    创建新用户（无需认证）
    """
    try:
        user = await user_service.create_user(
            username=user_in.username,
            email=user_in.email,
            password=user_in.password,
            full_name=user_in.full_name,
            role="user"  # 普通用户默认角色
        )
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

@router.get("/me", response_model=UserResponse)
async def read_current_user(
    current_user: dict = Depends(get_current_user)
) -> Any:
    """
    获取当前登录用户信息
    """
    return current_user

@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_in: UserUpdate,
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
) -> Any:
    """
    更新当前用户信息
    """
    try:
        user = await user_service.update_user(current_user["_id"], jsonable_encoder(user_in, exclude_unset=True))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户未找到"
            )
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

@router.get("/", response_model=List[UserResponse])
async def read_users(
    query: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    user_service: UserService = Depends(get_user_service),
    current_user: dict = Depends(get_current_admin_user)
) -> Any:
    """
    获取用户列表（仅管理员）
    """
    if query:
        users = await user_service.search_users(query, skip=skip, limit=limit)
    else:
        users = await user_service.user_repo.find({}, skip=skip, limit=limit)
    return users

@router.get("/{user_id}", response_model=UserResponse)
async def read_user_by_id(
    user_id: str,
    user_service: UserService = Depends(get_user_service),
    current_user: dict = Depends(get_current_admin_user)
) -> Any:
    """
    通过ID获取用户（仅管理员）
    """
    user = await user_service.get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户未找到"
        )
    return user

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_in: UserUpdate,
    user_service: UserService = Depends(get_user_service),
    current_user: dict = Depends(get_current_admin_user)
) -> Any:
    """
    更新用户信息（仅管理员）
    """
    try:
        user = await user_service.update_user(user_id, jsonable_encoder(user_in, exclude_unset=True))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户未找到"
            )
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    user_service: UserService = Depends(get_user_service),
    current_user: dict = Depends(get_current_admin_user)
) -> None:
    """
    删除用户（仅管理员）
    """
    success = await user_service.delete_user(user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户未找到"
        )