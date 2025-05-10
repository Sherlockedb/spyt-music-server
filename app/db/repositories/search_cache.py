from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, timezone

from app.db.base_repository import BaseRepository
from app.db.schemas import SEARCH_CACHE_COLLECTION

class SearchCacheRepository(BaseRepository):
    """
    搜索缓存仓库，缓存 Spotify 搜索结果
    """
    
    def __init__(self, db):
        """初始化仓库"""
        super().__init__(db, SEARCH_CACHE_COLLECTION)
    
    async def cache_search(self, query: str, search_type: str, limit: int,
                                   results: List[Dict[str, Any]], ttl_seconds: int = 3600) -> str:
        """
        缓存搜索结果
        
        参数:
            query: 搜索查询
            search_type: 搜索类型 (track, album, artist)
            limit: 结果数量限制
            results: 搜索结果
            ttl_seconds: 缓存有效期(秒)
            
        返回:
            缓存ID
        """
        # 创建缓存条目
        cache_entry = {
            "query": query,
            "type": search_type,
            "limit": limit,
            "results": results,
            "created_at": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
        }
        
        await self.update_one(
            {"query": query, "type": search_type, "limit": limit},
            {"$set": cache_entry},
            upsert=True
        )
        return True
    
    async def get_cached_search(self, query: str, search_type: str, limit: int) -> Optional[List[Dict[str, Any]]]:
        """
        获取缓存的搜索结果
        
        参数:
            query: 搜索查询
            search_type: 搜索类型
            limit: 结果数量限制

        返回:
            缓存的搜索结果，如果不存在或已过期则返回None
        """
        cache = await self.find_one({
            "query": query,
            "type": search_type,
            "limit": limit,
            "expires_at": {"$gt": datetime.now(timezone.utc)}
        })
        
        if cache:
            return cache["results"]
        return None
    
    async def clear_expired_cache(self) -> int:
        """
        清理过期缓存（通常不需要手动调用，因为TTL索引会自动删除过期文档）
        
        返回:
            删除的文档数
        """
        return await self.delete_many({
            "expires_at": {"$lt": datetime.now(timezone.utc)}
        })