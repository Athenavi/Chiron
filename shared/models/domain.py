"""
SQLAlchemy 模型定义 - Domain
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-08-26 16:02:06
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, ForeignKey
import uuid

from . import Base  # 使用统一的 Base



class Domain(Base):
    """域名模型"""
    __tablename__ = 'domains'




    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), doc='域名 ID')

    tenant_id = Column(String(36), ForeignKey('tenants.id'), doc='租户 ID')


    domain = Column(String(255), unique=True, nullable=True, doc='域名')

    ssl_status = Column(String(16), default='none', doc='SSL 状态')

    verified = Column(Boolean, default=False, doc='是否已验证')


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
            'domain': self.domain,
            'ssl_status': self.ssl_status,
            'verified': self.verified,
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
        return f'<Domain id={self.id}>'


