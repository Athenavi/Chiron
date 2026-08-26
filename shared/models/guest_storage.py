"""
SQLAlchemy 模型定义 - GuestStorage
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-08-26 12:50:58
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime
import uuid

from . import Base  # 使用统一的 Base



class GuestStorage(Base):
    """访客存储模型"""
    __tablename__ = 'guest_storage'




    client_id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()), doc='客户端 ID')

    storage_id = Column(String(64), unique=True, nullable=True, doc='存储 ID')

    created_at = Column(String(255), default='now()', doc='创建时间')


    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'client_id': self.client_id,
            'storage_id': self.storage_id,
            'created_at': self.created_at,
        }

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<GuestStorage client_id={self.client_id}>'


