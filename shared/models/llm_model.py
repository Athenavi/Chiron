"""
SQLAlchemy 模型定义 - LlmModel
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-08-27 17:11:31
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime
import uuid

from . import Base  # 使用统一的 Base



class LlmModel(Base):
    """LLM 模型模型"""
    __tablename__ = 'llm_models'




    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), doc='模型 ID')

    provider = Column(String(32), nullable=True, doc='提供商')

    name = Column(String(128), nullable=True, doc='模型名称')

    display_name = Column(String(128), default='', doc='显示名称')

    enabled = Column(Boolean, default=True, doc='是否启用')


    context_window = Column(Integer, default=8192, doc='上下文窗口大小')


    created_at = Column(String(255), default='now()', doc='创建时间')

    updated_at = Column(String(255), default='now()', doc='更新时间')


    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'provider': self.provider,
            'name': self.name,
            'display_name': self.display_name,
            'enabled': self.enabled,
            'context_window': self.context_window,
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
        return f'<LlmModel id={self.id}>'


