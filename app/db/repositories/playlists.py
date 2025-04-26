from typing import Dict, List, Optional, Any
from datetime import datetime
from bson import ObjectId

from app.db.base_repository import BaseRepository
from app.db.schemas import PLAYLISTS_COLLECTION

class PlaylistRepository(BaseRepository):
    """
    播放列表数据仓库，处理播放列表相关操作
    """
    
    def __init__(self, db):
        """初始化仓库"""
        super().__init__(db, PLAYLISTS_COLLECTION)
    
    async def create_playlist(self, name: str, user_id: str, description: str = None, 
                             public: bool = True) -> str:
        """
        创建新播放列表
        
        参数:
            name: 播放列表名称
            user_id: 用户ID
            description: 描述（可选）
            public: 是否公开（默认为True）
            
        返回:
            播放列表ID
        """
        playlist = {
            "name": name,
            "description": description,
            "user_id": ObjectId(user_id),
            "public": public,
            "tracks": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        return await self.insert_one(playlist)
    
    async def get_playlist(self, playlist_id: str) -> Optional[Dict[str, Any]]:
        """获取播放列表"""
        return await self.find_one({"_id": ObjectId(playlist_id)})
    
    async def get_user_playlists(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户的所有播放列表"""
        return await self.find({"user_id": ObjectId(user_id)})
    
    async def get_public_playlists(self, skip: int = 0, limit: int = 20) -> List[Dict[str, Any]]:
        """获取公开播放列表"""
        return await self.find({"public": True}, skip=skip, limit=limit)
    
    async def add_track_to_playlist(self, playlist_id: str, track_id: str) -> Optional[Dict[str, Any]]:
        """
        添加曲目到播放列表
        
        参数:
            playlist_id: 播放列表ID
            track_id: 曲目ID
            
        返回:
            更新后的播放列表
        """
        # 获取当前播放列表
        playlist = await self.get_playlist(playlist_id)
        if not playlist:
            return None
        
        # 计算新曲目的位置
        position = len(playlist.get("tracks", []))
        
        # 添加曲目
        update = {
            "$push": {
                "tracks": {
                    "track_id": track_id,
                    "added_at": datetime.utcnow(),
                    "position": position
                }
            },
            "$set": {"updated_at": datetime.utcnow()}
        }
        
        return await self.update_one({"_id": ObjectId(playlist_id)}, update)
    
    async def remove_track_from_playlist(self, playlist_id: str, track_id: str) -> Optional[Dict[str, Any]]:
        """从播放列表中删除曲目"""
        update = {
            "$pull": {"tracks": {"track_id": track_id}},
            "$set": {"updated_at": datetime.utcnow()}
        }
        
        playlist = await self.update_one({"_id": ObjectId(playlist_id)}, update)
        
        # 更新剩余曲目的位置
        if playlist and "tracks" in playlist:
            for i, track in enumerate(playlist["tracks"]):
                track["position"] = i
            
            await self.update_one(
                {"_id": ObjectId(playlist_id)},
                {"$set": {"tracks": playlist["tracks"]}}
            )
        
        return playlist