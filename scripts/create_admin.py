import asyncio
import os
import sys

# 确保能导入app包
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from app.core.config import settings
from app.db.repositories.users import UserRepository
from app.services.user_service import UserService
from motor.motor_asyncio import AsyncIOMotorClient

async def create_admin():
    # 连接数据库
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.MONGODB_DB]

    # 创建仓库和服务
    user_repo = UserRepository(db)
    user_service = UserService(user_repo)

    # 检查管理员是否已存在
    admin_username = input("Enter admin username: ")
    existing_user = await user_repo.get_user_by_username(admin_username)

    if existing_user:
        if existing_user.get("role") == "admin":
            print(f"用户 {admin_username} 已经是管理员，无需更新")
        else:
            print(f"用户 {admin_username} 已存在，正在更新为管理员...")
            # 更新为管理员
            user_id = str(existing_user["_id"])
            await user_repo.update_user(user_id, {"role": "admin"})
            print(f"用户 {admin_username} 已更新为管理员")
    else:
        # 创建新管理员
        email = input("Enter admin email: ")
        password = input("Enter admin password: ")
        full_name = input("Enter admin full name: ")

        try:
            # 直接创建具有管理员角色的用户
            admin = await user_service.create_user(
                username=admin_username,
                email=email,
                password=password,
                full_name=full_name,
                role="admin"  # 设置为管理员
            )
            print(f"管理员 {admin['username']} 创建成功")
        except Exception as e:
            print(f"创建管理员失败: {e}")

    # 关闭连接
    client.close()

if __name__ == "__main__":
    asyncio.run(create_admin())