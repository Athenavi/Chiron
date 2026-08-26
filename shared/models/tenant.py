"""
SQLAlchemy 模型定义 - Tenant
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-08-26 12:50:58
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime
import uuid

from . import Base  # 使用统一的 Base



class Tenant(Base):
    """租户模型"""
    __tablename__ = 'tenants'




    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), doc='租户 ID')

    name = Column(String(255), nullable=True, doc='租户名称')

    created_at = Column(String(255), default='now()', doc='创建时间')

    status = Column(String(16), default='active', doc='状态')


    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'name': self.name,
            'created_at': self.created_at,
            'status': self.status,
        }

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<Tenant id={self.id}>'


