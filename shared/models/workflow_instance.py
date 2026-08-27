"""
SQLAlchemy 模型定义 - WorkflowInstance
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-08-27 17:11:31
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, JSON
import uuid

from . import Base  # 使用统一的 Base



class WorkflowInstance(Base):
    """工作流实例模型"""
    __tablename__ = 'workflow_instances'




    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()), doc='实例 ID')

    user_id = Column(String(64), default='', doc='用户 ID')

    workflow_id = Column(String(64), default='', doc='工作流 ID')

    workflow_name = Column(String(255), default='', doc='工作流名称')

    status = Column(String(16), default='running', doc='状态')

    results = Column(JSON, default={}, doc='结果（JSONB）')


    error = Column(Text, nullable=True, doc='错误信息')


    created_at = Column(String(255), default='now()', doc='创建时间')

    updated_at = Column(String(255), default='now()', doc='更新时间')


    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'workflow_id': self.workflow_id,
            'workflow_name': self.workflow_name,
            'status': self.status,
            'results': self.results,
            'error': self.error,
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
        return f'<WorkflowInstance id={self.id}>'


