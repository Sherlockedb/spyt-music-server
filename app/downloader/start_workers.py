import argparse
import sys
import signal
import logging

from app.downloader.worker_manager import WorkerManager
from app.core.config import settings

# 全局变量保存WorkerManager实例
worker_manager = None

def signal_handler(sig, frame):
    """处理终止信号"""
    if sig in (signal.SIGINT, signal.SIGTERM):
        print(f"\n收到信号 {sig}，正在优雅关闭...")
        if worker_manager:
            worker_manager.stop()
        sys.exit(0)

def main():
    """命令行入口点"""
    global worker_manager

    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    # 设置信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    parser = argparse.ArgumentParser(description='启动Spyt音乐下载工作者')

    parser.add_argument(
        '-c', '--count',
        type=int,
        default=settings.WORKER_CONCURRENCY,
        help=f'工作者数量 (默认: {settings.WORKER_CONCURRENCY})'
    )

    args = parser.parse_args()

    print(f"正在启动 {args.count} 个下载工作者...")

    # 创建并启动WorkerManager
    worker_manager = WorkerManager(args.count)

    try:
        worker_manager.start()
    except KeyboardInterrupt:
        print("\n收到中断，正在优雅关闭...")
        worker_manager.stop()
    except Exception as e:
        logging.error(f"启动工作者管理器时出错: {e}")
        worker_manager.stop()
        sys.exit(1)

if __name__ == "__main__":
    main()