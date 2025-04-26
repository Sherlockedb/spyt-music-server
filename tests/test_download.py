import asyncio
import os
import sys
from motor.motor_asyncio import AsyncIOMotorClient

# 确保能导入app包
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.core.config import settings
from app.db.repositories.spotify_data import SpotifyDataRepository
from app.db.repositories.download_tasks import DownloadTaskRepository
from app.services.downloader_service import DownloaderService

async def test_download_track():
    """测试下载单曲并验证数据库存储"""
    print("开始测试下载功能...")
    print(f"- Spotify凭证: {'已配置' if settings.SPOTIFY_CLIENT_ID else '未配置'}")
    print(f"- MongoDB URL: {settings.MONGODB_URL}")
    print(f"- 数据库名称: {settings.MONGODB_DB}")
    print(f"- 音乐库路径: {settings.MUSIC_LIBRARY_PATH}")
    
    # 连接数据库
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.MONGODB_DB]
    
    # 创建仓库和服务
    spotify_repo = SpotifyDataRepository(db)
    task_repo = DownloadTaskRepository(db)
    service = DownloaderService(db, spotify_repo, task_repo)
    
    track_id = "6ENf77i5DmXDimXle5Ux3C"
    
    try:
        print(f"\n1. 创建下载任务...")
        task_id = await service.create_track_download_task(track_id)
        print(f"- 任务创建成功，ID: {task_id}")
        
        # 获取任务信息
        task = await task_repo.find_one({"task_id": task_id})
        print(f"- 任务详情: 名称={task['entity_name']}, 状态={task['status']}")
        
        print("\n2. 执行下载任务...")
        # 模拟工作者ID
        worker_id = "test-worker"
        
        # 分配任务给测试工作者
        await task_repo.assign_task(task_id, worker_id)
        
        # 执行任务
        success = await service.execute_task(task_id, worker_id)
        print(f"- 下载{'成功' if success else '失败'}")
        
        # 获取更新后的任务信息
        task = await task_repo.find_one({"task_id": task_id})
        print(f"- 任务最终状态: {task['status']}")
        
        print("\n3. 验证数据库存储...")
        # 检查是否存储了曲目信息
        track_info = await spotify_repo.get_track_info(track_id)
        print(f"- 曲目信息存储: {'成功' if track_info else '失败'}")
        
        # 检查是否存储了曲目统计信息
        track_stats = await spotify_repo.get_track_stats(track_id)
        print(f"- 曲目统计信息存储: {'成功' if track_stats else '失败'}")
        
        if track_stats and 'path' in track_stats:
            print(f"- 下载文件路径: {track_stats['path']}")
            print(f"- 文件是否存在: {'是' if os.path.exists(track_stats['path']) else '否'}")
        
        print("\n测试完成！")
    
    except Exception as e:
        print(f"测试过程中出错: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 关闭MongoDB连接
        client.close()

if __name__ == "__main__":
    asyncio.run(test_download_track())
