import os
import time
import logging
import pymongo
from pymongo import MongoClient
from datetime import datetime, timezone
import signal

from app.downloader.mongo_downloader import MongoDBSpotifyDownloader
from app.db.schemas import STATUS_PENDING, STATUS_IN_PROGRESS, STATUS_SUCCESS, STATUS_FAILED, DOWNLOAD_TASKS_COLLECTION
from app.core.config import settings
from app.core.retry import retry

# 添加一个自定义适配器，为每条日志添加worker_id和PID
class WorkerLogAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        return f"[{self.extra['worker_id']} {self.extra['pid']}] {msg}", kwargs

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
        self.pid = os.getpid()

        # 设置带有worker_id和PID的日志
        self._setup_logging()

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

    def _setup_logging(self):
        """设置带有worker_id和PID的日志"""
        # 获取根日志记录器
        root_logger = logging.getLogger()

        # 创建适配器，为所有日志添加worker_id和PID前缀
        self.logger = WorkerLogAdapter(root_logger, {'worker_id': self.worker_id, 'pid': self.pid})

        # 设置日志格式，确保包含worker_id和PID
        if not root_logger.handlers:
            # 避免重复配置处理器
            log_format = "%(asctime)s - %(levelname)s - %(message)s"
            handlers = [logging.StreamHandler()]

            # 自定义日志文件名为downloader_worker.log
            log_file = os.path.join(os.path.dirname(settings.LOG_FILE), "downloader_worker.log")

            # 确保日志目录存在
            log_dir = os.path.dirname(log_file)
            if not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)

            # 添加文件处理器
            handlers.append(logging.FileHandler(log_file))

            # 配置所有处理器
            for handler in handlers:
                handler.setFormatter(logging.Formatter(log_format))
                root_logger.addHandler(handler)

            # 设置日志级别
            root_logger.setLevel(getattr(logging, settings.LOG_LEVEL))

            # 记录日志文件路径
            print(f"日志将写入文件: {os.path.abspath(log_file)}")

    def run(self):
        """持续运行，处理下载任务"""
        self.logger.info(f"下载工作进程启动")

        # 设置信号处理器
        self._setup_signal_handlers()

        self.running = True

        try:
            while self.running:
                # 尝试获取待处理任务
                task = self._get_next_task()

                if task:
                    self._process_task(task)
                else:
                    # 没有任务，等待一段时间
                    time.sleep(self.poll_interval)

        except KeyboardInterrupt:
            self.logger.info(f"收到中断信号，正在关闭...")
        finally:
            self._cleanup()

    def _setup_signal_handlers(self):
        """设置信号处理器"""
        def handle_signal(sig, frame):
            self.logger.info(f"收到信号 {sig}，准备关闭...")
            self.running = False

        signal.signal(signal.SIGTERM, handle_signal)
        signal.signal(signal.SIGINT, handle_signal)

    def _cleanup(self):
        """清理资源"""
        self.logger.info(f"正在清理资源...")

        # 清理数据库连接
        if hasattr(self, 'client') and self.client:
            self.client.close()
            self.logger.info("数据库连接已关闭")

        # 清理下载器资源
        if hasattr(self, 'downloader') and hasattr(self.downloader, 'close'):
            self.downloader.close()
            self.logger.info("下载器资源已释放")

        self.logger.info(f"已安全关闭")

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

        self.logger.info(f"处理任务 {task_id}: {task_type} - {entity_id}")

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
                self.logger.error(error_msg)

            # 完成任务
            self._complete_task(task_id, success, error_msg)
            return success

        except Exception as e:
            error_msg = f"执行任务时出错: {str(e)}"
            self.logger.error(error_msg)
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

        self.logger.info(f"任务 {task_id} 已{'成功' if success else '失败'}{f': {error}' if error else ''}")

    @retry(max_tries=2, delay=1.0, exceptions=[pymongo.errors.PyMongoError])
    def _cleanup_stale_tasks(self):
        """
        清理由于崩溃或强制终止而卡在'in_progress'状态的任务，带有重试机制
        """
        try:
            self.logger.info(f"检查并清理卡住的任务...")

            # 重置所有分配给此worker的处于in_progress状态的任务
            reset_count = self.db[DOWNLOAD_TASKS_COLLECTION].update_many(
                {"worker_id": self.worker_id, "status": "in_progress"},
                {"$set": {"status": "pending", "worker_id": None}}
            ).modified_count

            if reset_count > 0:
                self.logger.info(f"已重置 {reset_count} 个分配给此worker但卡住的任务")

        except Exception as e:
            self.logger.error(f"清理卡住任务时出错: {e}")
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