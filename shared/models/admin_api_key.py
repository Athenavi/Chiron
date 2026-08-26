"""
SQLAlchemy 模型定义 - AdminApiKey
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-08-26 12:50:58
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime
import uuid

from . import Base  # 使用统一的 Base



class AdminApiKey(Base):
    """管理员 API 密钥模型"""
    __tablename__ = 'admin_api_keys'




    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), doc='密钥 ID')

    key_hash = Column(String(64), unique=True, nullable=True, doc='密钥哈希')

    name = Column(String(100), nullable=True, doc='名称')

    tenant_id = Column(String(50), nullable=True, doc='租户 ID')

    user_id = Column(String(50), nullable=True, doc='用户 ID')

    monthly_quota = Column(Integer, default=0, doc='月配额')


    used_count = Column(BigInteger, default=0, doc='已使用次数')


    used_credits = Column(BigInteger, default=0, doc='已使用 Credits')


    status = Column(String(20), default='active', doc='状态')

    expires_at = Column(String(255), nullable=True, doc='过期时间')

    created_at = Column(String(255), default='now()', doc='创建时间')

    updated_at = Column(String(255), default='now()', doc='更新时间')

    created_by = Column(String(50), nullable=True, doc='创建者')

    description = Column(Text, nullable=True, doc='描述')


    allowed_models = Column(String(255), nullable=True, doc='允许的模型')

    rate_limit_qps = Column(Integer, default=10, doc='速率限制 QPS')



    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'key_hash': self.key_hash,
            'name': self.name,
            'tenant_id': self.tenant_id,
            'user_id': self.user_id,
            'monthly_quota': self.monthly_quota,
            'used_count': self.used_count,
            'used_credits': self.used_credits,
            'status': self.status,
            'expires_at': self.expires_at,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'created_by': self.created_by,
            'description': self.description,
            'allowed_models': self.allowed_models,
            'rate_limit_qps': self.rate_limit_qps,
        }

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<AdminApiKey id={self.id}>'


