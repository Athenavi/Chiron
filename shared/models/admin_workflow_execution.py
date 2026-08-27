"""
SQLAlchemy 模型定义 - AdminWorkflowExecution
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-08-27 08:42:35
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime
import uuid

from . import Base  # 使用统一的 Base



class AdminWorkflowExecution(Base):
    """工作流执行记录模型"""
    __tablename__ = 'admin_workflow_executions'




    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), doc='执行 ID')

    workflow_id = Column(String(50), nullable=True, doc='工作流 ID')

    workflow_version = Column(Integer, doc='工作流版本')


    status = Column(String(20), default='running', doc='状态')

    started_at = Column(String(255), default='now()', doc='开始时间')

    completed_at = Column(String(255), nullable=True, doc='完成时间')

    duration_ms = Column(Integer, nullable=True, doc='耗时（毫秒）')


    input_data = Column(String(255), nullable=True, doc='输入数据（JSONB）')

    output_data = Column(String(255), nullable=True, doc='输出数据（JSONB）')

    error_message = Column(Text, nullable=True, doc='错误信息')


    triggered_by = Column(String(50), nullable=True, doc='触发者')

    node_results = Column(String(255), default='[]', doc='节点结果（JSONB）')


    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'workflow_id': self.workflow_id,
            'workflow_version': self.workflow_version,
            'status': self.status,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'duration_ms': self.duration_ms,
            'input_data': self.input_data,
            'output_data': self.output_data,
            'error_message': self.error_message,
            'triggered_by': self.triggered_by,
            'node_results': self.node_results,
        }

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<AdminWorkflowExecution id={self.id}>'


