"""
SQLAlchemy 模型定义 - EntQuotaAllocation
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-08-27 17:11:31
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, ForeignKey
import uuid

from . import Base  # 使用统一的 Base



class EntQuotaAllocation(Base):
    """配额分配模型"""
    __tablename__ = 'ent_quota_allocations'




    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), doc='分配 ID')

    pool_id = Column(String(36), ForeignKey('ent_quota_pools.id'), doc='配额池 ID')


    target_type = Column(String(10), nullable=True, doc='目标类型')

    target_id = Column(String(36), nullable=True, doc='目标 ID')

    amount = Column(BigInteger, default=0, doc='分配量')


    created_at = Column(String(255), default='now()', doc='创建时间')


    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'pool_id': self.pool_id,
            'target_type': self.target_type,
            'target_id': self.target_id,
            'amount': self.amount,
            'created_at': self.created_at,
        }

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<EntQuotaAllocation id={self.id}>'


