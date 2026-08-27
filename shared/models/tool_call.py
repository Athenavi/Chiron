"""
SQLAlchemy 模型定义 - ToolCall
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-08-27 08:42:35
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime
import uuid

from . import Base  # 使用统一的 Base



class ToolCall(Base):
    """工具调用记录模型"""
    __tablename__ = 'tool_calls'




    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), doc='调用 ID')

    session_id = Column(String(36), nullable=True, doc='会话 ID')

    message_id = Column(String(36), nullable=True, doc='消息 ID')

    tool_name = Column(String(128), nullable=True, doc='工具名称')

    input = Column(String(255), default='{}', doc='输入参数（JSONB）')

    output = Column(Text, nullable=False, doc='输出结果')


    is_error = Column(Boolean, default=False, doc='是否有错误')


    duration_ms = Column(BigInteger, default=0, doc='耗时（毫秒）')


    created_at = Column(String(255), default='now()', doc='创建时间')


    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'session_id': self.session_id,
            'message_id': self.message_id,
            'tool_name': self.tool_name,
            'input': self.input,
            'output': self.output,
            'is_error': self.is_error,
            'duration_ms': self.duration_ms,
            'created_at': self.created_at,
        }

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<ToolCall id={self.id}>'


