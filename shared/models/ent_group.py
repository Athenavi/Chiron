"""
SQLAlchemy 模型定义 - EntGroup
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-08-26 16:02:06
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, ForeignKey
import uuid

from . import Base  # 使用统一的 Base



class EntGroup(Base):
    """企业用户组模型"""
    __tablename__ = 'ent_groups'




    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), doc='组 ID')

    tenant_id = Column(String(36), ForeignKey('tenants.id'), doc='租户 ID')


    name = Column(String(128), nullable=True, doc='组名称')

    description = Column(Text, nullable=True, doc='描述')


    created_at = Column(String(255), default='now()', doc='创建时间')


    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at,
        }

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<EntGroup id={self.id}>'


