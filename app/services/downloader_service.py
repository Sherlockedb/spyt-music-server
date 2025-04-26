import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

from app.downloader.mongo_downloader import MongoDBSpotifyDownloader
from app.db.repositories.download_tasks import DownloadTaskRepository
from app.db.repositories.spotify_data import SpotifyDataRepository
from app.db.schemas import (
    TASK_TYPE_TRACK, TASK_TYPE_ALBUM, TASK_TYPE_ARTIST,
    STATUS_PENDING, STATUS_IN_PROGRESS, STATUS_SUCCESS, STATUS_FAILED
)
from app.core.config import settings

class DownloaderService:
    """
    下载服务，处理下载任务的创建和执行
    """
    
    def __init__(self, db, spotify_repo: SpotifyDataRepository, task_repo: DownloadTaskRepository):
        """
        初始化下载服务
        
        参数:
            db: 数据库实例
            spotify_repo: Spotify数据仓库
            task_repo: 下载任务仓库
        """
        self.db = db
        self.spotify_repo = spotify_repo
        self.task_repo = task_repo
        
        # 创建同步下载器 - 注意这里使用同步MongoDB客户端
        self.downloader = MongoDBSpotifyDownloader(
            mongodb_url=settings.MONGODB_URL,
            db_name=settings.MONGODB_DB,
            client_id=settings.SPOTIFY_CLIENT_ID,
            client_secret=settings.SPOTIFY_CLIENT_SECRET,
            output_root=settings.MUSIC_LIBRARY_PATH
        )
    
    async def create_track_download_task(self, track_id: str, priority: int = 5, force: bool = False) -> str:
        """
        创建曲目下载任务
        
        参数:
            track_id: Spotify 曲目ID
            priority: 优先级 (1-10，1为最高)
            force: 是否强制下载，即使已存在成功下载记录
            
        返回:
            任务ID
        """
        # 获取曲目信息，如果本地没有则从Spotify API获取
        track_info = await self.spotify_repo.get_track_info(track_id)
        
        if not track_info:
            try:
                # 这里使用下载器的Spotify客户端获取曲目信息
                track_info = {'info': self.downloader.sp.track(track_id)}
                
                # 保存到数据库
                await self.spotify_repo.save_track_info(track_id, track_info['info'])
            except Exception as e:
                logging.error(f"获取曲目信息失败: {e}")
                raise
        
        # 提取曲目名称
        track_name = track_info['info']['name'] if 'info' in track_info else "未知曲目"
        
        # 创建下载任务
        return await self.task_repo.create_task(
            task_type=TASK_TYPE_TRACK,
            entity_id=track_id,
            entity_name=track_name,
            priority=priority,
            force=force,
        )
    
    async def create_album_download_task(self, album_id: str, filter_artist_id: str = None, 
                                        priority: int = 5, force: bool = False) -> str:
        """
        创建专辑下载任务
        
        参数:
            album_id: Spotify 专辑ID
            filter_artist_id: 可选，过滤特定艺术家的曲目
            priority: 优先级 (1-10，1为最高)
            force: 是否强制下载，即使已存在成功下载记录
            
        返回:
            任务ID
        """
        # 获取专辑信息
        album_info = await self.spotify_repo.get_album_info(album_id)
        
        if not album_info:
            try:
                album_info = {'info': self.downloader.sp.album(album_id)}
                await self.spotify_repo.save_album_info(album_id, album_info['info'])
            except Exception as e:
                logging.error(f"获取专辑信息失败: {e}")
                raise
        
        # 提取专辑名称
        album_name = album_info['info']['name'] if 'info' in album_info else "未知专辑"
        
        # 创建下载任务，添加过滤艺术家选项
        options = {}
        if filter_artist_id:
            options['filter_artist_id'] = filter_artist_id
        
        return await self.task_repo.create_task(
            task_type=TASK_TYPE_ALBUM,
            entity_id=album_id,
            entity_name=album_name,
            priority=priority,
            options=options,
            force=force
        )
    
    async def create_artist_download_task(self, artist_id: str, include_singles: bool = True,
                                         include_appears_on: bool = False, min_tracks: int = 0,
                                         priority: int = 5, force: bool = False) -> str:
        """
        创建艺术家下载任务
        
        参数:
            artist_id: Spotify 艺术家ID
            include_singles: 是否包含单曲
            include_appears_on: 是否包含艺术家参与的专辑
            min_tracks: 仅下载包含至少指定数量歌曲的专辑，0表示不限制
            priority: 优先级 (1-10，1为最高)
            force: 是否强制下载，即使已存在成功下载记录
            
        返回:
            任务ID
        """
        # 获取艺术家信息
        artist_info = await self.spotify_repo.get_artist_info(artist_id)
        
        if not artist_info:
            try:
                artist_info = {'info': self.downloader.sp.artist(artist_id)}
                await self.spotify_repo.save_artist_info(artist_id, artist_info['info'])
            except Exception as e:
                logging.error(f"获取艺术家信息失败: {e}")
                raise
        
        # 提取艺术家名称
        artist_name = artist_info['info']['name'] if 'info' in artist_info else "未知艺术家"
        
        # 创建下载任务，添加选项
        options = {
            'include_singles': include_singles,
            'include_appears_on': include_appears_on,
            'min_tracks': min_tracks
        }
        
        return await self.task_repo.create_task(
            task_type=TASK_TYPE_ARTIST,
            entity_id=artist_id,
            entity_name=artist_name,
            priority=priority,
            options=options,
            force=force
        )
    
    async def execute_task(self, task_id: str, worker_id: str) -> bool:
        """
        执行下载任务
        
        参数:
            task_id: 任务ID
            worker_id: 工作者ID
            
        返回:
            bool: 是否成功
        """
        # 获取任务信息
        task = await self.task_repo.find_one({"task_id": task_id})
        if not task:
            logging.error(f"任务不存在: {task_id}")
            return False
        
        # 检查任务状态
        if task['status'] != STATUS_IN_PROGRESS:
            logging.warning(f"任务状态不是 '{STATUS_IN_PROGRESS}': {task['status']}")
            return False
        
        # 检查工作者ID是否匹配
        if task['worker_id'] != worker_id:
            logging.warning(f"工作者ID不匹配: {task['worker_id']} != {worker_id}")
            return False
        
        try:
            # 根据任务类型执行下载
            task_type = task['task_type']
            entity_id = task['entity_id']
            
            success = False
            error_msg = None
            
            if task_type == TASK_TYPE_TRACK:
                # 获取当前运行的事件循环
                loop = asyncio.get_running_loop()
                # 下载单曲 - 在线程池中运行同步方法
                success, stats, info, files = await loop.run_in_executor(
                    None,
                    lambda: self.downloader.download_track(
                        track_id=entity_id,
                        save=True,
                        load=True
                    )
                )
            
            elif task_type == TASK_TYPE_ALBUM:
                # 下载专辑
                options = task.get('options', {})
                filter_artist_id = options.get('filter_artist_id')
                
                success, stats, info, files = await self.downloader.download_album(
                    album_id=entity_id,
                    filter_artist_id=filter_artist_id,
                    save=True,
                    load=True
                )
                
                # 更新进度信息
                if stats:
                    completed = stats.get('success', 0)
                    failed = stats.get('failed', 0)
                    total = stats.get('total', 0)
                    
                    await self.task_repo.update_task_progress(task_id, completed, failed, total)
            
            elif task_type == TASK_TYPE_ARTIST:
                # 下载艺术家
                options = task.get('options', {})
                include_singles = options.get('include_singles', True)
                include_appears_on = options.get('include_appears_on', False)
                min_tracks = options.get('min_tracks', 0)
                
                success, stats, info, files = await self.downloader.download_artist(
                    artist_id=entity_id,
                    include_singles=include_singles,
                    include_appears_on=include_appears_on,
                    min_tracks=min_tracks,
                    save=True,
                    load=True
                )
                
                # 更新进度信息
                if stats:
                    total_albums = stats.get('total_albums', 0)
                    successful_albums = stats.get('successful_albums', 0)
                    failed_albums = stats.get('failed_albums', 0)
                    
                    await self.task_repo.update_task_progress(
                        task_id, 
                        successful_albums, 
                        failed_albums, 
                        total_albums
                    )
            
            else:
                error_msg = f"未知任务类型: {task_type}"
                logging.error(error_msg)
                
            # 完成任务
            if error_msg:
                await self.task_repo.complete_task(task_id, False, error_msg)
                return False
            else:
                await self.task_repo.complete_task(task_id, success)
                return success
                
        except Exception as e:
            error_msg = f"执行任务时出错: {str(e)}"
            logging.error(error_msg)
            
            # 记录错误并将任务标记为失败
            await self.task_repo.complete_task(task_id, False, error_msg)
            return False