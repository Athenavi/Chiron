"""
SQLAlchemy 模型定义 - User
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-08-27 08:42:35
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, ForeignKey
import uuid

from . import Base  # 使用统一的 Base



class User(Base):
    """用户模型"""
    __tablename__ = 'users'




    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), doc='用户 ID')

    tenant_id = Column(String(36), ForeignKey('tenants.id'), doc='租户 ID')


    email = Column(String(255), nullable=True, doc='邮箱')

    name = Column(String(128), nullable=True, doc='名称')

    password_hash = Column(String(255), nullable=True, doc='密码哈希')

    role = Column(String(16), default='user', doc='角色')

    storage_id = Column(String(64), unique=True, nullable=True, doc='存储 ID')

    credits = Column(Integer, default=1000, doc='Credits 余额')


    created_at = Column(String(255), default='now()', doc='创建时间')

    updated_at = Column(String(255), default='now()', doc='更新时间')

    phone = Column(String(32), nullable=True, doc='手机号')

    password_set = Column(Boolean, default=True, doc='是否已设置密码')


    settings = Column(String(255), default='{}', doc='用户设置（JSONB）')


    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'email': self.email,
            'name': self.name,
            'password_hash': self.password_hash,
            'role': self.role,
            'storage_id': self.storage_id,
            'credits': self.credits,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'phone': self.phone,
            'password_set': self.password_set,
            'settings': self.settings,
        }

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<User id={self.id}>'


