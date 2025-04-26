import argparse
import sys
import os

from app.downloader.worker_manager import start_workers
from app.core.config import settings


def main():
    """命令行入口点"""
    parser = argparse.ArgumentParser(description='启动Spyt音乐下载工作者')
    
    parser.add_argument(
        '-c', '--count',
        type=int,
        default=settings.WORKER_CONCURRENCY,
        help=f'工作者数量 (默认: {settings.WORKER_CONCURRENCY})'
    )
    
    args = parser.parse_args()
    
    print(f"正在启动 {args.count} 个下载工作者...")
    start_workers(args.count)


if __name__ == "__main__":
    main()