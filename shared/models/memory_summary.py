"""
SQLAlchemy 模型定义 - MemorySummary
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-08-27 17:22:39
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, JSON
import uuid

from . import Base  # 使用统一的 Base



class MemorySummary(Base):
    """对话摘要（L3 记忆）模型"""
    __tablename__ = 'memory_summaries'




    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()), doc='摘要 ID')

    tenant_id = Column(String(64), nullable=True, doc='租户 ID')

    user_id = Column(String(64), nullable=True, doc='用户 ID')

    session_id = Column(String(64), nullable=True, doc='会话 ID')

    content = Column(Text, nullable=False, doc='摘要内容')


    topics = Column(JSON, default=[], doc='主题列表（JSONB）')


    entities = Column(JSON, default={}, doc='实体字典（JSONB）')


    turn_start = Column(Integer, default=0, doc='起始轮次')


    turn_end = Column(Integer, default=0, doc='结束轮次')


    content_hash = Column(String(80), nullable=True, doc='内容哈希')

    access_count = Column(Integer, default=0, doc='访问次数')


    last_accessed_at = Column(String(255), nullable=True, doc='最近访问时间')

    status = Column(String(16), default='active', doc='状态')

    created_at = Column(String(255), default='now()', doc='创建时间')


    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'content': self.content,
            'topics': self.topics,
            'entities': self.entities,
            'turn_start': self.turn_start,
            'turn_end': self.turn_end,
            'content_hash': self.content_hash,
            'access_count': self.access_count,
            'last_accessed_at': self.last_accessed_at,
            'status': self.status,
            'created_at': self.created_at,
        }

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<MemorySummary id={self.id}>'


