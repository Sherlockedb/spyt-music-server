from pydantic import BaseModel

class TokenData(BaseModel):
    """令牌数据模型"""
    user_id: str