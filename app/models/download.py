from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class DownloadTaskCreate(BaseModel):
    """创建下载任务请求模型"""
    entity_id: str
    entity_type: str  # track, album, artist
    priority: int = 5
    options: Dict[str, Any] = {}

class DownloadTaskResponse(BaseModel):
    """下载任务响应模型"""
    task_id: str
    entity_id: str
    entity_name: str
    entity_type: str = Field(alias="task_type")
    status: str
    progress: Dict[str, int]
    created_at: datetime
    updated_at: Optional[datetime] = None
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    worker_id: Optional[str] = None
    options: Dict[str, Any] = {}

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "arbitrary_types_allowed": True  # 允许非标准类型如ObjectId
    }