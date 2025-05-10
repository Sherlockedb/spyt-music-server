from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from datetime import datetime

class FileInfo(BaseModel):
    """文件信息模型"""
    available: bool
    size: Optional[str] = None
    size_bytes: Optional[int] = None
    format: Optional[str] = None
    content_type: Optional[str] = None
    rel_path: Optional[str] = None
    downloaded_at: Optional[str] = None
    error: Optional[str] = None

class TrackFileInfo(BaseModel):
    """曲目文件信息模型"""
    info: Dict[str, Any]
    file: Optional[FileInfo] = None

class LibraryFile(BaseModel):
    """音乐库文件模型"""
    name: str
    path: str
    size: str
    size_bytes: int
    format: str
    content_type: str
    modified_at: str