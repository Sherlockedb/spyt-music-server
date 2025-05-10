from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import connect_to_mongo, close_mongo_connection, get_db
from app.db.schemas import init_db

# 创建FastAPI应用
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# 设置CORS
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# 添加会话中间件
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

# 注册API路由
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.middleware("http")
async def add_utf8_charset(request, call_next):
    response = await call_next(request)
    
    # 只为JSON响应添加charset，不修改其他类型的响应
    content_type = response.headers.get("Content-Type", "")
    if "application/json" in content_type and "charset" not in content_type:
        response.headers["Content-Type"] = "application/json; charset=utf-8"
    
    return response


# 启动与关闭事件
@app.on_event("startup")
async def startup_event():
    """应用启动时执行的操作"""
    await connect_to_mongo()
    db = await get_db()
    await init_db(db) # 使用get_db()获取数据库连接

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行的操作"""
    await close_mongo_connection()

# 根路径
@app.get("/")
async def root():
    return {"message": f"欢迎使用 {settings.PROJECT_NAME} API"}

# 健康检查端点
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
    )