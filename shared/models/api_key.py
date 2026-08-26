"""
SQLAlchemy 模型定义 - ApiKey
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-08-26 16:02:06
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, ForeignKey
import uuid

from . import Base  # 使用统一的 Base



class ApiKey(Base):
    """API 密钥模型"""
    __tablename__ = 'api_keys'




    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), doc='密钥 ID')

    user_id = Column(String(36), ForeignKey('users.id'), doc='用户 ID')


    name = Column(String(128), nullable=True, doc='名称')

    key_hash = Column(String(64), nullable=True, doc='密钥哈希')

    last_used_at = Column(String(255), nullable=True, doc='最后使用时间')

    expires_at = Column(String(255), nullable=True, doc='过期时间')

    created_at = Column(String(255), default='now()', doc='创建时间')

    revoked = Column(Boolean, default=False, doc='是否已撤销')



    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'key_hash': self.key_hash,
            'last_used_at': self.last_used_at,
            'expires_at': self.expires_at,
            'created_at': self.created_at,
            'revoked': self.revoked,
        }

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<ApiKey id={self.id}>'


