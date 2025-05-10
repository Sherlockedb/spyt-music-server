import logging
from typing import Dict, List, Optional, Any
from cachetools import TTLCache
from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials

from app.core.config import settings
from app.db.repositories.spotify_data import SpotifyDataRepository
from app.db.repositories.search_cache import SearchCacheRepository

class SpotifyService:
    """
    Spotify API服务，处理搜索和元数据获取
    """

    def __init__(self, spotify_repo: SpotifyDataRepository,
        search_cache_repo: Optional[SearchCacheRepository] = None):
        """
        初始化Spotify服务

        参数:
            spotify_repo: Spotify数据仓库
            search_cache_repo: 搜索缓存仓库（可选）
        """
        self.spotify_repo = spotify_repo
        self.search_cache_repo = search_cache_repo

        # 初始化Spotify客户端
        self.client = Spotify(auth_manager=SpotifyClientCredentials(
            client_id=settings.SPOTIFY_CLIENT_ID,
            client_secret=settings.SPOTIFY_CLIENT_SECRET
        ))

        # 初始化内存缓存，用于减少API调用
        # 缓存搜索结果10分钟
        self.search_cache = TTLCache(maxsize=100, ttl=600)

    async def search(self, query: str, search_type: str = "track,album,artist", limit: int = 20) -> Dict[str, List[Dict[str, Any]]]:
        """
        搜索Spotify

        参数:
            query: 搜索关键词
            search_type: 搜索类型，可以是track,album,artist的组合
            limit: 每种类型的结果数量限制

        返回:
            Dict: 搜索结果
        """
        cache_key = f"{query}:{search_type}:{limit}"

        # 检查缓存
        if cache_key in self.search_cache:
            logging.info(f"使用缓存的搜索结果: {query}")
            return self.search_cache[cache_key]

        # 检查数据库缓存
        if self.search_cache_repo:
            db_cached = await self.search_cache_repo.get_cached_search(query, search_type, limit)
            if db_cached:
                logging.info(f"使用数据库缓存的搜索结果: {query}")
                # 同时更新内存缓存
                self.search_cache[cache_key] = db_cached
                return db_cached

        try:
            # 调用Spotify API搜索
            logging.info(f"搜索Spotify: {query}, 类型: {search_type}")
            results = self.client.search(q=query, type=search_type, limit=limit)

            # 格式化结果
            formatted_results = self._format_search_results(results)

            # 更新内存缓存
            self.search_cache[cache_key] = formatted_results

            # 更新数据库缓存
            if self.search_cache_repo:
                await self.search_cache_repo.cache_search(
                    query=query,
                    search_type=search_type,
                    limit=limit,
                    results=formatted_results,
                    ttl_seconds=3600  # 1小时
                )

            return formatted_results

        except Exception as e:
            logging.error(f"Spotify搜索失败: {e}")
            raise

    def _format_search_results(self, results: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """
        格式化搜索结果，提取关键信息

        参数:
            results: Spotify API返回的原始结果

        返回:
            Dict: 格式化后的结果
        """
        formatted = {}

        # 处理曲目
        if 'tracks' in results and 'items' in results['tracks']:
            formatted['tracks'] = []
            for item in results['tracks']['items']:
                track = {
                    'id': item['id'],
                    'name': item['name'],
                    'artists': [{'id': artist['id'], 'name': artist['name']} for artist in item['artists']],
                    'album': {
                        'id': item['album']['id'],
                        'name': item['album']['name'],
                        'images': item['album']['images'] if 'images' in item['album'] else []
                    },
                    'duration_ms': item['duration_ms'],
                    'popularity': item['popularity']
                }
                formatted['tracks'].append(track)

        # 处理专辑
        if 'albums' in results and 'items' in results['albums']:
            formatted['albums'] = []
            for item in results['albums']['items']:
                album = {
                    'id': item['id'],
                    'name': item['name'],
                    'artists': [{'id': artist['id'], 'name': artist['name']} for artist in item['artists']],
                    'release_date': item['release_date'],
                    'total_tracks': item['total_tracks'],
                    'images': item['images'] if 'images' in item else []
                }
                formatted['albums'].append(album)

        # 处理艺术家
        if 'artists' in results and 'items' in results['artists']:
            formatted['artists'] = []
            for item in results['artists']['items']:
                artist = {
                    'id': item['id'],
                    'name': item['name'],
                    'genres': item['genres'] if 'genres' in item else [],
                    'popularity': item['popularity'],
                    'images': item['images'] if 'images' in item else []
                }
                formatted['artists'].append(artist)

        return formatted

    async def get_track_info(self, track_id: str) -> Optional[Dict[str, Any]]:
        """
        获取曲目信息

        参数:
            track_id: Spotify曲目ID

        返回:
            Dict: 曲目信息
        """
        # 先尝试从数据库获取
        track_info = await self.spotify_repo.get_track_info(track_id)

        if track_info:
            return track_info

        try:
            # 从Spotify API获取
            logging.info(f"从Spotify API获取曲目信息: {track_id}")
            raw_info = self.client.track(track_id)

            # 保存到数据库
            await self.spotify_repo.save_track_info(track_id, raw_info)

            return {'info': raw_info}

        except Exception as e:
            logging.error(f"获取曲目信息失败: {e}")
            return None

    async def get_album_info(self, album_id: str) -> Optional[Dict[str, Any]]:
        """
        获取专辑信息

        参数:
            album_id: Spotify专辑ID

        返回:
            Dict: 专辑信息
        """
        # 先尝试从数据库获取
        album_info = await self.spotify_repo.get_album_info(album_id)

        if album_info:
            return album_info

        try:
            # 从Spotify API获取
            logging.info(f"从Spotify API获取专辑信息: {album_id}")
            raw_info = self.client.album(album_id)

            # 保存到数据库
            await self.spotify_repo.save_album_info(album_id, raw_info)

            return {'info': raw_info}

        except Exception as e:
            logging.error(f"获取专辑信息失败: {e}")
            return None

    async def get_artist_info(self, artist_id: str) -> Optional[Dict[str, Any]]:
        """
        获取艺术家信息

        参数:
            artist_id: Spotify艺术家ID

        返回:
            Dict: 艺术家信息
        """
        # 先尝试从数据库获取
        artist_info = await self.spotify_repo.get_artist_info(artist_id)

        if artist_info:
            return artist_info

        try:
            # 从Spotify API获取
            logging.info(f"从Spotify API获取艺术家信息: {artist_id}")
            raw_info = self.client.artist(artist_id)

            # 获取艺术家的热门曲目
            top_tracks = self.client.artist_top_tracks(artist_id)
            raw_info['top_tracks'] = top_tracks['tracks']

            # 保存到数据库
            await self.spotify_repo.save_artist_info(artist_id, raw_info)

            return {'info': raw_info}

        except Exception as e:
            logging.error(f"获取艺术家信息失败: {e}")
            return None