from datetime import datetime
from typing import Optional, Dict, Any, Annotated
from pydantic import BaseModel, EmailStr, Field, model_validator, BeforeValidator
from bson import ObjectId
import typing

# 创建ObjectId转换器函数
def convert_object_id(id: Any) -> str:
    if isinstance(id, ObjectId):
        return str(id)
    if isinstance(id, dict) and "_id" in id and isinstance(id["_id"], ObjectId):
        id["_id"] = str(id["_id"])
    return id

# 使用Annotated和BeforeValidator创建字符串ID类型
StringObjectId = Annotated[str, BeforeValidator(lambda x: str(x) if isinstance(x, ObjectId) else x)]

class UserBase(BaseModel):
    """用户基础信息模型"""
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    disabled: bool = False
    role: str = "user"

class UserCreate(UserBase):
    """创建用户时使用的模型"""
    password: str

class UserUpdate(BaseModel):
    """更新用户信息时使用的模型"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    disabled: Optional[bool] = None
    role: Optional[str] = None

class UserInDB(UserBase):
    """数据库中的用户模型"""
    id: str
    hashed_password: str
    preferences: Dict[str, Any] = Field(default_factory=lambda: {
        "theme": "light",
        "quality": "high"
    })
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True

class UserResponse(UserBase):
    """API响应中的用户模型"""
    # 使用StringObjectId类型确保ObjectId被转换为字符串
    id: StringObjectId = Field(alias="_id")
    preferences: Dict[str, Any]
    created_at: datetime
    updated_at: Optional[datetime] = None

    # 在模型验证前处理输入数据
    @model_validator(mode='before')
    @classmethod
    def validate_to_json(cls, data: Any) -> Any:
        """处理从MongoDB直接获取的数据"""
        if isinstance(data, dict):
            # 转换ObjectId为字符串
            if "_id" in data and isinstance(data["_id"], ObjectId):
                data["_id"] = str(data["_id"])
        return data

    model_config = {
        "populate_by_name": True,
        "from_attributes": True,
        "arbitrary_types_allowed": True  # 允许非标准类型如ObjectId
    }