"""
SQLAlchemy 模型定义 - EntOidcProvider
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-08-26 16:02:06
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, ForeignKey
import uuid

from . import Base  # 使用统一的 Base



class EntOidcProvider(Base):
    """OIDC 身份提供商模型"""
    __tablename__ = 'ent_oidc_providers'




    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), doc='提供商 ID')

    tenant_id = Column(String(36), ForeignKey('tenants.id'), doc='租户 ID')


    name = Column(String(64), nullable=True, doc='名称')

    issuer = Column(String(512), nullable=True, doc='签发者')

    client_id = Column(String(256), nullable=True, doc='客户端 ID')

    client_secret_enc = Column(Text, nullable=False, doc='客户端密钥（加密）')


    scopes = Column(String(255), default='[openid,email,profile]', doc='作用域')

    enabled = Column(Boolean, default=True, doc='是否启用')


    auto_provision = Column(Boolean, default=True, doc='自动创建用户')


    role_mapping = Column(String(255), default='{}', doc='角色映射（JSONB）')

    created_at = Column(String(255), default='now()', doc='创建时间')

    updated_at = Column(String(255), default='now()', doc='更新时间')

    protocol = Column(String(16), default='oidc', doc='协议')

    provider_type = Column(String(32), default='custom', doc='提供商类型')

    display_name = Column(String(64), nullable=True, doc='显示名称')

    icon = Column(String(64), nullable=True, doc='图标')

    sort_order = Column(Integer, default=100, doc='排序顺序')


    auth_url = Column(String(512), nullable=True, doc='认证 URL')

    token_url = Column(String(512), nullable=True, doc='Token URL')

    userinfo_url = Column(String(512), nullable=True, doc='用户信息 URL')

    extra = Column(String(255), default='{}', doc='额外配置（JSONB）')


    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'name': self.name,
            'issuer': self.issuer,
            'client_id': self.client_id,
            'client_secret_enc': self.client_secret_enc,
            'scopes': self.scopes,
            'enabled': self.enabled,
            'auto_provision': self.auto_provision,
            'role_mapping': self.role_mapping,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'protocol': self.protocol,
            'provider_type': self.provider_type,
            'display_name': self.display_name,
            'icon': self.icon,
            'sort_order': self.sort_order,
            'auth_url': self.auth_url,
            'token_url': self.token_url,
            'userinfo_url': self.userinfo_url,
            'extra': self.extra,
        }

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<EntOidcProvider id={self.id}>'


