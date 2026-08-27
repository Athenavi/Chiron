"""
SQLAlchemy 模型定义 - UnifiedMessage
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-08-27 17:22:39
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, ForeignKey, JSON

from . import Base  # 使用统一的 Base



class UnifiedMessage(Base):
    """统一消息模型"""
    __tablename__ = 'unified_messages'




    id = Column(Integer, primary_key=True, autoincrement=True, doc='消息 ID')

    session_id = Column(String(36), ForeignKey('unified_sessions.id'), doc='会话 ID')


    role = Column(String(16), nullable=True, doc='角色')

    content = Column(Text, nullable=False, doc='内容')


    metadata_data = Column(JSON, default={}, doc='元数据（JSONB）')


    error = Column(Text, nullable=False, doc='错误信息')


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
            'metadata': self.metadata_data,
            'error': self.error,
            'created_at': self.created_at,
        }

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<UnifiedMessage id={self.id}>'


