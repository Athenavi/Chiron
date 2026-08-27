"""
SQLAlchemy 模型定义 - EntTenantPolicy
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-08-27 17:22:39
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, ForeignKey, JSON
import uuid

from . import Base  # 使用统一的 Base



class EntTenantPolicy(Base):
    """租户策略模型"""
    __tablename__ = 'ent_tenant_policies'




    tenant_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), doc='租户 ID')

    privacy_mode = Column(Boolean, default=False, doc='隐私模式')


    data_retention_days = Column(Integer, default=0, nullable=True, doc='数据保留天数')


    training_allowed = Column(Boolean, default=True, doc='允许训练')


    redaction_rules = Column(JSON, default={}, doc='脱敏规则（JSONB）')


    updated_at = Column(String(255), default='now()', doc='更新时间')


    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'tenant_id': self.tenant_id,
            'privacy_mode': self.privacy_mode,
            'data_retention_days': self.data_retention_days,
            'training_allowed': self.training_allowed,
            'redaction_rules': self.redaction_rules,
            'updated_at': self.updated_at,
        }

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<EntTenantPolicy tenant_id={self.tenant_id}>'


