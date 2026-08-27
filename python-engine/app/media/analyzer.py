"""AI驱动的媒体内容分析器"""

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


async def analyze_image(image_url: str, prompt: str = None) -> dict[str, Any]:
    """分析图片内容

    Args:
        image_url: 图片URL
        prompt: 自定义分析提示词

    Returns:
        分析结果字典
    """
    if not prompt:
        prompt = """请详细分析这张图片的内容，包括：
1. 主要对象和场景描述
2. 颜色、构图和风格
3. 可能的用途或含义
4. 任何文字内容（如有）

请用中文回答。"""

    try:
        from app.llm.client import get_llm_client

        llm = get_llm_client()

        # 构建多模态消息
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            }
        ]

        response = await llm.chat(messages, model="gpt-4-vision-preview")
        return {
            "success": True,
            "analysis": (
                response.content if hasattr(response, "content") else str(response)
            ),
            "model": getattr(response, "model", "unknown"),
            "analyzed_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Image analysis failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "analyzed_at": datetime.utcnow().isoformat(),
        }


async def extract_metadata(media_url: str, media_type: str) -> dict[str, Any]:
    """提取媒体元数据

    Args:
        media_url: 媒体URL
        media_type: 媒体类型 (image/video/audio/document)

    Returns:
        元数据字典
    """
    metadata = {
        "url": media_url,
        "type": media_type,
        "extracted_at": datetime.utcnow().isoformat(),
    }

    try:
        # 根据类型调用不同的提取逻辑
        if media_type == "image":
            # TODO: 可以使用PIL或其他库提取EXIF等
            metadata["note"] = "Basic metadata only, EXIF extraction not implemented"
        elif media_type == "video":
            # TODO: 可以使用ffmpeg-python提取视频信息
            metadata["note"] = (
                "Basic metadata only, video info extraction not implemented"
            )
        elif media_type == "audio":
            # TODO: 可以使用mutagen提取音频元数据
            metadata["note"] = (
                "Basic metadata only, audio metadata extraction not implemented"
            )
        elif media_type == "document":
            # TODO: 可以使用PyPDF2等提取文档信息
            metadata["note"] = "Basic metadata only, document parsing not implemented"

        return metadata
    except Exception as e:
        logger.error(f"Metadata extraction failed: {e}")
        metadata["error"] = str(e)
        return metadata
