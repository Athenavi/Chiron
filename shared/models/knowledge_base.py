"""
SQLAlchemy 模型定义 - KnowledgeBase
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-08-26 12:50:58
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, ForeignKey
import uuid

from . import Base  # 使用统一的 Base



class KnowledgeBase(Base):
    """知识库模型"""
    __tablename__ = 'knowledge_bases'




    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), doc='知识库 ID')

    tenant_id = Column(String(36), ForeignKey('tenants.id'), doc='租户 ID')


    user_id = Column(String(36), ForeignKey('users.id'), doc='用户 ID')


    name = Column(String(255), nullable=True, doc='名称')

    description = Column(Text, nullable=True, doc='描述')


    type = Column(String(32), default='rag', doc='类型')

    visibility = Column(String(32), default='private', doc='可见性')

    status = Column(String(32), default='active', doc='状态')

    document_count = Column(Integer, nullable=True, doc='文档数量')


    total_size_bytes = Column(BigInteger, nullable=True, doc='总大小（字节）')


    credits_consumed = Column(Integer, nullable=True, doc='已消耗 Credits')


    config = Column(String(255), default='{}', doc='JSON 配置')

    created_at = Column(String(255), default='now()', doc='创建时间')

    updated_at = Column(String(255), default='now()', doc='更新时间')

    doc_count = Column(Integer, default=0, nullable=True, doc='文档计数')



    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'user_id': self.user_id,
            'name': self.name,
            'description': self.description,
            'type': self.type,
            'visibility': self.visibility,
            'status': self.status,
            'document_count': self.document_count,
            'total_size_bytes': self.total_size_bytes,
            'credits_consumed': self.credits_consumed,
            'config': self.config,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'doc_count': self.doc_count,
        }

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<KnowledgeBase id={self.id}>'


