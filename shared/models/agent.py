"""
SQLAlchemy 模型定义 - Agent
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-08-27 17:22:39
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, ForeignKey, JSON
import uuid

from . import Base  # 使用统一的 Base



class Agent(Base):
    """Agent 配置模型"""
    __tablename__ = 'agents'




    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), doc='Agent ID')

    tenant_id = Column(String(36), ForeignKey('tenants.id'), doc='租户 ID')


    name = Column(String(255), nullable=True, doc='名称')

    description = Column(Text, nullable=True, doc='描述')


    system_prompt = Column(Text, nullable=True, doc='系统提示词')


    tools = Column(JSON, default=[], doc='工具配置（JSONB）')


    llm_config = Column(JSON, default={}, doc='LLM 配置（JSONB）')


    max_turns = Column(Integer, default=10, doc='最大轮次')


    timeout_seconds = Column(Integer, default=120, doc='超时秒数')


    enabled = Column(Boolean, default=True, doc='是否启用')


    created_at = Column(String(255), default='now()', doc='创建时间')

    updated_at = Column(String(255), default='now()', doc='更新时间')

    user_id = Column(String(36), nullable=True, doc='用户 ID')

    visibility = Column(String(16), default='private', doc='可见性')


    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'name': self.name,
            'description': self.description,
            'system_prompt': self.system_prompt,
            'tools': self.tools,
            'llm_config': self.llm_config,
            'max_turns': self.max_turns,
            'timeout_seconds': self.timeout_seconds,
            'enabled': self.enabled,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'user_id': self.user_id,
            'visibility': self.visibility,
        }

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<Agent id={self.id}>'


