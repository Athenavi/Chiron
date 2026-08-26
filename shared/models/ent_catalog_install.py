"""
SQLAlchemy 模型定义 - EntCatalogInstall
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-08-26 16:02:06
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, ForeignKey
import uuid

from . import Base  # 使用统一的 Base



class EntCatalogInstall(Base):
    """目录项安装模型"""
    __tablename__ = 'ent_catalog_installs'




    item_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), doc='目录项 ID')

    tenant_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), doc='租户 ID')

    enabled = Column(Boolean, default=True, doc='是否启用')


    installed_at = Column(String(255), default='now()', doc='安装时间')


    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'item_id': self.item_id,
            'tenant_id': self.tenant_id,
            'enabled': self.enabled,
            'installed_at': self.installed_at,
        }

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<EntCatalogInstall item_id={self.item_id}>'


