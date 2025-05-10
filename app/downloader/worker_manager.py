import logging
import os
import signal
import sys
import uuid
import multiprocessing
from typing import List, Dict, Any
import setproctitle

from app.core.config import settings
from app.downloader.download_worker import run_worker

class WorkerManager:
    """
    工作者管理器，负责启动和管理下载工作者进程
    """
    
    def __init__(self, worker_count=None):
        """
        初始化工作者管理器
        
        参数:
            worker_count: 工作者数量，默认使用配置中的值
        """
        self.worker_count = worker_count or settings.WORKER_CONCURRENCY
        self.processes = []
        self.running = False
        
        # 设置日志
        self._setup_logging()
    
    def _setup_logging(self):
        """设置日志"""
        log_file = os.path.join(os.path.dirname(settings.LOG_FILE), "worker_manager.log")
        
        handlers = [logging.StreamHandler()]
        if log_file:
            log_dir = os.path.dirname(log_file)
            if not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
            handlers.append(logging.FileHandler(log_file, encoding='utf-8'))
        
        logging.basicConfig(
            level=getattr(logging, settings.LOG_LEVEL),
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=handlers
        )
    
    def start(self):
        """启动所有工作者进程"""
        if self.running:
            logging.warning("工作者管理器已经在运行")
            return
        
        self.running = True
        logging.info(f"启动工作者管理器，工作者数量: {self.worker_count}")
        
        # 设置信号处理器
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # 启动工作者进程
        for i in range(self.worker_count):
            worker_id = f"worker-{i+1}"
            self.start_worker(worker_id)
        
        # 保持主进程运行，直到收到信号
        try:
            # 等待所有进程完成
            while self.running and self.processes:
                # 检查所有进程是否都在运行
                for i, process in enumerate(self.processes[:]):
                    if not process.is_alive():
                        logging.warning(f"工作者进程 {process.name} 已终止，退出码: {process.exitcode}")
                        self.processes.remove(process)
                        
                        # 如果管理器仍在运行，重新启动工作者
                        if self.running:
                            worker_id = f"worker-{uuid.uuid4()}"
                            self.start_worker(worker_id)
                
                # 短暂休眠，避免CPU过度使用
                import time
                time.sleep(5)
                
        except KeyboardInterrupt:
            logging.info("收到中断信号，正在停止工作者管理器...")
            self.stop()
    
    def start_worker(self, worker_id):
        """
        启动单个工作者进程
        
        参数:
            worker_id: 工作者ID
        """
        logging.info(f"启动工作者: {worker_id}")
        
        # 创建参数列表
        args = (worker_id, settings.WORKER_POLL_INTERVAL)
        
        # 创建进程
        process = multiprocessing.Process(
            target=run_worker_process,  # 改为同步版本的进程函数
            args=args,
            name=worker_id
        )
        
        # 设置为守护进程
        process.daemon = True
        
        # 启动进程
        process.start()
        self.processes.append(process)
        logging.info(f"工作者 {worker_id} 已启动，PID: {process.pid}")
    
    def stop(self):
        """停止所有工作者进程"""
        if not self.running:
            return
        
        logging.info("正在停止所有工作者进程...")
        self.running = False
        
        # 向所有进程发送终止信号
        for process in self.processes:
            if process.is_alive():
                logging.info(f"正在终止工作者进程 {process.name} (PID: {process.pid})")
                # 发送SIGTERM信号以允许进程优雅关闭
                os.kill(process.pid, signal.SIGTERM)
        
        # 等待所有进程终止
        for process in self.processes:
            process.join(timeout=30)
            
            # 如果进程仍在运行，强制终止
            if process.is_alive():
                logging.warning(f"工作者进程 {process.name} 没有响应，强制终止")
                process.kill()
                process.join(timeout=10)

                # 如果还是没响应，强制终止
                if process.is_alive():
                    logging.warning(f"工作者进程 {process.name} 没有响应，强制终止")
                    process.kill()
        
        self.processes = []
        logging.info("所有工作者进程已停止")
    
    def signal_handler(self, sig, frame):
        """处理信号"""
        if sig in (signal.SIGINT, signal.SIGTERM):
            logging.info(f"收到信号 {sig}，正在停止工作者管理器...")
            self.stop()


def run_worker_process(worker_id, poll_interval):
    """
    运行工作者进程的入口函数 - 同步版本
    
    参数:
        worker_id: 工作者ID
        poll_interval: 轮询间隔时间（秒）
    """
    try:
        # 设置进程标题
        setproctitle.setproctitle(f"spyt_music_worker_{worker_id}")
        
        # 直接创建并运行DownloadWorker实例
        run_worker(worker_id, poll_interval)
    except Exception as e:
        logging.error(f"工作者进程 {worker_id} 出错: {e}")
        sys.exit(1)


def start_workers(worker_count=None):
    """
    启动工作者管理器
    
    参数:
        worker_count: 工作者数量
    """
    manager = WorkerManager(worker_count)
    manager.start()


if __name__ == "__main__":
    # 如果直接运行此脚本，启动工作者管理器
    worker_count = int(sys.argv[1]) if len(sys.argv) > 1 else None
    start_workers(worker_count)