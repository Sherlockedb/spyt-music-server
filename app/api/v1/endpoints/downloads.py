from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from app.models.download import DownloadTaskCreate, DownloadTaskResponse, PaginatedDownloadTaskResponse
from app.services.downloader_service import DownloaderService
from app.core.auth import get_current_user
from app.core.deps import get_downloader_service

router = APIRouter()

@router.post("/", response_model=DownloadTaskResponse)
async def create_download_task(
    task: DownloadTaskCreate,
    downloader_service: DownloaderService = Depends(get_downloader_service),
    current_user: dict = Depends(get_current_user)
) -> Any:
    """创建下载任务"""
    try:
        if task.entity_type == "track":
            task_id = await downloader_service.create_track_download_task(
                track_id=task.entity_id,
                priority=task.priority
            )
        elif task.entity_type == "album":
            task_id = await downloader_service.create_album_download_task(
                album_id=task.entity_id,
                filter_artist_id=task.options.get("filter_artist_id"),
                priority=task.priority
            )
        elif task.entity_type == "artist":
            task_id = await downloader_service.create_artist_download_task(
                artist_id=task.entity_id,
                include_singles=task.options.get("include_singles", True),
                include_appears_on=task.options.get("include_appears_on", False),
                min_tracks=task.options.get("min_tracks", 0),
                priority=task.priority
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的实体类型: {task.entity_type}"
            )

        # 获取创建的任务详情
        task_info = await downloader_service.task_repo.find_one({"task_id": task_id})
        return task_info

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建下载任务失败: {str(e)}"
        )

@router.get("/", response_model=PaginatedDownloadTaskResponse)
async def list_download_tasks(
    status: Optional[str] = None,
    entity_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    downloader_service: DownloaderService = Depends(get_downloader_service),
    current_user: dict = Depends(get_current_user)
) -> Any:
    """获取下载任务列表"""
    tasks = []

    query = {}

    if status:
        query["status"] = status

    if entity_id:
        query["entity_id"] = entity_id

    # 使用优化的方法一次性获取列表和总数
    result = await downloader_service.task_repo.get_paginated_tasks(
        query=query,
        skip=skip,
        limit=limit,
        sort_field="created_at",
        sort_direction=-1
    )

    return result

@router.get("/statistics", response_model=Dict[str, int])
async def get_download_statistics(
    downloader_service: DownloaderService = Depends(get_downloader_service),
    current_user: dict = Depends(get_current_user)
) -> Any:
    """获取下载任务统计信息"""
    return await downloader_service.get_task_statistics()

@router.get("/{task_id}", response_model=DownloadTaskResponse)
async def get_download_task(
    task_id: str,
    downloader_service: DownloaderService = Depends(get_downloader_service),
    current_user: dict = Depends(get_current_user)
) -> Any:
    """获取下载任务详情"""
    task = await downloader_service.task_repo.find_one({"task_id": task_id})
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在"
        )
    return task

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_download_task(
    task_id: str,
    downloader_service: DownloaderService = Depends(get_downloader_service),
    current_user: dict = Depends(get_current_user)
) -> None:
    """取消下载任务"""
    # 实现取消任务的逻辑
    task = await downloader_service.task_repo.find_one({"task_id": task_id})
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在"
        )

    # 只能取消pending状态的任务
    if task["status"] != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无法取消状态为 {task['status']} 的任务"
        )

    # 将任务标记为取消状态
    await downloader_service.task_repo.update_one(
        {"task_id": task_id},
        {"$set": {"status": "canceled"}}
    )

@router.post("/{task_id}/retry", response_model=DownloadTaskResponse)
async def retry_download_task(
    task_id: str,
    downloader_service: DownloaderService = Depends(get_downloader_service),
    current_user: dict = Depends(get_current_user)
) -> Any:
    """重试失败的下载任务"""
    success = await downloader_service.retry_failed_task(task_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无法重试任务，可能任务不存在或不是失败状态"
        )

    # 返回更新后的任务信息
    task = await downloader_service.task_repo.find_one({"task_id": task_id})
    return task