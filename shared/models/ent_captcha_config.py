"""
SQLAlchemy 模型定义 - EntCaptchaConfig
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-08-27 17:22:39
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, ForeignKey
import uuid

from . import Base  # 使用统一的 Base



class EntCaptchaConfig(Base):
    """验证码配置模型"""
    __tablename__ = 'ent_captcha_config'




    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), doc='配置 ID')

    tenant_id = Column(String(36), ForeignKey('tenants.id'), doc='租户 ID')


    provider = Column(String(32), default='turnstile', doc='提供商')

    site_key = Column(String(256), default='', doc='站点密钥')

    secret_enc = Column(Text, nullable=False, doc='密钥（加密）')


    verify_url = Column(String(512), nullable=True, doc='验证 URL')

    enabled = Column(Boolean, default=False, doc='是否启用')


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
            'provider': self.provider,
            'site_key': self.site_key,
            'secret_enc': self.secret_enc,
            'verify_url': self.verify_url,
            'enabled': self.enabled,
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
        return f'<EntCaptchaConfig id={self.id}>'


