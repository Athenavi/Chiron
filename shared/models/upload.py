"""
SQLAlchemy 模型定义 - Upload
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-08-27 17:22:39
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, ForeignKey
import uuid

from . import Base  # 使用统一的 Base



class Upload(Base):
    """文件上传模型"""
    __tablename__ = 'uploads'




    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()), doc='上传 ID')

    user_id = Column(String(64), default='', doc='用户 ID')

    name = Column(String(255), nullable=True, doc='文件名')

    size = Column(BigInteger, default=0, doc='文件大小')


    mime_type = Column(String(64), default='', doc='MIME 类型')

    purpose = Column(String(16), default='generic', doc='用途')

    parent_id = Column(String(64), default='', doc='父资源 ID')

    category = Column(String(64), default='', doc='分类')

    chunk_size = Column(Integer, default=2097152, doc='分块大小')


    chunk_count = Column(Integer, default=0, doc='分块数量')


    chunks_received = Column(String(255), default='[]', doc='已接收分块')

    status = Column(String(16), default='pending', doc='状态')

    created_at = Column(String(255), default='now()', doc='创建时间')

    updated_at = Column(String(255), default='now()', doc='更新时间')

    tenant_id = Column(String(36), ForeignKey('tenants.id'), doc='租户 ID')



    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'size': self.size,
            'mime_type': self.mime_type,
            'purpose': self.purpose,
            'parent_id': self.parent_id,
            'category': self.category,
            'chunk_size': self.chunk_size,
            'chunk_count': self.chunk_count,
            'chunks_received': self.chunks_received,
            'status': self.status,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'tenant_id': self.tenant_id,
        }

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<Upload id={self.id}>'


