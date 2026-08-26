"""
SQLAlchemy 模型定义 - EntModelPolicy
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-08-26 12:50:58
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, ForeignKey
import uuid

from . import Base  # 使用统一的 Base



class EntModelPolicy(Base):
    """模型策略模型"""
    __tablename__ = 'ent_model_policies'




    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), doc='策略 ID')

    tenant_id = Column(String(36), ForeignKey('tenants.id'), doc='租户 ID')


    role_id = Column(String(36), ForeignKey('ent_roles.id'), nullable=True, doc='角色 ID')


    allowed_models = Column(String(255), default='[]', doc='允许的模型')

    per_model_limits = Column(String(255), default='{}', doc='模型限制（JSONB）')

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
            'role_id': self.role_id,
            'allowed_models': self.allowed_models,
            'per_model_limits': self.per_model_limits,
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
        return f'<EntModelPolicy id={self.id}>'


