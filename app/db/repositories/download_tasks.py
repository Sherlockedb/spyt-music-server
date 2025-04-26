from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid

from app.db.base_repository import BaseRepository
from app.db.schemas import (
    DOWNLOAD_TASKS_COLLECTION,
    STATUS_PENDING, STATUS_IN_PROGRESS, STATUS_SUCCESS, STATUS_FAILED,
    TASK_TYPE_TRACK, TASK_TYPE_ALBUM, TASK_TYPE_ARTIST
)

class DownloadTaskRepository(BaseRepository):
    """
    下载任务仓库，处理任务队列
    """
    
    def __init__(self, db):
        """初始化仓库"""
        super().__init__(db, DOWNLOAD_TASKS_COLLECTION)
    
    async def create_task(self, task_type: str, entity_id: str, entity_name: str, 
                          priority: int = 5, options: dict = None) -> str:
        """
        创建新的下载任务
        
        参数:
            task_type: 任务类型 (track, album, artist)
            entity_id: 实体ID
            entity_name: 实体名称
            priority: 优先级 (1-10, 1为最高)
            options: 额外选项
            
        返回:
            任务ID
        """
        # 生成唯一任务ID
        task_id = str(uuid.uuid4())
        
        # 创建任务文档
        task = {
            "task_id": task_id,
            "task_type": task_type,
            "entity_id": entity_id,
            "entity_name": entity_name,
            "priority": priority,
            "status": STATUS_PENDING,
            "progress": {
                "total": 1,
                "completed": 0,
                "failed": 0
            },
            "options": options or {},
            "retries": 0,
            "max_retries": 3,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "scheduled_at": datetime.utcnow(),
            "started_at": None,
            "completed_at": None,
            "worker_id": None
        }
        
        # 插入任务
        await self.insert_one(task)
        return task_id
    
    async def get_next_pending_task(self, worker_id: str) -> Optional[Dict[str, Any]]:
        """
        获取下一个待处理的任务并标记为进行中
        
        参数:
            worker_id: 工作进程ID
            
        返回:
            任务文档，如果没有待处理任务则返回None
        """
        # 查询条件：状态为待处理，按优先级和创建时间排序
        query = {"status": STATUS_PENDING}
        sort = [("priority", 1), ("created_at", 1)]
        
        # 查找任务
        pending_tasks = await self.find(query, limit=1, sort=sort)
        if not pending_tasks:
            return None
        
        task = pending_tasks[0]
        task_id = task["task_id"]
        
        # 更新任务状态为进行中
        update = {
            "status": STATUS_IN_PROGRESS,
            "started_at": datetime.utcnow(),
            "worker_id": worker_id
        }
        
        updated_task = await self.update_one({"task_id": task_id}, {"$set": update})
        return updated_task
    
    async def update_task_progress(self, task_id: str, completed: int, failed: int, total: int) -> Optional[Dict[str, Any]]:
        """
        更新任务进度
        
        参数:
            task_id: 任务ID
            completed: 已完成的项目数
            failed: 失败的项目数
            total: 总项目数
            
        返回:
            更新后的任务文档
        """
        update = {
            "progress": {
                "completed": completed,
                "failed": failed,
                "total": total
            }
        }
        
        return await self.update_one({"task_id": task_id}, {"$set": update})
    
    async def complete_task(self, task_id: str, success: bool, error: str = None) -> Optional[Dict[str, Any]]:
        """
        完成任务
        
        参数:
            task_id: 任务ID
            success: 是否成功
            error: 错误信息（如果失败）
            
        返回:
            更新后的任务文档
        """
        update = {
            "status": STATUS_SUCCESS if success else STATUS_FAILED,
            "completed_at": datetime.utcnow()
        }
        
        if error:
            update["error"] = error
        
        return await self.update_one({"task_id": task_id}, {"$set": update})
    
    async def retry_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        重试失败的任务
        
        参数:
            task_id: 任务ID
            
        返回:
            更新后的任务文档，如果超过最大重试次数则返回None
        """
        # 查找任务
        task = await self.find_one({"task_id": task_id})
        if not task:
            return None
        
        # 检查重试次数
        retries = task.get("retries", 0)
        max_retries = task.get("max_retries", 3)
        
        if retries >= max_retries:
            return None
        
        # 更新任务状态为待处理
        update = {
            "status": STATUS_PENDING,
            "retries": retries + 1,
            "scheduled_at": datetime.utcnow(),
            "started_at": None,
            "worker_id": None
        }
        
        return await self.update_one({"task_id": task_id}, {"$set": update})
    
    async def get_tasks_by_status(self, status: str, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取特定状态的任务
        
        参数:
            status: 任务状态
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        返回:
            任务列表
        """
        return await self.find({"status": status}, skip=skip, limit=limit, sort=[("created_at", -1)])
    
    async def get_tasks_by_entity(self, entity_id: str, task_type: str = None) -> List[Dict[str, Any]]:
        """
        获取特定实体的任务
        
        参数:
            entity_id: 实体ID
            task_type: 任务类型（可选）
            
        返回:
            任务列表
        """
        query = {"entity_id": entity_id}
        if task_type:
            query["task_type"] = task_type
        
        return await self.find(query, sort=[("created_at", -1)])
    
    async def get_tasks_by_worker(self, worker_id: str, status: str = None) -> List[Dict[str, Any]]:
        """
        获取特定工作进程的任务
        
        参数:
            worker_id: 工作进程ID
            status: 任务状态（可选）
            
        返回:
            任务列表
        """
        query = {"worker_id": worker_id}
        if status:
            query["status"] = status
        
        return await self.find(query, sort=[("created_at", -1)])
    
    async def assign_task(self, task_id: str, worker_id: str) -> bool:
        """
        将任务分配给指定的工作者
        
        参数:
            task_id: 任务ID
            worker_id: 工作者ID
            
        返回:
            bool: 是否成功分配
        """
        from app.db.schemas import STATUS_IN_PROGRESS
        
        # 更新任务状态为进行中，并分配给工作者
        result = await self.update_one(
            {"task_id": task_id, "status": "pending"},  # 只更新状态为pending的任务
            {
                "$set": {
                    "status": STATUS_IN_PROGRESS,
                    "worker_id": worker_id,
                    "started_at": datetime.utcnow()
                }
            }
        )
        
        # 如果没有找到匹配的文档或更新失败
        if not result or result.get('matched_count', 0) == 0:
            return False
            
        return True