"""
SQLAlchemy 模型定义 - MarketingCampaign
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-08-27 17:11:31
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, ForeignKey, JSON
import uuid

from . import Base  # 使用统一的 Base



class MarketingCampaign(Base):
    """营销活动模型"""
    __tablename__ = 'marketing_campaigns'




    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), doc='活动 ID')

    tenant_id = Column(String(36), ForeignKey('tenants.id'), doc='租户 ID')


    user_id = Column(String(32), default='', doc='用户 ID')

    name = Column(String(255), nullable=True, doc='名称')

    description = Column(Text, nullable=False, doc='描述')


    campaign_type = Column(String(32), default='email', doc='活动类型')

    config = Column(JSON, default={}, doc='JSON 配置')


    status = Column(String(16), default='draft', doc='状态')

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
            'user_id': self.user_id,
            'name': self.name,
            'description': self.description,
            'campaign_type': self.campaign_type,
            'config': self.config,
            'status': self.status,
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
        return f'<MarketingCampaign id={self.id}>'


