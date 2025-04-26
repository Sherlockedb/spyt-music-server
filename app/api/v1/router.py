from fastapi import APIRouter

api_router = APIRouter()

# 这里将导入和包含各个端点路由器
# 例如：
# from app.api.v1.endpoints import users, search, downloads
# api_router.include_router(users.router, prefix="/users", tags=["users"])
# api_router.include_router(search.router, prefix="/search", tags=["search"])
# api_router.include_router(downloads.router, prefix="/downloads", tags=["downloads"])