"""
SQLAlchemy 模型定义 - EntQuotaPool
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-08-27 17:11:31
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, ForeignKey
import uuid

from . import Base  # 使用统一的 Base



class EntQuotaPool(Base):
    """配额池模型"""
    __tablename__ = 'ent_quota_pools'




    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), doc='配额池 ID')

    tenant_id = Column(String(36), ForeignKey('tenants.id'), doc='租户 ID')


    resource_type = Column(String(20), nullable=True, doc='资源类型')

    total_amount = Column(BigInteger, default=0, doc='总量')


    period = Column(String(10), default='monthly', doc='周期')

    created_at = Column(String(255), default='now()', doc='创建时间')

    updated_at = Column(String(255), default='now()', doc='更新时间')


    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'resource_type': self.resource_type,
            'total_amount': self.total_amount,
            'period': self.period,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<EntQuotaPool id={self.id}>'


