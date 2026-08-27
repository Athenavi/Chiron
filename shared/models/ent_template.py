"""
SQLAlchemy 模型定义 - EntTemplate
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-08-27 08:42:35
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime
import uuid

from . import Base  # 使用统一的 Base



class EntTemplate(Base):
    """企业模板模型"""
    __tablename__ = 'ent_templates'




    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), doc='模板 ID')

    type = Column(String(16), nullable=True, doc='模板类型')

    name = Column(String(128), nullable=True, doc='名称')

    description = Column(Text, nullable=False, doc='描述')


    payload = Column(String(255), nullable=True, doc='负载（JSONB）')

    published = Column(Boolean, default=True, doc='是否已发布')


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
            'description': self.description,
            'payload': self.payload,
            'published': self.published,
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
        return f'<EntTemplate id={self.id}>'


