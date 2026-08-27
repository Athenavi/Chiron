"""
SQLAlchemy 模型定义 - AdminCronJob
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-08-27 17:11:31
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, JSON
import uuid

from . import Base  # 使用统一的 Base



class AdminCronJob(Base):
    """定时任务模型"""
    __tablename__ = 'admin_cron_jobs'




    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), doc='任务 ID')

    job_id = Column(String(50), unique=True, nullable=True, doc='任务标识')

    name = Column(String(100), nullable=True, doc='名称')

    schedule = Column(String(50), nullable=True, doc='调度表达式')

    last_run_at = Column(String(255), nullable=True, doc='最后运行时间')

    last_run_status = Column(String(20), nullable=True, doc='最后运行状态')

    last_error = Column(Text, nullable=True, doc='最后错误信息')


    next_run_at = Column(String(255), nullable=True, doc='下次运行时间')

    enabled = Column(Boolean, default=True, doc='是否启用')


    metadata = Column(JSON, default={}, doc='元数据（JSONB）')


    created_at = Column(String(255), default='now()', doc='创建时间')

    updated_at = Column(String(255), default='now()', doc='更新时间')


    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'job_id': self.job_id,
            'name': self.name,
            'schedule': self.schedule,
            'last_run_at': self.last_run_at,
            'last_run_status': self.last_run_status,
            'last_error': self.last_error,
            'next_run_at': self.next_run_at,
            'enabled': self.enabled,
            'metadata': self.metadata,
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
        return f'<AdminCronJob id={self.id}>'


