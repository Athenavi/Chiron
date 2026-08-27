"""
SQLAlchemy 模型定义 - AdminDomain
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-08-27 08:42:35
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, ForeignKey
import uuid

from . import Base  # 使用统一的 Base



class AdminDomain(Base):
    """域名管理模型"""
    __tablename__ = 'admin_domains'




    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), doc='域名 ID')

    domain = Column(String(100), unique=True, nullable=True, doc='域名')

    tenant_id = Column(String(50), ForeignKey('admin_tenants.tenant_id'), doc='租户 ID')


    dns_provider = Column(String(50), nullable=True, doc='DNS 提供商')

    dns_record_id = Column(String(100), nullable=True, doc='DNS 记录 ID')

    cname_target = Column(String(200), nullable=True, doc='CNAME 目标')

    ssl_status = Column(String(20), default='pending', doc='SSL 状态')

    ssl_expires_at = Column(String(255), nullable=True, doc='SSL 过期时间')

    auto_renew = Column(Boolean, default=True, doc='自动续期')


    status = Column(String(20), default='active', doc='状态')

    verified_at = Column(String(255), nullable=True, doc='验证时间')

    verified_by = Column(String(50), nullable=True, doc='验证者')

    created_at = Column(String(255), default='now()', doc='创建时间')

    updated_at = Column(String(255), default='now()', doc='更新时间')


    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'domain': self.domain,
            'tenant_id': self.tenant_id,
            'dns_provider': self.dns_provider,
            'dns_record_id': self.dns_record_id,
            'cname_target': self.cname_target,
            'ssl_status': self.ssl_status,
            'ssl_expires_at': self.ssl_expires_at,
            'auto_renew': self.auto_renew,
            'status': self.status,
            'verified_at': self.verified_at,
            'verified_by': self.verified_by,
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
        return f'<AdminDomain id={self.id}>'


