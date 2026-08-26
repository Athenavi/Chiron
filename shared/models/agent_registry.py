"""
SQLAlchemy 模型定义 - AgentRegistry
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-08-26 12:50:58
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime
import uuid

from . import Base  # 使用统一的 Base



class AgentRegistry(Base):
    """Agent 注册表模型"""
    __tablename__ = 'agent_registry'




    agent_type = Column(String(32), primary_key=True, default=lambda: str(uuid.uuid4()), doc='Agent 类型')

    name = Column(String(128), nullable=True, doc='名称')

    description = Column(Text, nullable=False, doc='描述')


    enabled = Column(Boolean, default=True, doc='是否启用')


    config = Column(String(255), default='{}', doc='JSON 配置')

    created_at = Column(String(255), default='now()', doc='创建时间')


    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'agent_type': self.agent_type,
            'name': self.name,
            'description': self.description,
            'enabled': self.enabled,
            'config': self.config,
            'created_at': self.created_at,
        }

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<AgentRegistry agent_type={self.agent_type}>'


