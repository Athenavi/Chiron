"""
SQLAlchemy 模型定义 - CronJob
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-08-27 08:42:35
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime
import uuid

from . import Base  # 使用统一的 Base



class CronJob(Base):
    """定时任务模型"""
    __tablename__ = 'cron_jobs'




    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), doc='任务 ID')

    name = Column(String(128), nullable=True, doc='名称')

    schedule = Column(String(64), nullable=True, doc='调度表达式')

    task = Column(String(255), nullable=True, doc='任务')

    enabled = Column(Boolean, default=True, doc='是否启用')


    last_run_at = Column(String(255), nullable=True, doc='最后运行时间')

    last_status = Column(String(16), default='pending', doc='最后状态')

    created_at = Column(String(255), default='now()', doc='创建时间')

    updated_at = Column(String(255), default='now()', doc='更新时间')

    tenant_id = Column(String(36), nullable=True, doc='租户 ID')

    user_id = Column(String(36), nullable=True, doc='用户 ID')

    webhook_token = Column(String(64), default='', doc='Webhook Token')


    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'name': self.name,
            'schedule': self.schedule,
            'task': self.task,
            'enabled': self.enabled,
            'last_run_at': self.last_run_at,
            'last_status': self.last_status,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'tenant_id': self.tenant_id,
            'user_id': self.user_id,
            'webhook_token': self.webhook_token,
        }

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<CronJob id={self.id}>'


