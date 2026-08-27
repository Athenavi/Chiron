"""
SQLAlchemy 模型定义 - UnifiedSession
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-08-27 17:22:39
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, JSON
import uuid

from . import Base  # 使用统一的 Base



class UnifiedSession(Base):
    """统一会话模型"""
    __tablename__ = 'unified_sessions'




    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), doc='会话 ID')

    tenant_id = Column(String(36), nullable=True, doc='租户 ID')

    user_id = Column(String(36), nullable=True, doc='用户 ID')

    title = Column(String(255), default='', doc='标题')

    mode = Column(String(16), default='auto', doc='模式')

    shared_context = Column(JSON, default={}, doc='共享上下文（JSONB）')


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
            'title': self.title,
            'mode': self.mode,
            'shared_context': self.shared_context,
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
        return f'<UnifiedSession id={self.id}>'


