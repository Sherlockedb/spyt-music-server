from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from bson import ObjectId

from app.db.base_repository import BaseRepository
from app.db.schemas import USER_LIBRARY_COLLECTION, PLAY_HISTORY_COLLECTION

class UserLibraryRepository(BaseRepository):
    """
    用户媒体库仓库，处理用户收藏项目
    """

    def __init__(self, db):
        """初始化仓库"""
        super().__init__(db, USER_LIBRARY_COLLECTION)

    async def add_item(self, user_id: str, item_id: str, item_type: str) -> str:
        """
        添加项目到用户媒体库

        参数:
            user_id: 用户ID
            item_id: 项目ID (track_id, album_id, artist_id)
            item_type: 项目类型 (track, album, artist)

        返回:
            添加的条目ID
        """
        # 检查项目是否已存在
        existing = await self.find_one({
            "user_id": ObjectId(user_id),
            "item_id": item_id,
            "item_type": item_type
        })

        if existing:
            # 如果已存在，更新添加时间
            await self.update_one(
                {"_id": existing["_id"]},
                {"$set": {"added_at": datetime.now(timezone.utc)}}
            )
            return str(existing["_id"])

        # 创建新条目
        item = {
            "user_id": ObjectId(user_id),
            "item_id": item_id,
            "item_type": item_type,
            "added_at": datetime.now(timezone.utc),
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }

        return await self.insert_one(item)

    async def remove_item(self, user_id: str, item_id: str, item_type: str) -> bool:
        """从用户媒体库中移除项目"""
        result = await self.delete_one({
            "user_id": ObjectId(user_id),
            "item_id": item_id,
            "item_type": item_type
        })

        return result

    async def check_item(self, user_id: str, item_id: str, item_type: str) -> bool:
        """检查项目是否在用户媒体库中"""
        item = await self.find_one({
            "user_id": ObjectId(user_id),
            "item_id": item_id,
            "item_type": item_type
        })

        return item is not None

    async def get_user_items(self, user_id: str, item_type: str, skip: int = 0, limit: int = 50) -> List[Dict[str, Any]]:
        """获取用户媒体库中特定类型的所有项目"""
        return await self.find(
            {"user_id": ObjectId(user_id), "item_type": item_type},
            skip=skip,
            limit=limit,
            sort=[("added_at", -1)]
        )

    async def get_user_item_ids(self, user_id: str, item_type: str) -> List[str]:
        """获取用户媒体库中特定类型的所有项目ID"""
        items = await self.find(
            {"user_id": ObjectId(user_id), "item_type": item_type},
            sort=[("added_at", -1)]
        )

        return [item["item_id"] for item in items]

class PlayHistoryRepository(BaseRepository):
    """
    播放历史仓库，处理用户的播放记录
    """

    def __init__(self, db):
        """初始化仓库"""
        super().__init__(db, PLAY_HISTORY_COLLECTION)

    async def add_play_record(self, user_id: str, track_id: str, play_duration_ms: int = 0, 
                             play_context: Dict[str, Any] = None) -> str:
        """
        添加播放记录

        参数:
            user_id: 用户ID
            track_id: 曲目ID
            play_duration_ms: 播放时长(毫秒)
            play_context: 播放上下文，如来源类型和ID

        返回:
            记录ID
        """
        record = {
            "user_id": ObjectId(user_id),
            "track_id": track_id,
            "played_at": datetime.now(timezone.utc),
            "play_duration_ms": play_duration_ms,
            "play_context": play_context or {},
            "created_at": datetime.now(timezone.utc)
        }

        return await self.insert_one(record)

    async def get_user_play_history(self, user_id: str, skip: int = 0, limit: int = 50) -> List[Dict[str, Any]]:
        """获取用户的播放历史"""
        return await self.find(
            {"user_id": ObjectId(user_id)},
            skip=skip,
            limit=limit,
            sort=[("played_at", -1)]
        )

    async def get_track_play_count(self, track_id: str) -> int:
        """获取曲目的播放次数"""
        return await self.count({"track_id": track_id})

    async def get_user_track_play_count(self, user_id: str, track_id: str) -> int:
        """获取用户对特定曲目的播放次数"""
        return await self.count({
            "user_id": ObjectId(user_id),
            "track_id": track_id
        })

    async def get_recently_played_tracks(self, user_id: str, limit: int = 20) -> List[str]:
        """获取用户最近播放的曲目ID列表"""
        records = await self.find(
            {"user_id": ObjectId(user_id)},
            limit=limit,
            sort=[("played_at", -1)]
        )

        # 返回不重复的曲目ID
        track_ids = []
        for record in records:
            track_id = record["track_id"]
            if track_id not in track_ids:
                track_ids.append(track_id)

        return track_ids