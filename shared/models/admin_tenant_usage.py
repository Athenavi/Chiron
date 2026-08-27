"""
SQLAlchemy 模型定义 - AdminTenantUsage
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-08-27 17:11:31
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, ForeignKey
import uuid

from . import Base  # 使用统一的 Base



class AdminTenantUsage(Base):
    """租户使用统计模型"""
    __tablename__ = 'admin_tenant_usage'




    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), doc='统计 ID')

    tenant_id = Column(String(50), ForeignKey('admin_tenants.tenant_id'), doc='租户 ID')


    stat_date = Column(String(255), nullable=True, doc='统计日期')

    api_calls = Column(BigInteger, default=0, doc='API 调用次数')


    tokens_used = Column(BigInteger, default=0, doc='Tokens 使用量')


    credits_consumed = Column(BigInteger, default=0, doc='Credits 消耗')


    storage_mb = Column(String(255), default='0', doc='存储使用量（MB）')

    created_at = Column(String(255), default='now()', doc='创建时间')


    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'stat_date': self.stat_date,
            'api_calls': self.api_calls,
            'tokens_used': self.tokens_used,
            'credits_consumed': self.credits_consumed,
            'storage_mb': self.storage_mb,
            'created_at': self.created_at,
        }

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<AdminTenantUsage id={self.id}>'


