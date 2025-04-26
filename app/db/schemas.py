from typing import List, Dict, Any

# 既有的集合名称常量
ARTIST_INFO_COLLECTION = "artist_info"
ARTIST_STATS_COLLECTION = "artist_stats"
ALBUM_INFO_COLLECTION = "album_info"
ALBUM_STATS_COLLECTION = "album_stats"
TRACK_INFO_COLLECTION = "track_info"
TRACK_STATS_COLLECTION = "track_stats"
DOWNLOAD_TASKS_COLLECTION = "download_tasks"

USERS_COLLECTION = "users"
PLAYLISTS_COLLECTION = "playlists"
USER_LIBRARY_COLLECTION = "user_library"
PLAY_HISTORY_COLLECTION = "play_history"
SETTINGS_COLLECTION = "settings"
SEARCH_CACHE_COLLECTION = "search_cache"

# 状态常量
STATUS_PENDING = "pending"
STATUS_IN_PROGRESS = "in_progress"
STATUS_SUCCESS = "success"
STATUS_FAILED = "failed"

# 任务类型常量
TASK_TYPE_TRACK = "track"
TASK_TYPE_ALBUM = "album"
TASK_TYPE_ARTIST = "artist"

# 索引定义
COLLECTION_INDEXES = {
    # 已有的集合索引
    ARTIST_INFO_COLLECTION: [
        {"key": [("info.name", "text")]},
        {"key": [("info.genres", 1)]},
        {"key": [("info.popularity", -1)]},
    ],
    ARTIST_STATS_COLLECTION: [
        {"key": [("status", 1)]},
        {"key": [("artist_name", "text")]},
    ],
    ALBUM_INFO_COLLECTION: [
        {"key": [("info.artists.id", 1)]},
        {"key": [("info.name", "text")]},
        {"key": [("info.release_date", -1)]},
    ],
    ALBUM_STATS_COLLECTION: [
        {"key": [("artist_id", 1)]},
        {"key": [("status", 1)]},
    ],
    TRACK_INFO_COLLECTION: [
        {"key": [("info.artists.id", 1)]},
        {"key": [("info.album.id", 1)]},
        {"key": [("info.name", "text")]},
        {"key": [("info.popularity", -1)]},
    ],
    TRACK_STATS_COLLECTION: [
        {"key": [("artist_id", 1)]},
        {"key": [("status", 1)]},
    ],
    DOWNLOAD_TASKS_COLLECTION: [
        {"key": [("priority", 1), ("status", 1), ("created_at", 1)]},
        {"key": [("entity_id", 1), ("task_type", 1)]},
        {"key": [("status", 1), ("created_at", 1)]},
        {"key": [("worker_id", 1)]},
    ],
    
    # 新增的集合索引
    USERS_COLLECTION: [
        {"key": [("username", 1)], "unique": True},
        {"key": [("email", 1)], "unique": True},
        {"key": [("role", 1)]},
    ],
    PLAYLISTS_COLLECTION: [
        {"key": [("user_id", 1)]},
        {"key": [("name", "text"), ("description", "text")]},
        {"key": [("tracks.track_id", 1)]},
        {"key": [("public", 1)]},
    ],
    USER_LIBRARY_COLLECTION: [
        {"key": [("user_id", 1), ("item_type", 1)]},
        {"key": [("item_id", 1), ("item_type", 1)]},
        {"key": [("added_at", -1)]},
    ],
    PLAY_HISTORY_COLLECTION: [
        {"key": [("user_id", 1), ("played_at", -1)]},
        {"key": [("track_id", 1)]},
    ],
    SEARCH_CACHE_COLLECTION: [
        {"key": [("query", 1), ("type", 1)]},
        {"key": [("expires_at", 1)], "expireAfterSeconds": 0},
    ],
}

async def setup_indexes(db):
    """
    设置所有集合的索引
    
    参数:
        db: 异步 MongoDB 数据库对象
    """
    for collection_name, indexes in COLLECTION_INDEXES.items():
        for index_spec in indexes:
            try:
                await db[collection_name].create_index(**index_spec)
            except Exception as e:
                print(f"创建索引时出错 ({collection_name}): {e}")


async def init_db(db):
    """
    初始化数据库模式，创建必要的集合和索引
    
    参数:
        db: 异步 MongoDB 数据库对象
    """
    # 确保所有集合存在
    collections = [
        ARTIST_INFO_COLLECTION,
        ARTIST_STATS_COLLECTION,
        ALBUM_INFO_COLLECTION,
        ALBUM_STATS_COLLECTION,
        TRACK_INFO_COLLECTION,
        TRACK_STATS_COLLECTION,
        DOWNLOAD_TASKS_COLLECTION,
        USERS_COLLECTION,
        PLAYLISTS_COLLECTION,
        USER_LIBRARY_COLLECTION,
        PLAY_HISTORY_COLLECTION,
        SETTINGS_COLLECTION,
        SEARCH_CACHE_COLLECTION,
    ]
    
    existing_collections = await db.list_collection_names()
    
    for collection in collections:
        if collection not in existing_collections:
            await db.create_collection(collection)
    
    # 为search_cache集合创建TTL索引时使用特殊处理
    if SEARCH_CACHE_COLLECTION not in existing_collections:
        await db.create_collection(SEARCH_CACHE_COLLECTION)
    
    # 设置索引
    await setup_indexes(db)