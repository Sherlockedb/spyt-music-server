from typing import Dict, Optional, Any
from datetime import datetime

from app.db.base_repository import BaseRepository
from app.db.schemas import SETTINGS_COLLECTION

class SettingsRepository(BaseRepository):
    """
    系统设置仓库
    """
    
    def __init__(self, db):
        """初始化仓库"""
        super().__init__(db, SETTINGS_COLLECTION)
        self.settings_id = "system_settings"
    
    async def get_system_settings(self) -> Dict[str, Any]:
        """
        获取系统设置，如果不存在则创建默认设置
        
        返回:
            系统设置
        """
        settings = await self.find_one({"_id": self.settings_id})
        
        if not settings:
            # 创建默认设置
            settings = {
                "_id": self.settings_id,
                "version": "1.0.0",
                "maintenance_mode": False,
                "download_limits": {
                    "concurrent_tasks": 5,
                    "max_retries": 3,
                    "retry_delay": 5
                },
                "spotify_api": {
                    "rate_limit": 100,
                    "reset_interval": 3600
                },
                "updated_at": datetime.utcnow(),
                "updated_by": "system"
            }
            
            await self.insert_one(settings)
        
        return settings
    
    async def update_system_settings(self, settings: Dict[str, Any], updated_by: str = "system") -> Optional[Dict[str, Any]]:
        """
        更新系统设置
        
        参数:
            settings: 新的设置值
            updated_by: 更新者
            
        返回:
            更新后的设置
        """
        # 添加更新信息
        settings["updated_at"] = datetime.utcnow()
        settings["updated_by"] = updated_by
        
        return await self.update_one(
            {"_id": self.settings_id},
            {"$set": settings},
            upsert=True
        )
    
    async def get_setting(self, key: str, default: Any = None) -> Any:
        """
        获取特定设置项
        
        参数:
            key: 设置键名
            default: 默认值
            
        返回:
            设置值
        """
        settings = await self.get_system_settings()
        
        # 支持使用点表示法访问嵌套设置
        if "." in key:
            parts = key.split(".")
            value = settings
            for part in parts:
                if part in value:
                    value = value[part]
                else:
                    return default
            return value
        
        return settings.get(key, default)
    
    async def set_setting(self, key: str, value: Any, updated_by: str = "system") -> bool:
        """
        设置特定设置项
        
        参数:
            key: 设置键名
            value: 设置值
            updated_by: 更新者
            
        返回:
            是否成功
        """
        # 支持使用点表示法设置嵌套设置
        if "." in key:
            update = {}
            update[key] = value
            update["updated_at"] = datetime.utcnow()
            update["updated_by"] = updated_by
            
            result = await self.update_one(
                {"_id": self.settings_id},
                {"$set": update},
                upsert=True
            )
            return result is not None
        
        # 获取当前设置
        settings = await self.get_system_settings()
        settings[key] = value
        settings["updated_at"] = datetime.utcnow()
        settings["updated_by"] = updated_by
        
        result = await self.update_one(
            {"_id": self.settings_id},
            {"$set": settings},
            upsert=True
        )
        return result is not None