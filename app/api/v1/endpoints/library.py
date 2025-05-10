from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.responses import StreamingResponse
from typing import List, Dict, Any, Optional
import os

from app.services.file_service import FileService
from app.models.file import TrackFileInfo, LibraryFile
from app.core.deps import get_file_service
from app.core.auth import get_current_user

router = APIRouter()

@router.get("/tracks/{track_id}", response_model=TrackFileInfo)
async def get_track_file_info(
    track_id: str,
    file_service: FileService = Depends(get_file_service),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    获取曲目文件信息
    """
    return await file_service.get_track_info_with_file(track_id)

@router.get("/files", response_model=List[LibraryFile])
async def list_library_files(
    skip: int = 0,
    limit: int = 100,
    file_service: FileService = Depends(get_file_service),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    列出音乐库中的文件
    """
    return await file_service.list_library_files(skip=skip, limit=limit)