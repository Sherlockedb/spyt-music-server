from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import get_current_user
from app.db.repositories.download_tasks import DownloadTaskRepository
from app.core.deps import get_download_task_repository

router = APIRouter()

@router.get("/stats")
async def get_system_stats(
    task_repo: DownloadTaskRepository = Depends(get_download_task_repository),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    获取系统统计信息
    """
    try:
        # 从system_stats集合中获取统计信息
        stats = await task_repo.db["system_stats"].find_one({"_id": "system_stats"})

        if not stats:
            return {
                "tasks_total": 0,
                "tasks_success": 0,
                "tasks_failed": 0,
                "tasks_pending": 0,
                "tasks_in_progress": 0,
                "success_rate": 0,
                "library_tracks": 0,
                "library_albums": 0,
                "library_artists": 0,
                "updated_at": None
            }

        # 删除_id字段
        if "_id" in stats:
            del stats["_id"]

        return stats

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取系统统计信息失败: {str(e)}"
        )

@router.get("/health")
async def healthcheck():
    """
    系统健康检查
    """
    return {"status": "ok", "version": "1.0.0"}

@router.get("/workers")
async def get_active_workers(
    task_repo: DownloadTaskRepository = Depends(get_download_task_repository),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    获取活跃的工作者列表
    """
    try:
        # 找到所有处于进行中状态的任务，并提取其worker_id
        in_progress_tasks = await task_repo.find({"status": "in_progress"})

        workers = {}
        for task in in_progress_tasks:
            worker_id = task.get("worker_id")
            if worker_id:
                if worker_id not in workers:
                    workers[worker_id] = {
                        "worker_id": worker_id,
                        "active_tasks": 0,
                        "last_active": None
                    }

                workers[worker_id]["active_tasks"] += 1

                # 更新最后活跃时间
                started_at = task.get("started_at")
                if started_at and (not workers[worker_id]["last_active"] or
                                  started_at > workers[worker_id]["last_active"]):
                    workers[worker_id]["last_active"] = started_at

        return list(workers.values())

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取活跃工作者失败: {str(e)}"
        )