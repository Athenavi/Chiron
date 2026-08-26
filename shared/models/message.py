"""
SQLAlchemy 模型定义 - Message
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-08-26 12:50:58
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, ForeignKey
import uuid

from . import Base  # 使用统一的 Base



class Message(Base):
    """消息模型"""
    __tablename__ = 'messages'




    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), doc='消息 ID')

    session_id = Column(String(36), ForeignKey('sessions.id'), doc='会话 ID')


    role = Column(String(16), nullable=True, doc='角色')

    content = Column(Text, nullable=False, doc='内容')


    tool_calls = Column(String(255), nullable=True, doc='工具调用（JSONB）')

    created_at = Column(String(255), default='now()', doc='创建时间')


    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'session_id': self.session_id,
            'role': self.role,
            'content': self.content,
            'tool_calls': self.tool_calls,
            'created_at': self.created_at,
        }

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<Message id={self.id}>'


