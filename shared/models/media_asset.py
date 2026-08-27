"""
SQLAlchemy 模型定义 - MediaAsset
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-08-27 08:42:35
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, ForeignKey
import uuid
from datetime import datetime

from . import Base  # 使用统一的 Base



class MediaAsset(Base):
    """媒体资源模型"""
    __tablename__ = 'media_assets'




    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), doc='资源 ID')

    tenant_id = Column(String(36), ForeignKey('tenants.id'), doc='租户 ID')


    user_id = Column(String(36), nullable=True, doc='用户 ID')

    type = Column(String(16), default='text', doc='类型')

    name = Column(String(255), nullable=True, doc='名称')

    file_url = Column(String(1024), default='', doc='文件 URL')

    file_path = Column(String(512), default='', doc='文件路径')

    mime_type = Column(String(64), default='', doc='MIME 类型')

    thumbnail = Column(String(512), default='', doc='缩略图')

    metadata = Column(String(255), default='{}', doc='元数据（JSONB）')

    tags = Column(String(255), default='[]', doc='标签')

    category = Column(String(64), default='', doc='分类')

    size = Column(BigInteger, default=0, doc='文件大小')


    created_at = Column(DateTime, default=datetime.utcnow, doc='创建时间')

    updated_at = Column(DateTime, default=datetime.utcnow, doc='更新时间')

    parent_id = Column(String(64), default='', doc='父资源 ID')


    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'user_id': self.user_id,
            'type': self.type,
            'name': self.name,
            'file_url': self.file_url,
            'file_path': self.file_path,
            'mime_type': self.mime_type,
            'thumbnail': self.thumbnail,
            'metadata': self.metadata,
            'tags': self.tags,
            'category': self.category,
            'size': self.size,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'parent_id': self.parent_id,
        }

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<MediaAsset id={self.id}>'


