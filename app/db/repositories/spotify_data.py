from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from app.db.base_repository import BaseRepository
from app.db.schemas import (
    ARTIST_INFO_COLLECTION, ARTIST_STATS_COLLECTION,
    ALBUM_INFO_COLLECTION, ALBUM_STATS_COLLECTION,
    TRACK_INFO_COLLECTION, TRACK_STATS_COLLECTION
)

class SpotifyDataRepository:
    """
    Spotify 数据仓库，处理 artist/album/track 的 info 和 stats 数据
    """

    def __init__(self, db):
        """初始化仓库"""
        self.db = db
        # 创建各个集合的仓库实例
        self.artist_info = BaseRepository(db, ARTIST_INFO_COLLECTION)
        self.artist_stats = BaseRepository(db, ARTIST_STATS_COLLECTION)
        self.album_info = BaseRepository(db, ALBUM_INFO_COLLECTION)
        self.album_stats = BaseRepository(db, ALBUM_STATS_COLLECTION)
        self.track_info = BaseRepository(db, TRACK_INFO_COLLECTION)
        self.track_stats = BaseRepository(db, TRACK_STATS_COLLECTION)

    # Artist 方法
    async def save_artist_info(self, artist_id: str, info: Dict[str, Any]) -> str:
        """保存艺术家元数据"""
        document = {
            "_id": artist_id,
            "info": info,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        return await self.artist_info.insert_one(document)

    async def get_artist_info(self, artist_id: str) -> Optional[Dict[str, Any]]:
        """获取艺术家元数据"""
        return await self.artist_info.find_one({"_id": artist_id})

    async def save_artist_stats(self, artist_id: str, stats: Dict[str, Any]) -> str:
        """保存艺术家统计信息"""
        # 确保统计信息包含ID
        stats["_id"] = artist_id
        return await self.artist_stats.insert_one(stats)

    async def get_artist_stats(self, artist_id: str) -> Optional[Dict[str, Any]]:
        """获取艺术家统计信息"""
        return await self.artist_stats.find_one({"_id": artist_id})

    async def update_artist_stats(self, artist_id: str, stats: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """更新艺术家统计信息"""
        return await self.artist_stats.update_one({"_id": artist_id}, {"$set": stats}, upsert=True)

    # Album 方法
    async def save_album_info(self, album_id: str, info: Dict[str, Any]) -> str:
        """保存专辑元数据"""
        document = {
            "_id": album_id,
            "info": info,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        return await self.album_info.insert_one(document)

    async def get_album_info(self, album_id: str) -> Optional[Dict[str, Any]]:
        """获取专辑元数据"""
        return await self.album_info.find_one({"_id": album_id})

    async def save_album_stats(self, album_id: str, stats: Dict[str, Any]) -> str:
        """保存专辑统计信息"""
        # 确保统计信息包含ID
        stats["_id"] = album_id
        return await self.album_stats.insert_one(stats)

    async def get_album_stats(self, album_id: str) -> Optional[Dict[str, Any]]:
        """获取专辑统计信息"""
        return await self.album_stats.find_one({"_id": album_id})

    async def update_album_stats(self, album_id: str, stats: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """更新专辑统计信息"""
        return await self.album_stats.update_one({"_id": album_id}, {"$set": stats}, upsert=True)

    async def get_albums_by_artist(self, artist_id: str, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """获取艺术家的所有专辑元数据"""
        return await self.album_info.find({"info.artists.id": artist_id}, skip=skip, limit=limit)

    async def get_album_stats_by_artist(self, artist_id: str, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """获取艺术家的所有专辑统计信息"""
        return await self.album_stats.find({"artist_id": artist_id}, skip=skip, limit=limit)

    # Track 方法
    async def save_track_info(self, track_id: str, info: Dict[str, Any]) -> str:
        """保存曲目元数据"""
        document = {
            "_id": track_id,
            "info": info,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        return await self.track_info.insert_one(document)

    async def get_track_info(self, track_id: str) -> Optional[Dict[str, Any]]:
        """获取曲目元数据"""
        return await self.track_info.find_one({"_id": track_id})

    async def save_track_stats(self, track_id: str, stats: Dict[str, Any]) -> str:
        """保存曲目统计信息"""
        # 确保统计信息包含ID
        stats["_id"] = track_id
        return await self.track_stats.insert_one(stats)

    async def get_track_stats(self, track_id: str) -> Optional[Dict[str, Any]]:
        """获取曲目统计信息"""
        return await self.track_stats.find_one({"_id": track_id})

    async def update_track_stats(self, track_id: str, stats: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """更新曲目统计信息"""
        return await self.track_stats.update_one({"_id": track_id}, {"$set": stats}, upsert=True)

    async def get_tracks_by_album(self, album_id: str, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """获取专辑的所有曲目元数据"""
        return await self.track_info.find({"info.album.id": album_id}, skip=skip, limit=limit)

    async def get_track_stats_by_album(self, album_id: str, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """获取专辑的所有曲目统计信息"""
        # 需要先查询专辑的 stats 信息，因为曲目 stats 中不一定包含 album_id
        album_stats = await self.get_album_stats(album_id)
        if not album_stats or "tracks" not in album_stats:
            return []

        track_ids = list(album_stats["tracks"].keys())
        return await self.track_stats.find({"_id": {"$in": track_ids}}, skip=skip, limit=limit)

    async def get_tracks_by_artist(self, artist_id: str, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """获取艺术家的所有曲目元数据"""
        return await self.track_info.find({"info.artists.id": artist_id}, skip=skip, limit=limit)

    async def get_track_stats_by_artist(self, artist_id: str, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """获取艺术家的所有曲目统计信息"""
        return await self.track_stats.find({"artist_id": artist_id}, skip=skip, limit=limit)

    # 组合搜索方法
    async def get_track_with_download_status(self, track_id: str) -> Dict[str, Any]:
        """获取曲目信息及其下载状态"""
        info = await self.get_track_info(track_id)
        stats = await self.get_track_stats(track_id)

        result = {
            "track_id": track_id,
            "info": info["info"] if info else None,
            "is_downloaded": False,
            "download_path": None,
            "download_status": None
        }

        if stats:
            result["is_downloaded"] = stats.get("status") == "success"
            result["download_path"] = stats.get("path")
            result["download_status"] = stats.get("status")

        return result

    async def search_tracks_by_name(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """通过名称搜索曲目（仅本地数据）"""
        # 使用文本索引进行搜索
        tracks = await self.track_info.find(
            {"$text": {"$search": query}},
            limit=limit,
            sort=[("info.popularity", -1)]
        )

        # 为每个曲目添加下载状态
        results = []
        for track in tracks:
            track_id = track["_id"]
            stats = await self.get_track_stats(track_id)

            result = {
                "track_id": track_id,
                "info": track["info"],
                "is_downloaded": False,
                "download_path": None,
                "download_status": None
            }

            if stats:
                result["is_downloaded"] = stats.get("status") == "success"
                result["download_path"] = stats.get("path")
                result["download_status"] = stats.get("status")

            results.append(result)

        return results

    async def count_tracks_with_files(self) -> int:
        """
        获取有本地文件的曲目数量

        返回:
            int: 曲目数量
        """
        return await self.db["track_stats"].count_documents({"path": {"$exists": True, "$ne": None}})

    async def count_albums_with_files(self) -> int:
        """
        获取有本地文件的专辑数量

        返回:
            int: 专辑数量
        """
        # 假设专辑至少有一首歌曲有本地文件，就认为这个专辑有本地文件
        albums = await self.db["album_stats"].distinct("album_id", {"tracks.path": {"$exists": True, "$ne": None}})
        return len(albums)

    async def count_artists_with_files(self) -> int:
        """
        获取有本地文件的艺术家数量

        返回:
            int: 艺术家数量
        """
        # 获取所有有文件的曲目
        tracks_with_files = await self.db["track_stats"].find(
            {"path": {"$exists": True, "$ne": None}},
            {"artist_id": 1}
        ).to_list(length=None)

        # 提取不重复的艺术家ID
        artist_ids = set()
        for track in tracks_with_files:
            if "artist_id" in track:
                artist_ids.add(track["artist_id"])

        return len(artist_ids)