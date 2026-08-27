"""
SQLAlchemy 模型定义 - AdminWorkflow
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-08-27 17:22:39
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, JSON
import uuid

from . import Base  # 使用统一的 Base



class AdminWorkflow(Base):
    """工作流管理模型"""
    __tablename__ = 'admin_workflows'




    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), doc='工作流 ID')

    workflow_id = Column(String(50), unique=True, nullable=True, doc='工作流标识')

    name = Column(String(100), nullable=True, doc='名称')

    description = Column(Text, nullable=True, doc='描述')


    nodes = Column(JSON, doc='节点（JSONB）')


    edges = Column(JSON, doc='边（JSONB）')


    error_handling_strategy = Column(String(20), default='fail_fast', doc='错误处理策略')

    timeout_ms = Column(Integer, default=30000, doc='超时（毫秒）')


    max_retries = Column(Integer, default=3, doc='最大重试次数')


    version = Column(Integer, default=1, doc='版本号')


    published_version = Column(Integer, default=0, doc='发布版本号')


    status = Column(String(20), default='draft', doc='状态')

    created_by = Column(String(50), nullable=True, doc='创建者')

    created_at = Column(String(255), default='now()', doc='创建时间')

    updated_at = Column(String(255), default='now()', doc='更新时间')

    published_at = Column(String(255), nullable=True, doc='发布时间')


    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'workflow_id': self.workflow_id,
            'name': self.name,
            'description': self.description,
            'nodes': self.nodes,
            'edges': self.edges,
            'error_handling_strategy': self.error_handling_strategy,
            'timeout_ms': self.timeout_ms,
            'max_retries': self.max_retries,
            'version': self.version,
            'published_version': self.published_version,
            'status': self.status,
            'created_by': self.created_by,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'published_at': self.published_at,
        }

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<AdminWorkflow id={self.id}>'


