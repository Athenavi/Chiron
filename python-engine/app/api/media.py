"""媒体资源 API - 与 Go 后端 media_assets 表对接。

提供媒体文件的上传、下载、分享、搜索等功能。
通过 HTTP 客户端调用 Go 后端的 /v1/media/* 接口。
"""
from __future__ import annotations

import logging
import os
from typing import Any, Optional

import httpx
from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(tags=["media"])


# ── Pydantic Models ──

class MediaCreateRequest(BaseModel):
    """创建文本/代码媒体请求"""
    name: str
    content: str
    type: str = "text"
    category: str = "generated"
    tags: list[str] = []
    metadata: dict[str, Any] = {}


class FolderCreateRequest(BaseModel):
    """创建文件夹请求"""
    name: str
    parent_id: str = ""


class MediaUpdateRequest(BaseModel):
    """更新媒体请求"""
    name: Optional[str] = None
    parent_id: Optional[str] = None
    tags: Optional[list[str]] = None


class BatchDeleteRequest(BaseModel):
    """批量删除请求"""
    ids: list[str]


class ShareRequest(BaseModel):
    """分享链接请求"""
    expires_in_seconds: int = 900


# ── Helper Functions ──

def get_backend_url() -> str:
    """获取 Go 后端地址"""
    return os.getenv("CHIRON_BACKEND_URL", "http://localhost:8080").rstrip("/")


async def get_auth_token(request: Request) -> str:
    """从请求中获取认证 token"""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
    # 从查询参数获取（兼容旧方式）
    token = request.query_params.get("token", "")
    if token:
        return token
    raise HTTPException(status_code=401, detail="Missing authentication token")


async def create_http_client(token: str) -> httpx.AsyncClient:
    """创建带认证的 HTTP 客户端"""
    return httpx.AsyncClient(
        base_url=get_backend_url(),
        timeout=httpx.Timeout(30.0),
        headers={"Authorization": f"Bearer {token}"},
    )


# ── API Endpoints ──

@router.get("/v1/media")
async def list_media(
    request: Request,
    parent_id: str = Query("", description="父文件夹 ID"),
    category: str = Query("", description="分类筛选"),
    type: str = Query("", description="类型筛选 (text/image/video/folder)"),
    search: str = Query("", description="名称搜索"),
    tags: str = Query("", description="标签筛选（逗号分隔）"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
):
    """列出媒体资源列表"""
    token = await get_auth_token(request)
    
    async with await create_http_client(token) as client:
        params = {
            "parent_id": parent_id,
            "page": page,
            "page_size": page_size,
        }
        if category:
            params["category"] = category
        if type:
            params["type"] = type
        if search:
            params["search"] = search
        if tags:
            params["tags"] = tags
        
        try:
            response = await client.get("/v1/media", params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"List media failed: {e.response.status_code} - {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail="Failed to list media")
        except Exception as e:
            logger.error(f"List media error: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/v1/media")
async def create_media(body: MediaCreateRequest, request: Request):
    """创建文本或代码类型的媒体资源"""
    token = await get_auth_token(request)
    
    async with await create_http_client(token) as client:
        payload = body.model_dump(exclude_none=True)
        
        try:
            response = await client.post("/v1/media", json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Create media failed: {e.response.status_code} - {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail="Failed to create media")
        except Exception as e:
            logger.error(f"Create media error: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/v1/media/folders")
async def create_folder(body: FolderCreateRequest, request: Request):
    """创建虚拟文件夹"""
    token = await get_auth_token(request)
    
    async with await create_http_client(token) as client:
        payload = body.model_dump(exclude_none=True)
        
        try:
            response = await client.post("/v1/media/folders", json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Create folder failed: {e.response.status_code} - {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail="Failed to create folder")
        except Exception as e:
            logger.error(f"Create folder error: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/v1/media/folders")
async def list_folders(request: Request):
    """获取当前用户的所有文件夹"""
    token = await get_auth_token(request)
    
    async with await create_http_client(token) as client:
        try:
            response = await client.get("/v1/media/folders")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"List folders failed: {e.response.status_code} - {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail="Failed to list folders")
        except Exception as e:
            logger.error(f"List folders error: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/v1/media/{media_id}")
async def update_media(media_id: str, body: MediaUpdateRequest, request: Request):
    """更新媒体资源（重命名/移动/修改标签）"""
    token = await get_auth_token(request)
    
    async with await create_http_client(token) as client:
        payload = body.model_dump(exclude_none=True)
        
        try:
            response = await client.put(f"/v1/media/{media_id}", json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Update media failed: {e.response.status_code} - {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail="Failed to update media")
        except Exception as e:
            logger.error(f"Update media error: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/v1/media/{media_id}")
async def delete_media(media_id: str, request: Request):
    """删除单个媒体资源"""
    token = await get_auth_token(request)
    
    async with await create_http_client(token) as client:
        try:
            response = await client.delete(f"/v1/media/{media_id}")
            response.raise_for_status()
            return {"status": "success", "message": "Media deleted"}
        except httpx.HTTPStatusError as e:
            logger.error(f"Delete media failed: {e.response.status_code} - {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail="Failed to delete media")
        except Exception as e:
            logger.error(f"Delete media error: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/v1/media/batch-delete")
async def batch_delete_media(body: BatchDeleteRequest, request: Request):
    """批量删除媒体资源"""
    token = await get_auth_token(request)
    
    async with await create_http_client(token) as client:
        try:
            response = await client.post("/v1/media/batch-delete", json=body.model_dump())
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Batch delete failed: {e.response.status_code} - {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail="Failed to batch delete media")
        except Exception as e:
            logger.error(f"Batch delete error: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/v1/media/{media_id}/share")
async def share_media(media_id: str, body: ShareRequest, request: Request):
    """生成媒体文件的临时分享链接"""
    token = await get_auth_token(request)
    
    async with await create_http_client(token) as client:
        try:
            response = await client.post(f"/v1/media/{media_id}/share", json=body.model_dump())
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Share media failed: {e.response.status_code} - {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail="Failed to generate share link")
        except Exception as e:
            logger.error(f"Share media error: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/v1/media/{media_id}/sign")
async def sign_media(media_id: str, request: Request):
    """生成带签名的媒体访问 URL"""
    token = await get_auth_token(request)
    
    async with await create_http_client(token) as client:
        try:
            response = await client.post(f"/v1/media/{media_id}/sign")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Sign media failed: {e.response.status_code} - {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail="Failed to generate signed URL")
        except Exception as e:
            logger.error(f"Sign media error: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/v1/media/upload")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    category: str = Form("upload"),
    tags: str = Form(""),
):
    """上传本地文件到媒体库"""
    token = await get_auth_token(request)
    
    # 解析标签
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    
    async with await create_http_client(token) as client:
        try:
            # 读取文件内容
            file_content = await file.read()
            
            # 构建 multipart 请求
            files = {
                "file": (file.filename, file_content, file.content_type or "application/octet-stream")
            }
            data = {"category": category}
            if tag_list:
                data["tags"] = ",".join(tag_list)
            
            response = await client.post("/v1/media/upload", files=files, data=data)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Upload file failed: {e.response.status_code} - {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail="Failed to upload file")
        except Exception as e:
            logger.error(f"Upload file error: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/v1/search/media")
async def search_media(
    request: Request,
    q: str = Query(..., description="搜索关键词"),
    limit: int = Query(20, ge=1, le=100, description="返回结果数量限制"),
):
    """全文搜索媒体文件"""
    token = await get_auth_token(request)
    
    async with await create_http_client(token) as client:
        try:
            params = {"q": q, "limit": limit}
            response = await client.get("/v1/search/media", params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Search media failed: {e.response.status_code} - {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail="Failed to search media")
        except Exception as e:
            logger.error(f"Search media error: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")


# ── AI Media Processing Interfaces (预留) ──

@router.post("/v1/media/{media_id}/analyze")
async def analyze_media(media_id: str, request: Request):
    """AI 分析媒体文件（图像识别、文档解析等）"""
    token = await get_auth_token(request)
    
    # TODO: 实现 AI 媒体分析功能
    # 1. 从 Go 后端获取媒体元数据
    # 2. 根据 MIME 类型选择处理策略：
    #    - image/*: 调用视觉模型进行图像识别
    #    - application/pdf: 使用 PDF 解析器提取文本和结构
    #    - application/msword, application/vnd.openxmlformats-officedocument.*: Word 文档解析
    # 3. 提取元数据（尺寸、格式、页数等）
    # 4. 更新媒体 metadata 字段
    
    raise HTTPException(status_code=501, detail="AI media analysis not yet implemented")


@router.post("/v1/media/{media_id}/extract-metadata")
async def extract_metadata(media_id: str, request: Request):
    """提取媒体文件元数据"""
    token = await get_auth_token(request)
    
    # TODO: 实现元数据提取功能
    # 支持提取：图片尺寸、视频时长、文档页数、文件大小等
    
    raise HTTPException(status_code=501, detail="Metadata extraction not yet implemented")
