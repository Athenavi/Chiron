"""
SQLAlchemy 模型定义 - AdminTenant
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-08-26 16:02:06
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime
import uuid

from . import Base  # 使用统一的 Base



class AdminTenant(Base):
    """租户管理模型"""
    __tablename__ = 'admin_tenants'




    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), doc='租户 ID')

    tenant_id = Column(String(50), unique=True, nullable=True, doc='租户标识')

    name = Column(String(100), nullable=True, doc='名称')

    company_name = Column(String(200), nullable=True, doc='公司名称')

    contact_email = Column(String(100), nullable=True, doc='联系邮箱')

    contact_phone = Column(String(20), nullable=True, doc='联系电话')

    max_api_keys = Column(Integer, default=10, doc='最大 API 密钥数')


    max_models = Column(Integer, default=5, doc='最大模型数')


    monthly_quota = Column(BigInteger, default=0, doc='月配额')


    max_concurrent_sessions = Column(Integer, default=10, doc='最大并发会话数')


    status = Column(String(20), default='active', doc='状态')

    expires_at = Column(String(255), nullable=True, doc='过期时间')

    created_at = Column(String(255), default='now()', doc='创建时间')

    updated_at = Column(String(255), default='now()', doc='更新时间')

    created_by = Column(String(50), nullable=True, doc='创建者')

    features = Column(String(255), default='{}', doc='功能特性（JSONB）')


    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'name': self.name,
            'company_name': self.company_name,
            'contact_email': self.contact_email,
            'contact_phone': self.contact_phone,
            'max_api_keys': self.max_api_keys,
            'max_models': self.max_models,
            'monthly_quota': self.monthly_quota,
            'max_concurrent_sessions': self.max_concurrent_sessions,
            'status': self.status,
            'expires_at': self.expires_at,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'created_by': self.created_by,
            'features': self.features,
        }

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<AdminTenant id={self.id}>'


