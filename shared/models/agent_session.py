"""
SQLAlchemy 模型定义 - AgentSession
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-08-27 17:11:31
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, ForeignKey
import uuid

from . import Base  # 使用统一的 Base



class AgentSession(Base):
    """Agent 会话模型"""
    __tablename__ = 'agent_sessions'




    id = Column(String(128), primary_key=True, default=lambda: str(uuid.uuid4()), doc='会话 ID')

    user_id = Column(String(36), ForeignKey('users.id'), doc='用户 ID')


    agent_id = Column(String(36), ForeignKey('agents.id'), nullable=True, doc='Agent ID')


    name = Column(String(128), nullable=True, doc='会话名称')

    task = Column(Text, nullable=False, doc='任务描述')


    status = Column(String(16), default='pending', doc='状态')

    result = Column(Text, nullable=True, doc='结果')


    created_at = Column(String(255), default='now()', doc='创建时间')

    updated_at = Column(String(255), default='now()', doc='更新时间')

    tenant_id = Column(String(36), ForeignKey('tenants.id'), doc='租户 ID')



    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'agent_id': self.agent_id,
            'name': self.name,
            'task': self.task,
            'status': self.status,
            'result': self.result,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'tenant_id': self.tenant_id,
        }

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<AgentSession id={self.id}>'


