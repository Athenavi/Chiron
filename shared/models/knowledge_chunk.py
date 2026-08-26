"""
SQLAlchemy 模型定义 - KnowledgeChunk
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-08-26 16:02:06
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, ForeignKey
import uuid

from . import Base  # 使用统一的 Base



class KnowledgeChunk(Base):
    """知识库分块模型"""
    __tablename__ = 'knowledge_chunks'




    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), doc='分块 ID')

    document_id = Column(String(36), ForeignKey('knowledge_documents.id'), doc='文档 ID')


    knowledge_base_id = Column(String(36), ForeignKey('knowledge_bases.id'), doc='知识库 ID')


    tenant_id = Column(String(36), ForeignKey('tenants.id'), doc='租户 ID')


    chunk_index = Column(Integer, doc='分块索引')


    content = Column(Text, nullable=False, doc='内容')


    metadata = Column(String(255), default='{}', doc='元数据（JSONB）')

    search_vector = Column(String(255), nullable=True, doc='搜索向量')

    created_at = Column(String(255), default='now()', doc='创建时间')


    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'document_id': self.document_id,
            'knowledge_base_id': self.knowledge_base_id,
            'tenant_id': self.tenant_id,
            'chunk_index': self.chunk_index,
            'content': self.content,
            'metadata': self.metadata,
            'search_vector': self.search_vector,
            'created_at': self.created_at,
        }

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<KnowledgeChunk id={self.id}>'


