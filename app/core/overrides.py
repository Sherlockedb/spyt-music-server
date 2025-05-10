from fastapi import FastAPI, Depends
from app.core.auth import get_current_user, get_current_active_user, get_current_admin_user
from app.core.deps import get_user_repository, get_user_service

def setup_dependency_overrides(app: FastAPI, overrides: dict = None):
    """
    设置依赖覆盖

    参数:
        app: FastAPI应用实例
        overrides: 依赖覆盖字典，键为原始依赖项，值为替代依赖项
    """
    if overrides:
        for original, override in overrides.items():
            app.dependency_overrides[original] = override

# 用于替换当前用户依赖的辅助函数
def override_get_current_user(user: dict):
    """生成一个返回固定用户的依赖覆盖函数"""
    async def _get_current_user():
        return user
    return _get_current_user