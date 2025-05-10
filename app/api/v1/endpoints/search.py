from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Optional, List, Dict, Any

from app.services.spotify_service import SpotifyService
from app.models.spotify import SpotifySearchResults, SpotifyTrackDetail, SpotifyAlbumDetail, SpotifyArtistDetail
from app.core.auth import get_current_user
from app.core.deps import get_spotify_service

router = APIRouter()

@router.get("/", response_model=SpotifySearchResults)
async def search_spotify(
    q: str = Query(..., description="搜索关键词"),
    type: str = Query("track,album,artist", description="搜索类型"),
    limit: int = Query(20, ge=1, le=50, description="每种类型的结果数量限制"),
    spotify_service: SpotifyService = Depends(get_spotify_service),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    搜索Spotify音乐、专辑和艺术家
    """
    try:
        results = await spotify_service.search(query=q, search_type=type, limit=limit)
        return results
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"搜索Spotify时出错: {str(e)}"
        )

@router.get("/tracks/{track_id}", response_model=SpotifyTrackDetail)
async def get_track_detail(
    track_id: str,
    spotify_service: SpotifyService = Depends(get_spotify_service),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    获取Spotify曲目详情
    """
    track_info = await spotify_service.get_track_info(track_id)
    if not track_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="曲目未找到"
        )
    return track_info

@router.get("/albums/{album_id}", response_model=SpotifyAlbumDetail)
async def get_album_detail(
    album_id: str,
    spotify_service: SpotifyService = Depends(get_spotify_service),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    获取Spotify专辑详情
    """
    album_info = await spotify_service.get_album_info(album_id)
    if not album_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="专辑未找到"
        )
    return album_info

@router.get("/artists/{artist_id}", response_model=SpotifyArtistDetail)
async def get_artist_detail(
    artist_id: str,
    spotify_service: SpotifyService = Depends(get_spotify_service),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    获取Spotify艺术家详情
    """
    artist_info = await spotify_service.get_artist_info(artist_id)
    if not artist_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="艺术家未找到"
        )
    return artist_info