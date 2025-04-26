from spotdl.download.downloader import Downloader
from spotdl.types.album import Album
from spotdl.types.artist import Artist
from spotdl.types.song import Song
from spotdl.utils.spotify import SpotifyClient
from spotdl.types.options import DownloaderOptions
import logging
import sys
import os
import time
import json
from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials

class BaseSpotifyDownloader:
    """
    通用的 Spotify 下载器类，提供统一接口下载单曲、专辑和艺术家的音乐
    """

    def __init__(self, client_id=None, client_secret=None, output_root="music_lib", 
                 output_format="{album}/[{artists}] {track-number}-{title}.{output-ext}",
                 use_artist_dir=True, max_retries=3, retry_delay=5,
                 log_file=None):
        """
        初始化 BaseSpotifyDownloader 类

        参数:
            client_id: Spotify API 客户端 ID
            client_secret: Spotify API 客户端密钥
            output_root: 输出根目录
            output_format: 输出文件格式（不含艺术家目录部分）
            use_artist_dir: 是否使用艺术家名称作为上层目录
            max_retries: 下载重试次数
            retry_delay: 重试间隔时间(秒)
            log_file: 日志文件路径，如果指定则同时输出到控制台和文件
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.output_root = output_root
        self.output_format = output_format
        self.use_artist_dir = use_artist_dir
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # 配置日志
        self._setup_logging(log_file)

        # 初始化 Spotify 客户端
        self._init_spotify_client()

        # 不可重试的错误类型模式
        self.non_retryable_errors = ["LookupError"]

    def _setup_logging(self, log_file=None):
        """设置日志配置，同时输出到控制台和文件"""
        log_handlers = [logging.StreamHandler()]
        if log_file:
            log_dir = os.path.dirname(log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
            log_handlers.append(logging.FileHandler(log_file, encoding='utf-8'))

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=log_handlers
        )

    def _init_spotify_client(self):
        """初始化 Spotify 客户端"""
        try:
            # 初始化 SpotifyClient
            if self.client_id and self.client_secret:
                try:
                    SpotifyClient.init(
                        client_id=self.client_id,
                        client_secret=self.client_secret
                    )
                except Exception as e:
                    # 如果已经初始化，忽略错误
                    if "already been initialized" not in str(e):
                        raise

            # 初始化 spotipy 客户端，用于更多的 Spotify API 功能
            self.sp = Spotify(auth_manager=SpotifyClientCredentials(
                client_id=self.client_id,
                client_secret=self.client_secret
            ))
        except Exception as e:
            logging.error(f"初始化 Spotify 客户端出错: {e}")
            raise

    def is_retryable_error(self, error_msg):
        """判断错误是否可以重试"""
        error_str = str(error_msg).lower()

        # 检查是否匹配任何不可重试的错误模式
        for pattern in self.non_retryable_errors:
            if pattern.lower() in error_str:
                return False

        # 如果没有匹配到不可重试的错误，假定是网络错误或其他可重试的错误
        return True

    def get_output_format(self, artist_name=None):
        """
        根据配置和艺术家名称构建输出格式

        参数:
            artist_name: 艺术家名称，如果为 None 则不添加艺术家目录

        返回:
            str: 完整的输出格式字符串
        """
        if artist_name and self.use_artist_dir:
            # 使用艺术家名称作为上层目录
            artist_safe_name = artist_name.replace('/', '_').replace('\\', '_')
            return os.path.join(self.output_root, artist_safe_name, self.output_format)
        else:
            # 不使用艺术家名称
            return os.path.join(self.output_root, self.output_format)

    # 将基类中的存储和加载方法修改为抛出异常
    def _save_stats(self, entity_type, entity_id, stats):
        """
        保存统计信息，需要被子类重写
        """
        raise NotImplementedError("_save_stats must be implemented by subclass")

    def _save_info(self, entity_type, entity_id, info):
        """
        保存元数据信息，需要被子类重写
        """
        raise NotImplementedError("_save_info must be implemented by subclass")

    def _load_stats(self, entity_type, entity_id):
        """
        加载统计信息，需要被子类重写
        """
        raise NotImplementedError("_load_stats must be implemented by subclass")

    def _load_info(self, entity_type, entity_id):
        """
        加载元数据信息，需要被子类重写
        """
        raise NotImplementedError("_load_info must be implemented by subclass")

    def download_track(self, track_id, artist_id=None, save=True, load=True):
        """
        下载单曲

        参数:
            track_id: Spotify 曲目 ID
            save: 是否保存统计和元数据信息
            load: 是否尝试加载已有的统计和元数据信息

        返回:
            (bool, dict, dict, list): 
                - success: 下载是否成功
                - stats: 下载统计信息
                - info: 曲目信息
                - downloaded_files: 下载的文件列表
        """
        # 尝试加载已有数据
        if load:
            stats = self._load_stats('track', track_id)
            info = self._load_info('track', track_id)

            if stats and info and stats.get('status') == 'success' and stats.get('path'):
                logging.info(f"曲目 {track_id} 已存在，直接返回缓存数据")
                return True, stats, info, [stats.get('path')]

        try:
            # 获取曲目信息
            track_info = self.sp.track(track_id)
            track_name = track_info['name']
            artist_infos = track_info['artists']
            artist_id, artist_name = next(
                ((artist['id'], artist['name']) for artist in artist_infos if artist_id and artist['id'] == artist_id),
                (artist_infos[0]['id'], artist_infos[0]['name'])  # 默认值：第一个艺术家
            )

            track_url = track_info['external_urls']['spotify']

            logging.info(f"开始下载曲目: {track_name}")

            # 构建输出格式
            output_format = self.get_output_format(artist_name)

            # 创建下载选项
            settings = DownloaderOptions(
                output=output_format,
                lyrics=True,
                threads=1,
                simple_tui=True
            )

            # 创建下载器实例
            downloader = Downloader(settings=settings)

            # 从 Spotify URL 获取歌曲信息
            song = Song.from_url(track_url)

            if not song:
                logging.error(f"无法获取曲目信息: {track_url}")
                stats = {
                    "track_id": track_id,
                    "name": track_name,
                    "artist_id": artist_id,
                    "artist_name": artist_name,
                    "status": "failed",
                    "error": "无法获取曲目信息",
                    "path": None
                }
                if save:
                    self._save_stats('track', track_id, stats)
                    self._save_info('track', track_id, track_info)
                return False, stats, track_info, []

            # 统计信息
            stats = {
                "track_id": track_id,
                "name": track_name,
                "artist_id": artist_id,
                "artist_name": artist_name,
                "retried": 0,
                "status": "failed",
                "error": None,
                "path": None,
                "non_retryable": False  # 标记是否是不可重试的错误
            }

            # 下载曲目
            retry_count = 0
            success = False
            downloaded_files = []

            while not success and retry_count <= self.max_retries:
                try:
                    if retry_count > 0:
                        logging.info(f"重试下载曲目 '{track_name}' (尝试 {retry_count}/{self.max_retries})")
                        stats["retried"] += 1
                        time.sleep(self.retry_delay)

                    # 清除之前的错误
                    downloader.errors = []

                    # 下载单曲
                    result = downloader.download_song(song)

                    # 检查下载器错误
                    if downloader.errors:
                        error_msg = "; ".join(str(e) for e in downloader.errors)
                        logging.warning(f"下载器报告错误: {error_msg}")
                        raise Exception(f"下载错误: {error_msg}")

                    # 处理返回值
                    if result and len(result) == 2 and result[1] is not None:
                        _, file_path = result
                        file_path_str = str(file_path)
                        downloaded_files.append(file_path_str)
                        logging.info(f"曲目 '{track_name}' 下载成功: {file_path_str}")
                        stats["status"] = "success"
                        stats["error"] = None
                        stats["path"] = file_path_str
                        success = True
                    else:
                        raise Exception("下载完成但未找到文件")

                except Exception as e:
                    error_msg = str(e)

                    # 检查是否是不可重试的错误
                    if not self.is_retryable_error(error_msg) or retry_count == self.max_retries:
                        if not self.is_retryable_error(error_msg):
                            logging.warning(f"曲目 '{track_name}' 下载失败，不可重试的错误: {error_msg}")
                            stats["non_retryable"] = True  # 标记为不可重试错误
                        else:
                            logging.error(f"曲目 '{track_name}' 下载失败，已重试最大次数: {error_msg}")

                        stats["error"] = error_msg
                        break
                    else:
                        logging.warning(f"曲目 '{track_name}' 下载出错(可重试): {error_msg}")

                retry_count += 1

            # 保存统计信息和元数据
            if save:
                self._save_stats('track', track_id, stats)
                self._save_info('track', track_id, track_info)

            return success, stats, track_info, downloaded_files

        except Exception as e:
            logging.error(f"下载曲目时出错: {e}")
            import traceback
            traceback.print_exc()

            # 创建错误状态
            stats = {
                "track_id": track_id,
                "status": "failed",
                "error": str(e)
            }

            # 尝试保存错误状态
            if save:
                self._save_stats('track', track_id, stats)

            return False, stats, {}, []

    def download_album(self, album_id, filter_artist_id=None, save=True, load=True):
        """
        下载专辑

        参数:
            album_id: Spotify 专辑 ID
            filter_artist_id: 可选，过滤特定艺术家的曲目，只下载与该艺术家相关的曲目
            save: 是否保存统计和元数据信息
            load: 是否尝试加载已有的统计和元数据信息

        返回:
            (bool, dict, dict, list): 
                - success: 下载是否成功
                - stats: 下载统计信息
                - info: 专辑信息
                - downloaded_files: 下载的文件列表
        """
        # 尝试加载已有数据
        if load:
            stats = self._load_stats('album', album_id)
            info = self._load_info('album', album_id)

            if stats and info and stats.get('status') == 'success' and stats.get('tracks'):
                # 收集已下载的文件路径
                downloaded_files = []
                for track_stats in stats.get('tracks', {}).values():
                    if track_stats.get('path'):
                        downloaded_files.append(track_stats.get('path'))

                logging.info(f"专辑 {album_id} 已存在，直接返回缓存数据")
                return True, stats, info, downloaded_files

        try:
            # 获取专辑信息
            album_info = self.sp.album(album_id)
            album_name = album_info['name']
            artist_id = album_info['artists'][0]['id']
            artist_name = album_info['artists'][0]['name']

            logging.info(f"开始下载专辑: {album_name}")

            # 获取专辑中的所有曲目
            tracks = []
            results = self.sp.album_tracks(album_id, limit=50)

            while results:
                for item in results['items']:
                    track_id = item['id']

                    # 如果指定了过滤艺术家ID，检查曲目艺术家列表中是否包含该艺术家
                    if filter_artist_id:
                        track_artist_ids = [artist['id'] for artist in item['artists']]
                        if filter_artist_id not in track_artist_ids:
                            logging.info(f"跳过曲目 '{item['name']}'，艺术家ID {filter_artist_id} 不在曲目艺术家列表中")
                            continue

                    tracks.append((track_id, item['name']))

                # 获取下一页结果
                if results['next']:
                    results = self.sp.next(results)
                else:
                    results = None

            '''
            if not tracks:
                logging.error(f"专辑 '{album_name}' 中没有找到歌曲" + 
                            (f"（与艺术家ID {filter_artist_id} 相关）" if filter_artist_id else ""))
                stats = {
                    "album_id": album_id,
                    "album_name": album_name,
                    "artist_id": artist_id,
                    "artist_name": artist_name,
                    "filter_artist_id": filter_artist_id,
                    "status": "failed",
                    "error": "专辑中没有找到歌曲" + 
                            (f"（与艺术家ID {filter_artist_id} 相关）" if filter_artist_id else ""),
                    "total": 0,
                    "success": 0,
                    "failed": 0,
                    "non_retryable": 0,
                    "tracks": {}
                }
                if save:
                    self._save_stats('album', album_id, stats)
                    self._save_info('album', album_id, album_info)
                return False, stats, album_info, []
            '''

            # 统计信息
            stats = {
                "album_id": album_id,
                "album_name": album_name,
                "artist_id": artist_id,
                "artist_name": artist_name,
                "filter_artist_id": filter_artist_id,
                "total": len(tracks),
                "success": 0,
                "failed": 0,
                "non_retryable": 0,
                "retried": 0,
                "status": "failed",
                "tracks": {}
            }

            # 下载专辑中的所有歌曲
            downloaded_files = []

            for track_id, track_name in tracks:
                # 使用 download_track 方法下载单曲，同时保存单曲的统计信息
                track_success, track_stats, track_info, track_files = self.download_track(
                    track_id=track_id,
                    artist_id=artist_id,
                    save=save,
                    load=load
                )

                # 记录曲目下载状态
                stats["tracks"][track_id] = {
                    "name": track_name,
                    "status": track_stats.get("status", "failed"),
                    "error": track_stats.get("error"),
                    "path": track_stats.get("path"),
                    "retried": track_stats.get("retried", 0),
                    "non_retryable": track_stats.get("non_retryable", False)  # 保存不可重试状态
                }

                # 更新专辑统计信息
                stats["retried"] += track_stats.get("retried", 0)

                if track_success:
                    stats["success"] += 1
                    downloaded_files.extend(track_files)
                else:
                    stats["failed"] += 1
                    if track_stats.get("non_retryable", False):
                        stats["non_retryable"] += 1

            # 检查下载结果
            is_success = (stats["success"] + stats["non_retryable"]) == stats["total"]

            if is_success:
                stats["status"] = "success"
                stats["error"] = None
                logging.info(f"专辑 '{album_name}' 下载完成，共下载 {stats['success']}/{stats['total']} 首歌")
                if stats["failed"] > 0:
                    logging.warning(f"其中 {stats['failed']} 首歌曲下载失败")
                if stats["retried"] > 0:
                    logging.info(f"共进行了 {stats['retried']} 次重试")
                if stats["non_retryable"] > 0:
                    logging.info(f"其中 {stats['non_retryable']} 首歌曲因不可重试错误而跳过")
            else:
                stats["status"] = "failed"
                logging.error(f"专辑 '{album_name}' 下载失败，没有成功下载任何歌曲")

            # 保存统计信息
            if save:
                self._save_stats('album', album_id, stats)
                self._save_info('album', album_id, album_info)

            return is_success, stats, album_info, downloaded_files

        except Exception as e:
            logging.error(f"下载专辑时出错: {e}")
            import traceback
            traceback.print_exc()

            # 创建错误状态
            stats = {
                "album_id": album_id,
                "status": "failed",
                "error": str(e)
            }

            # 尝试保存错误状态
            if save:
                self._save_stats('album', album_id, stats)

            return False, stats, {}, []

    def download_artist(self, artist_id, include_singles=True, include_appears_on=False,
                    min_tracks=0, save=True, load=True):
        """
        下载艺术家的所有专辑

        参数:
            artist_id: Spotify 艺术家ID
            include_singles: 是否包含单曲
            include_appears_on: 是否包含艺术家参与的专辑
            min_tracks: 仅下载包含至少指定数量歌曲的专辑，0表示不限制
            save: 是否保存统计和元数据信息
            load: 是否尝试加载已有的统计和元数据信息

        返回:
            (bool, dict, dict, list): 
                - success: 下载是否成功
                - stats: 下载统计信息
                - info: 艺术家信息
                - downloaded_files: 下载的文件列表
        """
        # 尝试加载已有数据
        if load:
            stats = self._load_stats('artist', artist_id)
            info = self._load_info('artist', artist_id)

            if stats and info and stats.get('status') == 'success' and stats.get('albums'):
                # 收集已下载的文件路径
                downloaded_files = []
                for album_stats in stats.get('albums', {}).values():
                    for track_stats in album_stats.get('tracks', {}).values():
                        if track_stats.get('path'):
                            downloaded_files.append(track_stats.get('path'))

                logging.info(f"艺术家 {artist_id} 已存在，直接返回缓存数据")
                return True, stats, info, downloaded_files

        try:
            # 获取艺术家信息
            artist_info = self.sp.artist(artist_id)
            artist_name = artist_info['name']

            logging.info(f"艺术家: {artist_name}")

            # 加载或创建统计信息
            artist_stats = self._load_stats('artist', artist_id) if load else None
            if not artist_stats:
                artist_stats = self._create_new_artist_stats(artist_id, artist_name)
            else:
                # 更新艺术家名称，以防有变化
                artist_stats["artist_name"] = artist_name

            # 确保 albums 字段存在
            if "albums" not in artist_stats:
                artist_stats["albums"] = {}

            # 获取艺术家的专辑 - 简化逻辑，参照 download_artist_albums.py
            # 确定要获取的专辑类型
            album_types = ["album"]
            if include_singles:
                album_types.append("single")
            if include_appears_on:
                album_types.append("appears_on")

            album_type_param = ",".join(album_types)
            albums_data = []

            # 一次性获取所有类型的专辑
            results = self.sp.artist_albums(artist_id, include_groups=album_type_param, limit=50)
            while results:
                for item in results["items"]:
                    # 检查专辑艺术家列表中是否包含当前处理的艺术家ID
                    artist_ids = [artist["id"] for artist in item["artists"]]
                    if artist_id not in artist_ids:
                        # 如果不包含当前艺术家ID，则跳过这个专辑
                        continue

                    album_id = item["id"]
                    album_name = item["name"]
                    total_tracks = item["total_tracks"]

                    # 检查最小曲目数量
                    if min_tracks > 0 and total_tracks < min_tracks:
                        continue

                    albums_data.append({
                        "album_id": album_id,
                        "album_name": album_name,
                        "total_tracks": total_tracks,
                        "album_type": item["album_type"]  # album, single, compilation
                    })

                # 获取下一页结果
                if results["next"]:
                    results = self.sp.next(results)
                else:
                    results = None

            logging.info(f"共找到 {len(albums_data)} 张专辑/单曲")
            artist_stats["total_albums"] = len(albums_data)

            # 下载所有专辑
            all_downloaded_files = []
            artist_stats["total_tracks"] = 0
            artist_stats["downloaded_tracks"] = 0
            artist_stats["non_retryable_tracks"] = 0

            for album_data in albums_data:
                album_id = album_data["album_id"]
                album_name = album_data["album_name"]

                # 检查是否已经下载过
                if album_id in artist_stats["albums"] and artist_stats["albums"][album_id].get("status") == "success":
                    logging.info(f"专辑 '{album_name}' 已经下载过，跳过")

                    # 统计已下载专辑的曲目数量
                    album_stats = artist_stats["albums"][album_id]
                    artist_stats["total_tracks"] += album_stats.get("total", 0)
                    artist_stats["downloaded_tracks"] += album_stats.get("success", 0)
                    artist_stats["non_retryable_tracks"] += album_stats.get("non_retryable", 0)

                    # 收集文件路径
                    for track_stats in album_stats.get("tracks", {}).values():
                        if track_stats.get("path"):
                            all_downloaded_files.append(track_stats.get("path"))

                    continue

                # 下载专辑，传入 artist_id 参数以便在曲目下载时可能的过滤
                success, album_stats, album_info, downloaded_files = self.download_album(
                    album_id=album_id,
                    filter_artist_id=artist_id,
                    save=save,
                    load=load    # 使用相同的 load 参数
                )

                # 更新统计信息
                album_stats["album_type"] = album_data["album_type"]
                artist_stats["albums"][album_id] = album_stats

                # 更新艺术家总曲目和已下载曲目数
                artist_stats["total_tracks"] += album_stats.get("total", 0)
                artist_stats["downloaded_tracks"] += album_stats.get("success", 0)
                artist_stats["non_retryable_tracks"] += album_stats.get("non_retryable", 0)

                if success:
                    artist_stats["successful_albums"] = artist_stats.get("successful_albums", 0) + 1
                    logging.info(f"专辑 '{album_name}' 下载成功")
                    all_downloaded_files.extend(downloaded_files)
                else:
                    artist_stats["failed_albums"] = artist_stats.get("failed_albums", 0) + 1
                    logging.error(f"专辑 '{album_name}' 下载失败")

                # 保存最新的统计信息
                if save:
                    self._save_stats('artist', artist_id, artist_stats)

            # 判断是否全部成功
            artist_stats["successful_albums"] = artist_stats.get("successful_albums", 0)
            artist_stats["failed_albums"] = artist_stats.get("failed_albums", 0)
            is_success = artist_stats["successful_albums"] > 0

            if is_success:
                artist_stats["status"] = "success"
                artist_stats["error"] = None
            else:
                artist_stats["status"] = "failed"

            # 打印总结
            logging.info(f"艺术家 '{artist_name}' 所有专辑下载完成")
            logging.info(f"共找到 {artist_stats['total_albums']} 张专辑，成功下载 {artist_stats['successful_albums']} 张")
            logging.info(f"总计 {artist_stats['total_tracks']} 首歌曲，成功下载 {artist_stats['downloaded_tracks']} 首")
            if (artist_stats['non_retryable_tracks']):
                logging.info(f"\t其中 {artist_stats['non_retryable_tracks']} 首歌曲因不可重试错误而跳过")

            # 保存统计信息和元数据
            if save:
                self._save_stats('artist', artist_id, artist_stats)
                self._save_info('artist', artist_id, artist_info)

            return is_success, artist_stats, artist_info, all_downloaded_files

        except Exception as e:
            logging.error(f"下载艺术家专辑时出错: {e}")
            import traceback
            traceback.print_exc()

            # 创建错误状态
            stats = {
                "artist_id": artist_id,
                "status": "failed",
                "error": str(e)
            }

            # 尝试保存错误状态
            if save:
                self._save_stats('artist', artist_id, stats)

            return False, stats, {}, []

    def _create_new_artist_stats(self, artist_id, artist_name):
        """创建新的艺术家统计信息"""
        return {
            "artist_name": artist_name,
            "artist_id": artist_id,
            "total_albums": 0,
            "successful_albums": 0,
            "failed_albums": 0,
            "total_tracks": 0,
            "downloaded_tracks": 0,
            "non_retryable_tracks": 0,
            "status": "pending",
            "albums": {}
        }