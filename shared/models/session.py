"""
SQLAlchemy 模型定义 - Session
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-08-27 17:11:31
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, ForeignKey
import uuid

from . import Base  # 使用统一的 Base



class Session(Base):
    """会话模型"""
    __tablename__ = 'sessions'




    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), doc='会话 ID')

    tenant_id = Column(String(36), ForeignKey('tenants.id'), doc='租户 ID')


    user_id = Column(String(36), ForeignKey('users.id'), nullable=True, doc='用户 ID')


    agent_id = Column(String(36), ForeignKey('agents.id'), nullable=True, doc='Agent ID')


    title = Column(String(255), default='', doc='标题')

    status = Column(String(16), default='active', doc='状态')

    created_at = Column(String(255), default='now()', doc='创建时间')

    updated_at = Column(String(255), default='now()', doc='更新时间')

    pinned = Column(Boolean, default=False, doc='是否置顶')



    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'user_id': self.user_id,
            'agent_id': self.agent_id,
            'title': self.title,
            'status': self.status,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'pinned': self.pinned,
        }

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<Session id={self.id}>'


