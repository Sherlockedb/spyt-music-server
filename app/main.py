from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.core.environment import get_settings
from app.core.init_app import init_app
from app.api.v1.router import api_router


def create_app() -> FastAPI:
    """
    创建 FastAPI 应用
    """
    settings = get_settings()
    
    app = FastAPI(
        title=settings.PROJECT_NAME,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    
    # 初始化应用
    init_app(app)
    
    # 包含 API 路由
    app.include_router(api_router, prefix=settings.API_V1_STR)
    
    @app.get("/")
    async def root():
        return JSONResponse(
            content={
                "message": f"Welcome to {settings.PROJECT_NAME}",
                "docs": "/docs",
            }
        )
    
    @app.get("/health")
    async def health_check():
        return JSONResponse(
            content={"status": "ok"}
        )
    
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
    )