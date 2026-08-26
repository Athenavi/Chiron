"""
SQLAlchemy 模型定义 - EntUserIdentity
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-08-26 12:50:58
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, ForeignKey
import uuid

from . import Base  # 使用统一的 Base



class EntUserIdentity(Base):
    """用户身份绑定模型"""
    __tablename__ = 'ent_user_identities'




    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), doc='身份 ID')

    user_id = Column(String(36), ForeignKey('users.id'), doc='用户 ID')


    provider_id = Column(String(36), ForeignKey('ent_oidc_providers.id'), doc='提供商 ID')


    subject = Column(String(256), nullable=True, doc='主体标识')

    email = Column(String(255), nullable=True, doc='邮箱')

    created_at = Column(String(255), default='now()', doc='创建时间')


    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'provider_id': self.provider_id,
            'subject': self.subject,
            'email': self.email,
            'created_at': self.created_at,
        }

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<EntUserIdentity id={self.id}>'


