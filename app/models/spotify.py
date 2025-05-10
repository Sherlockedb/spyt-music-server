from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class SpotifyImage(BaseModel):
    """Spotify图片模型"""
    url: str
    height: Optional[int] = None
    width: Optional[int] = None

class SpotifyArtistSimple(BaseModel):
    """简化版Spotify艺术家模型"""
    id: str
    name: str

class SpotifyAlbumSimple(BaseModel):
    """简化版Spotify专辑模型"""
    id: str
    name: str
    images: List[SpotifyImage] = []

class SpotifyTrackItem(BaseModel):
    """Spotify搜索结果中的曲目项"""
    id: str
    name: str
    artists: List[SpotifyArtistSimple]
    album: SpotifyAlbumSimple
    duration_ms: int
    popularity: int

class SpotifyAlbumItem(BaseModel):
    """Spotify搜索结果中的专辑项"""
    id: str
    name: str
    artists: List[SpotifyArtistSimple]
    release_date: str
    total_tracks: int
    images: List[SpotifyImage] = []

class SpotifyArtistItem(BaseModel):
    """Spotify搜索结果中的艺术家项"""
    id: str
    name: str
    genres: List[str] = []
    popularity: int
    images: List[SpotifyImage] = []

class SpotifySearchResults(BaseModel):
    """Spotify搜索结果模型"""
    tracks: Optional[List[SpotifyTrackItem]] = None
    albums: Optional[List[SpotifyAlbumItem]] = None
    artists: Optional[List[SpotifyArtistItem]] = None

class SpotifyTrackDetail(BaseModel):
    """Spotify曲目详情"""
    info: Dict[str, Any]

class SpotifyAlbumDetail(BaseModel):
    """Spotify专辑详情"""
    info: Dict[str, Any]

class SpotifyArtistDetail(BaseModel):
    """Spotify艺术家详情"""
    info: Dict[str, Any]