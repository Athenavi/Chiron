"""
SQLAlchemy 模型定义 - EntCatalogItem
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-08-27 08:42:35
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime
import uuid

from . import Base  # 使用统一的 Base



class EntCatalogItem(Base):
    """市场目录项模型"""
    __tablename__ = 'ent_catalog_items'




    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), doc='目录项 ID')

    type = Column(String(8), nullable=True, doc='类型')

    name = Column(String(128), nullable=True, doc='名称')

    version = Column(String(32), default='1.0.0', doc='版本')

    manifest = Column(String(255), default='{}', doc='清单（JSONB）')

    status = Column(String(16), default='draft', doc='状态')

    created_by = Column(String(36), nullable=True, doc='创建者')

    created_at = Column(String(255), default='now()', doc='创建时间')

    updated_at = Column(String(255), default='now()', doc='更新时间')


    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'type': self.type,
            'name': self.name,
            'version': self.version,
            'manifest': self.manifest,
            'status': self.status,
            'created_by': self.created_by,
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
        return f'<EntCatalogItem id={self.id}>'


