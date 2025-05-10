from fastapi import APIRouter
from app.api.v1.endpoints import users, auth, downloads, search, library, stream

api_router = APIRouter()

# 认证相关路由
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])

# 用户相关路由
api_router.include_router(users.router, prefix="/users", tags=["users"])

# 下载相关路由
api_router.include_router(downloads.router, prefix="/downloads", tags=["downloads"])

# 搜索相关路由
api_router.include_router(search.router, prefix="/search", tags=["search"])

api_router.include_router(library.router, prefix="/library", tags=["library"])

api_router.include_router(stream.router, prefix="/stream", tags=["stream"])