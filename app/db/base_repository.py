from typing import Any, Dict, List, Optional, TypeVar, Generic, Type
from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from pymongo import ReturnDocument

T = TypeVar('T')

class BaseRepository:
    """
    基础数据仓库，提供通用的操作
    """
    
    def __init__(self, db: AsyncIOMotorDatabase, collection_name: str):
        """
        初始化仓库
        
        参数:
            db: 数据库实例
            collection_name: 集合名称
        """
        self.db = db
        self.collection_name = collection_name
        self.collection = db[collection_name]
    
    async def find_one(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        查找单个文档
        
        参数:
            query: 查询条件
            
        返回:
            找到的文档，或者 None
        """
        return await self.collection.find_one(query)
    
    async def find(self, query: Dict[str, Any], skip: int = 0, limit: int = 100, 
                  sort: List[tuple] = None) -> List[Dict[str, Any]]:
        """
        查找多个文档
        
        参数:
            query: 查询条件
            skip: 跳过的文档数量
            limit: 返回的最大文档数量
            sort: 排序条件，例如 [("created_at", -1)]
            
        返回:
            文档列表
        """
        cursor = self.collection.find(query).skip(skip).limit(limit)
        if sort:
            cursor = cursor.sort(sort)
        
        return await cursor.to_list(length=limit)
    
    async def count(self, query: Dict[str, Any]) -> int:
        """
        计算符合条件的文档数量
        
        参数:
            query: 查询条件
            
        返回:
            文档数量
        """
        return await self.collection.count_documents(query)
    
    async def insert_one(self, document: Dict[str, Any]) -> str:
        """
        插入单个文档
        
        参数:
            document: 要插入的文档
            
        返回:
            插入的文档 ID
        """
        # 添加创建和更新时间
        if "created_at" not in document:
            document["created_at"] = datetime.utcnow()
        document["updated_at"] = datetime.utcnow()
        
        result = await self.collection.insert_one(document)
        return str(result.inserted_id)
    
    async def update_one(self, query: Dict[str, Any], update: Dict[str, Any], 
                        upsert: bool = False) -> Optional[Dict[str, Any]]:
        """
        更新单个文档
        
        参数:
            query: 查询条件
            update: 更新操作
            upsert: 如果文档不存在，是否插入
            
        返回:
            更新后的文档，或者 None
        """
        # 确保更新操作包含 $set 操作符
        if not any(key.startswith('$') for key in update.keys()):
            update = {"$set": update}
        
        # 添加更新时间
        if "$set" in update:
            update["$set"]["updated_at"] = datetime.utcnow()
        else:
            update["$set"] = {"updated_at": datetime.utcnow()}
        
        return await self.collection.find_one_and_update(
            query,
            update,
            upsert=upsert,
            return_document=ReturnDocument.AFTER
        )
    
    async def delete_one(self, query: Dict[str, Any]) -> bool:
        """
        删除单个文档
        
        参数:
            query: 查询条件
            
        返回:
            是否成功删除
        """
        result = await self.collection.delete_one(query)
        return result.deleted_count > 0
    
    async def delete_many(self, query: Dict[str, Any]) -> int:
        """
        删除多个文档
        
        参数:
            query: 查询条件
            
        返回:
            删除的文档数量
        """
        result = await self.collection.delete_many(query)
        return result.deleted_count