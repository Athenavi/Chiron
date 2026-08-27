"""
SQLAlchemy 模型定义 - KnowledgeDocument
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-08-27 08:42:35
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, ForeignKey
import uuid

from . import Base  # 使用统一的 Base



class KnowledgeDocument(Base):
    """知识库文档模型"""
    __tablename__ = 'knowledge_documents'




    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), doc='文档 ID')

    knowledge_base_id = Column(String(36), ForeignKey('knowledge_bases.id'), doc='知识库 ID')


    tenant_id = Column(String(36), ForeignKey('tenants.id'), doc='租户 ID')


    user_id = Column(String(36), ForeignKey('users.id'), doc='用户 ID')


    name = Column(String(255), nullable=True, doc='文档名称')

    file_url = Column(String(1024), nullable=True, doc='文件 URL')

    file_type = Column(String(32), nullable=True, doc='文件类型')

    file_size_bytes = Column(BigInteger, default=0, nullable=True, doc='文件大小')


    chunk_count = Column(Integer, default=0, nullable=True, doc='分块数量')


    status = Column(String(32), default='pending', doc='状态')

    error_message = Column(Text, nullable=True, doc='错误信息')


    metadata = Column(String(255), default='{}', doc='元数据（JSONB）')

    created_at = Column(String(255), default='now()', doc='创建时间')

    updated_at = Column(String(255), default='now()', doc='更新时间')

    content = Column(String(255), nullable=True, doc='二进制内容')


    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'knowledge_base_id': self.knowledge_base_id,
            'tenant_id': self.tenant_id,
            'user_id': self.user_id,
            'name': self.name,
            'file_url': self.file_url,
            'file_type': self.file_type,
            'file_size_bytes': self.file_size_bytes,
            'chunk_count': self.chunk_count,
            'status': self.status,
            'error_message': self.error_message,
            'metadata': self.metadata,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'content': self.content,
        }

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<KnowledgeDocument id={self.id}>'


