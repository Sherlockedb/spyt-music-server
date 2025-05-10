from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.responses import StreamingResponse
from typing import Dict, Any, Optional
import os

from app.services.file_service import FileService
from app.core.deps import get_file_service
from app.core.auth import get_current_user, get_optional_user
import mimetypes

router = APIRouter()

@router.get("/{track_id}")
async def stream_track(
    track_id: str,
    request: Request,
    file_service: FileService = Depends(get_file_service),
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_user)
):
    """
    流式传输曲目音频文件

    支持范围请求(Range)，用于音频播放器的seek功能
    """
    file_stream, content_type, file_size = await file_service.get_file_stream(track_id)

    if not file_stream:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件未找到"
        )

    # 处理范围请求 (支持音频播放器的seek功能)
    range_header = request.headers.get("range")

    if range_header:
        start_byte = 0
        end_byte = file_size - 1

        if range_header.startswith("bytes="):
            range_str = range_header[6:].split("-")
            if len(range_str) == 2:
                if range_str[0]:
                    start_byte = int(range_str[0])
                if range_str[1]:
                    end_byte = min(int(range_str[1]), file_size - 1)

        # 计算内容长度
        content_length = end_byte - start_byte + 1

        # 设置文件指针位置
        file_stream.seek(start_byte)

        # 定义异步读取生成器
        async def range_file_streamer():
            remaining = content_length
            chunk_size = 1024 * 1024  # 1MB

            try:
                while remaining > 0:
                    chunk_size = min(chunk_size, remaining)
                    data = file_stream.read(chunk_size)
                    if not data:
                        break
                    remaining -= len(data)
                    yield data
            finally:
                file_stream.close()

        # 创建部分内容响应
        headers = {
            "Content-Range": f"bytes {start_byte}-{end_byte}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(content_length),
        }

        return StreamingResponse(
            range_file_streamer(),
            status_code=206,
            media_type=content_type,
            headers=headers
        )

    # 非范围请求，返回整个文件
    async def file_streamer():
        try:
            chunk_size = 1024 * 1024  # 1MB
            while True:
                chunk = file_stream.read(chunk_size)
                if not chunk:
                    break
                yield chunk
        finally:
            file_stream.close()

    return StreamingResponse(
        file_streamer(),
        media_type=content_type,
        headers={"Content-Length": str(file_size), "Accept-Ranges": "bytes"}
    )

@router.head("/{track_id}")
async def check_track_available(
    track_id: str,
    file_service: FileService = Depends(get_file_service),
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_user)
):
    """
    检查曲目文件是否可用（HEAD请求）
    """
    file_path = await file_service.get_file_path(track_id)

    if not file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件未找到"
        )

    # 获取文件MIME类型和大小
    content_type, _ = mimetypes.guess_type(file_path)
    if not content_type:
        content_type = 'application/octet-stream'

    file_size = os.path.getsize(file_path)

    # 返回成功响应，仅包含头信息
    return Response(
        status_code=200,
        headers={
            "Content-Type": content_type,
            "Content-Length": str(file_size),
            "Accept-Ranges": "bytes"
        }
    )