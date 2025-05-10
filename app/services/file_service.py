import os
import logging
import shutil
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, BinaryIO, Tuple
from fastapi import HTTPException, status

from app.core.config import settings
from app.db.repositories.spotify_data import SpotifyDataRepository

def format_file_size(size_in_bytes):
    """将文件大小格式化为人类可读的形式"""
    # 定义单位
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    size = float(size_in_bytes)
    unit_index = 0

    # 逐级转换单位，直到小于1024或达到最大单位
    while size >= 1024.0 and unit_index < len(units) - 1:
        size /= 1024.0
        unit_index += 1

    # 根据大小决定小数位数：小于10用2位小数，大于100不用小数
    if size < 10:
        return f"{size:.2f} {units[unit_index]}"
    elif size < 100:
        return f"{size:.1f} {units[unit_index]}"
    else:
        return f"{int(size)} {units[unit_index]}"

class FileService:
    """
    文件管理服务，处理音频文件的存储和访问
    """

    def __init__(self, spotify_repo: SpotifyDataRepository):
        """
        初始化文件服务

        参数:
            spotify_repo: Spotify数据仓库，用于获取文件元数据
        """
        self.spotify_repo = spotify_repo
        self.music_library_path = Path(settings.MUSIC_LIBRARY_PATH)
        self.temp_download_path = Path(settings.TEMP_DOWNLOAD_PATH)

        # 确保目录存在
        self.music_library_path.mkdir(parents=True, exist_ok=True)
        self.temp_download_path.mkdir(parents=True, exist_ok=True)

        # 添加常见音频格式的MIME类型
        mimetypes.add_type('audio/aac', '.aac')
        mimetypes.add_type('audio/flac', '.flac')
        mimetypes.add_type('audio/mpeg', '.mp3')
        mimetypes.add_type('audio/ogg', '.ogg')
        mimetypes.add_type('audio/wav', '.wav')

    async def get_file_path(self, track_id: str) -> Optional[str]:
        """
        获取曲目文件的完整路径

        参数:
            track_id: Spotify曲目ID

        返回:
            str|None: 文件路径，如果找不到则返回None
        """
        # 从数据库获取曲目统计信息
        track_stats = await self.spotify_repo.get_track_stats(track_id)

        if not track_stats or 'path' not in track_stats:
            return None

        file_path = track_stats['path']

        # 检查文件是否存在
        if not os.path.isfile(file_path):
            logging.warning(f"曲目文件不存在: {file_path}")
            return None

        return file_path

    async def get_file_stream(self, track_id: str) -> Tuple[Optional[BinaryIO], Optional[str], Optional[int]]:
        """
        获取曲目文件流

        参数:
            track_id: Spotify曲目ID

        返回:
            Tuple[BinaryIO|None, str|None, int|None]:
                - 文件流对象
                - MIME类型
                - 文件大小
        """
        file_path = await self.get_file_path(track_id)

        if not file_path:
            return None, None, None

        try:
            # 获取文件MIME类型
            content_type, _ = mimetypes.guess_type(file_path)
            if not content_type:
                content_type = 'application/octet-stream'

            # 获取文件大小
            file_size = os.path.getsize(file_path)

            # 打开文件流
            file_stream = open(file_path, 'rb')

            return file_stream, content_type, file_size

        except Exception as e:
            logging.error(f"打开文件流失败: {e}")
            return None, None, None

    async def get_track_info_with_file(self, track_id: str) -> Dict[str, Any]:
        """
        获取曲目信息，包括文件信息

        参数:
            track_id: Spotify曲目ID

        返回:
            Dict: 曲目信息
        """
        # 获取曲目信息
        track_info = await self.spotify_repo.get_track_info(track_id)

        if not track_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="曲目未找到"
            )

        # 获取曲目统计信息
        track_stats = await self.spotify_repo.get_track_stats(track_id)

        # 创建结果对象
        result = {
            "info": track_info.get('info', {}),
            "file": None
        }

        # 添加文件信息
        if track_stats and 'path' in track_stats:
            file_path = track_stats['path']

            if os.path.isfile(file_path):
                # 获取文件信息
                file_size = os.path.getsize(file_path)
                content_type, _ = mimetypes.guess_type(file_path)
                if not content_type:
                    content_type = 'application/octet-stream'

                # 获取相对路径（用于URL生成）
                relative_path = os.path.relpath(file_path, self.music_library_path)

                result["file"] = {
                    "available": True,
                    "size_bytes": file_size,
                    "size": format_file_size(file_size),
                    "format": os.path.splitext(file_path)[1].lstrip('.'),
                    "content_type": content_type,
                    "rel_path": relative_path.replace('\\', '/'),  # 确保路径分隔符一致
                    "downloaded_at": datetime.fromtimestamp(os.path.getmtime(file_path)).strftime("%Y-%m-%d %H:%M:%S")
                }
            else:
                result["file"] = {
                    "available": False,
                    "error": "文件不存在"
                }

        return result

    async def list_library_files(self, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """
        列出音乐库中的文件

        参数:
            skip: 跳过的文件数
            limit: 返回的最大文件数

        返回:
            List[Dict]: 文件列表
        """
        files = []
        allowed_extensions = {'.mp3', '.flac', '.aac', '.ogg', '.wav'}

        try:
            # 递归遍历音乐库目录
            for root, _, filenames in os.walk(self.music_library_path):
                for filename in filenames:
                    if os.path.splitext(filename)[1].lower() in allowed_extensions:
                        file_path = os.path.join(root, filename)
                        rel_path = os.path.relpath(file_path, self.music_library_path)

                        # 获取文件信息
                        file_size = os.path.getsize(file_path)
                        content_type, _ = mimetypes.guess_type(file_path)
                        if not content_type:
                            content_type = 'application/octet-stream'

                        files.append({
                            "name": filename,
                            "path": rel_path.replace('\\', '/'),
                            "size_bytes": file_size,
                            "size": format_file_size(file_size),
                            "format": os.path.splitext(filename)[1].lstrip('.'),
                            "content_type": content_type,
                            "modified_at": datetime.fromtimestamp(os.path.getmtime(file_path)).strftime("%Y-%m-%d %H:%M:%S")
                        })

            # 应用分页
            return files[skip:skip+limit]

        except Exception as e:
            logging.error(f"列出音乐库文件失败: {e}")
            return []

    async def copy_file_to_library(self, source_path: str, destination_dir: str, filename: str) -> Optional[str]:
        """
        将文件复制到音乐库

        参数:
            source_path: 源文件路径
            destination_dir: 目标目录（相对于音乐库根目录）
            filename: 文件名

        返回:
            str|None: 新文件的完整路径，如果失败则返回None
        """
        if not os.path.isfile(source_path):
            logging.error(f"源文件不存在: {source_path}")
            return None

        try:
            # 创建目标目录
            dest_dir_path = self.music_library_path / destination_dir
            dest_dir_path.mkdir(parents=True, exist_ok=True)

            # 构建目标文件路径
            dest_file_path = dest_dir_path / filename

            # 复制文件
            shutil.copy2(source_path, dest_file_path)

            logging.info(f"文件已复制到音乐库: {dest_file_path}")
            return str(dest_file_path)

        except Exception as e:
            logging.error(f"复制文件到音乐库失败: {e}")
            return None