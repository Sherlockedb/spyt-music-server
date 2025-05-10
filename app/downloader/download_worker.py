import time
import logging
import pymongo
from pymongo import MongoClient
from datetime import datetime, timezone

from app.downloader.mongo_downloader import MongoDBSpotifyDownloader
from app.db.schemas import STATUS_PENDING, STATUS_IN_PROGRESS, STATUS_SUCCESS, STATUS_FAILED, DOWNLOAD_TASKS_COLLECTION
from app.core.config import settings
from app.core.retry import retry

class DownloadWorker:
    """下载任务执行器 - 完全同步实现"""

    def __init__(self, worker_id, poll_interval=None):
        """
        初始化下载工作者

        参数:
            worker_id: 工作者ID，如果未提供则自动生成
            poll_interval: 轮询间隔时间（秒）
        """
        self.worker_id = worker_id
        self.poll_interval = poll_interval or settings.WORKER_POLL_INTERVAL

        # 创建同步MongoDB连接
        self.client = MongoClient(settings.MONGODB_URL)
        self.db = self.client[settings.MONGODB_DB]

        # 创建下载器实例 - 完全同步
        self.downloader = MongoDBSpotifyDownloader(
            mongodb_url=settings.MONGODB_URL,
            db_name=settings.MONGODB_DB,
            client_id=settings.SPOTIFY_CLIENT_ID,
            client_secret=settings.SPOTIFY_CLIENT_SECRET,
            output_root=settings.MUSIC_LIBRARY_PATH
        )
        self._cleanup_stale_tasks()

    def run(self):
        """持续运行，处理下载任务"""
        logging.info(f"下载工作进程 {self.worker_id} 启动")

        while True:
            # 尝试获取待处理任务
            task = self._get_next_task()

            if task:
                self._process_task(task)
            else:
                # 没有任务，等待一段时间
                time.sleep(self.poll_interval)

    def _get_next_task(self):
        """获取下一个待处理任务"""
        # 查找状态为"待处理"的任务
        tasks_collection = self.db[DOWNLOAD_TASKS_COLLECTION]
        task = tasks_collection.find_one_and_update(
            {"status": STATUS_PENDING},
            {"$set": {
                "status": STATUS_IN_PROGRESS,
                "worker_id": self.worker_id,
                "started_at": datetime.now(timezone.utc)
            }},
            sort=[("priority", 1), ("created_at", 1)],
            return_document=pymongo.ReturnDocument.AFTER
        )
        return task

    @retry(max_tries=3, delay=3.0, backoff=2.0,
           exceptions=[ConnectionError, TimeoutError, pymongo.errors.PyMongoError])
    def _process_task(self, task):
        """处理下载任务，带有重试机制"""
        task_id = task["task_id"]
        task_type = task["task_type"]
        entity_id = task["entity_id"]

        logging.info(f"处理任务 {task_id}: {task_type} - {entity_id}")

        try:
            success = False
            error_msg = None

            # 根据任务类型执行下载 - 全部使用同步方法
            if task_type == "track":
                success, stats, info, files = self.downloader.download_track(
                    track_id=entity_id,
                    save=True,
                    load=True
                )

            elif task_type == "album":
                options = task.get("options", {})
                filter_artist_id = options.get("filter_artist_id")

                success, stats, info, files = self.downloader.download_album(
                    album_id=entity_id,
                    filter_artist_id=filter_artist_id,
                    save=True,
                    load=True
                )

                # 更新进度信息
                if stats:
                    self._update_task_progress(
                        task_id,
                        stats.get("success", 0),
                        stats.get("failed", 0),
                        stats.get("total", 0)
                    )

            elif task_type == "artist":
                options = task.get("options", {})
                include_singles = options.get("include_singles", True)
                include_appears_on = options.get("include_appears_on", False)
                min_tracks = options.get("min_tracks", 0)

                success, stats, info, files = self.downloader.download_artist(
                    artist_id=entity_id,
                    include_singles=include_singles,
                    include_appears_on=include_appears_on,
                    min_tracks=min_tracks,
                    save=True,
                    load=True
                )

                # 更新进度信息
                if stats:
                    self._update_task_progress(
                        task_id,
                        stats.get("successful_albums", 0),
                        stats.get("failed_albums", 0),
                        stats.get("total_albums", 0)
                    )

            else:
                error_msg = f"未知任务类型: {task_type}"
                logging.error(error_msg)

            # 完成任务
            self._complete_task(task_id, success, error_msg)
            return success

        except Exception as e:
            error_msg = f"执行任务时出错: {str(e)}"
            logging.error(error_msg)
            self._complete_task(task_id, False, error_msg)
            raise  # 重新抛出异常以便重试装饰器可以捕获

    @retry(max_tries=2, delay=1.0, exceptions=[pymongo.errors.PyMongoError])
    def _update_task_progress(self, task_id, completed, failed, total):
        """更新任务进度，带有重试机制"""
        tasks_collection = self.db[DOWNLOAD_TASKS_COLLECTION]
        tasks_collection.update_one(
            {"task_id": task_id},
            {"$set": {
                "progress": {
                    "completed": completed,
                    "failed": failed,
                    "total": total
                }
            }}
        )

    @retry(max_tries=2, delay=1.0, exceptions=[pymongo.errors.PyMongoError])
    def _complete_task(self, task_id, success, error=None):
        """完成任务，带有重试机制"""
        tasks_collection = self.db[DOWNLOAD_TASKS_COLLECTION]
        update = {
            "status": STATUS_SUCCESS if success else STATUS_FAILED,
            "completed_at": datetime.now(timezone.utc)
        }

        if error:
            update["error"] = error

        tasks_collection.update_one(
            {"task_id": task_id},
            {"$set": update}
        )

        logging.info(f"任务 {task_id} 已{'成功' if success else '失败'}{f': {error}' if error else ''}")

    @retry(max_tries=2, delay=1.0, exceptions=[pymongo.errors.PyMongoError])
    def _cleanup_stale_tasks(self):
        """
        清理由于崩溃或强制终止而卡在'in_progress'状态的任务，带有重试机制
        """
        try:
            logging.info(f"检查并清理卡住的任务...")

            # 重置所有分配给此worker的处于in_progress状态的任务
            reset_count = self.db[DOWNLOAD_TASKS_COLLECTION].update_many(
                {"worker_id": self.worker_id, "status": "in_progress"},
                {"$set": {"status": "pending", "worker_id": None}}
            ).modified_count

            if reset_count > 0:
                logging.info(f"已重置 {reset_count} 个分配给此worker但卡住的任务")

        except Exception as e:
            logging.error(f"清理卡住任务时出错: {e}")
            raise  # 重新抛出异常以便重试装饰器可以捕获

def run_worker(worker_id=None, poll_interval=None):
    """运行下载工作者"""
    worker = DownloadWorker(worker_id, poll_interval)
    worker.run()

# 运行工作进程
if __name__ == "__main__":
    import uuid
    worker_id = str(uuid.uuid4())
    run_worker(worker_id)