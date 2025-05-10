from typing import Generator
from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorClient

from app.db.repositories.users import UserRepository
from app.services.user_service import UserService
from app.services.downloader_service import DownloaderService
from app.db.repositories.download_tasks import DownloadTaskRepository
from app.db.repositories.spotify_data import SpotifyDataRepository
from app.services.spotify_service import SpotifyService
from app.db.repositories.search_cache import SearchCacheRepository
from app.core.database import get_db

# 获取用户仓库
async def get_user_repository(db=Depends(get_db)) -> UserRepository:
    return UserRepository(db)

# 获取用户服务
async def get_user_service(
    user_repo: UserRepository = Depends(get_user_repository)
) -> UserService:
    return UserService(user_repo)

async def get_spotify_repo(
    db = Depends(get_db)
) -> SpotifyDataRepository:
    """
    获取Spotify数据仓库实例
    """
    return SpotifyDataRepository(db)

async def get_downloader_service(
    db = Depends(get_db),
    spotify_repo: SpotifyDataRepository = Depends(get_spotify_repo),
) -> DownloaderService:
    """
    获取下载服务实例

    依赖项：数据库连接

    返回：
        DownloaderService实例
    """
    # 创建所需的仓库
    task_repo = DownloadTaskRepository(db)

    # 创建下载服务
    downloader_service = DownloaderService(
        db=db,
        spotify_repo=spotify_repo,
        task_repo=task_repo
    )

    return downloader_service

async def get_search_cache_repo(
    db = Depends(get_db)
) -> SearchCacheRepository:
    """
    获取搜索缓存仓库实例
    """
    return SearchCacheRepository(db)

async def get_spotify_service(
    spotify_repo: SpotifyDataRepository = Depends(get_spotify_repo),
    search_cache_repo: SearchCacheRepository = Depends(get_search_cache_repo)
) -> SpotifyService:
    """
    获取Spotify服务实例
    """
    return SpotifyService(
        spotify_repo=spotify_repo,
        search_cache_repo=search_cache_repo
    )
