import logging
from datetime import datetime, timedelta
from typing import List, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.triggers.cron import CronTrigger

from app.db.repositories.download_tasks import DownloadTaskRepository
from app.db.repositories.spotify_data import SpotifyDataRepository
from app.core.config import settings
from app.db.schemas import STATUS_FAILED, STATUS_SUCCESS, STATUS_IN_PROGRESS

class TaskScheduler:
    """
    任务调度器，负责管理定时任务
    """

    def __init__(self, task_repo: DownloadTaskRepository, spotify_repo: SpotifyDataRepository):
        """
        初始化调度器

        参数:
            task_repo: 下载任务仓库
            spotify_repo: Spotify数据仓库
        """
        self.task_repo = task_repo
        self.spotify_repo = spotify_repo
        self.scheduler = None

    async def start(self):
        """启动调度器"""
        if self.scheduler and self.scheduler.running:
            logging.warning("调度器已经在运行")
            return

        # 配置调度器
        jobstores = {
            'default': MemoryJobStore()
        }

        executors = {
            'default': ThreadPoolExecutor(max_workers=5)
        }

        job_defaults = {
            'coalesce': True,
            'max_instances': 1,
            'misfire_grace_time': 60  # 错过的任务可以延迟多少秒执行
        }

        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults
        )

        # 添加定时任务

        # 每小时清理僵尸任务
        self.scheduler.add_job(
            self.clean_zombie_tasks,
            CronTrigger(minute=0),  # 每小时整点执行
            id='clean_zombie_tasks',
            name='清理僵尸任务',
            replace_existing=True
        )

        # 每天清理过期任务
        self.scheduler.add_job(
            self.clean_expired_tasks,
            CronTrigger(hour=3, minute=0),  # 每天凌晨3点执行
            id='clean_expired_tasks',
            name='清理过期任务',
            replace_existing=True
        )

        # 每6小时更新一次统计信息
        self.scheduler.add_job(
            self.update_statistics,
            CronTrigger(hour='*/6'),  # 每6小时执行一次
            id='update_statistics',
            name='更新统计信息',
            replace_existing=True
        )

        # 启动调度器
        self.scheduler.start()
        logging.info("定时任务调度器已启动")

    async def stop(self):
        """停止调度器"""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown()
            logging.info("定时任务调度器已停止")

    async def clean_zombie_tasks(self):
        """
        清理僵尸任务（状态为进行中但已超时的任务）
        """
        logging.info("开始清理僵尸任务...")

        try:
            # 获取所有处于进行中状态的任务
            in_progress_tasks = await self.task_repo.find({"status": STATUS_IN_PROGRESS})

            # 计算超时时间（默认1小时）
            timeout_threshold = datetime.utcnow() - timedelta(hours=1)

            cleaned_count = 0

            for task in in_progress_tasks:
                # 检查任务是否超时
                started_at = task.get("started_at")

                if started_at and started_at < timeout_threshold:
                    # 将僵尸任务标记为失败
                    await self.task_repo.update_one(
                        {"task_id": task["task_id"]},
                        {"$set": {
                            "status": STATUS_FAILED,
                            "error": "任务执行超时",
                            "completed_at": datetime.utcnow()
                        }}
                    )

                    cleaned_count += 1
                    logging.info(f"已将僵尸任务标记为失败: {task['task_id']}")

            logging.info(f"僵尸任务清理完成，共处理 {cleaned_count} 个任务")

        except Exception as e:
            logging.error(f"清理僵尸任务时出错: {e}")

    async def clean_expired_tasks(self):
        """
        清理过期的已完成任务（默认保留30天）
        """
        logging.info("开始清理过期任务...")

        try:
            # 计算过期时间（默认30天）
            expiry_threshold = datetime.utcnow() - timedelta(days=settings.TASK_RETENTION_DAYS)

            # 找出所有已完成/失败且完成时间超过保留期的任务
            query = {
                "status": {"$in": [STATUS_SUCCESS, STATUS_FAILED]},
                "completed_at": {"$lt": expiry_threshold}
            }

            # 统计要删除的任务数量
            count = await self.task_repo.count(query)

            if count > 0:
                # 删除过期任务
                await self.task_repo.delete_many(query)
                logging.info(f"已删除 {count} 个过期任务")
            else:
                logging.info("没有发现过期任务")

        except Exception as e:
            logging.error(f"清理过期任务时出错: {e}")

    async def update_statistics(self):
        """
        更新系统统计信息
        """
        logging.info("开始更新系统统计信息...")

        try:
            # 统计各种状态的任务数量
            stats = {}

            # 任务状态统计
            for status in [STATUS_SUCCESS, STATUS_FAILED, STATUS_IN_PROGRESS, "pending"]:
                count = await self.task_repo.count({"status": status})
                stats[f"tasks_{status}"] = count

            # 总任务数
            stats["tasks_total"] = sum(stats.values())

            # 下载成功率
            completed_tasks = stats.get("tasks_success", 0) + stats.get("tasks_failed", 0)
            stats["success_rate"] = (stats.get("tasks_success", 0) / completed_tasks) * 100 if completed_tasks > 0 else 0

            # 媒体库统计
            track_count = await self.spotify_repo.count_tracks_with_files()
            album_count = await self.spotify_repo.count_albums_with_files()
            artist_count = await self.spotify_repo.count_artists_with_files()

            stats["library_tracks"] = track_count
            stats["library_albums"] = album_count
            stats["library_artists"] = artist_count

            # 更新时间
            stats["updated_at"] = datetime.utcnow()

            # 保存统计信息到数据库
            await self._save_statistics(stats)

            logging.info("系统统计信息更新完成")

        except Exception as e:
            logging.error(f"更新统计信息时出错: {e}")

    async def _save_statistics(self, stats):
        """
        将统计信息保存到数据库

        参数:
            stats: 统计信息字典
        """
        try:
            # 假设我们有一个专门的集合来存储系统统计信息
            # 使用 _id = "system_stats" 来标识这个唯一的文档
            await self.task_repo.db["system_stats"].replace_one(
                {"_id": "system_stats"},
                stats,
                upsert=True
            )
        except Exception as e:
            logging.error(f"保存统计信息到数据库时出错: {e}")