"""
SQLAlchemy 模型定义 - AdminDatabaseBackup
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-08-26 16:02:06
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime
import uuid

from . import Base  # 使用统一的 Base



class AdminDatabaseBackup(Base):
    """数据库备份模型"""
    __tablename__ = 'admin_database_backups'




    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), doc='备份 ID')

    backup_type = Column(String(20), default='manual', doc='备份类型')

    description = Column(Text, nullable=True, doc='描述')


    file_path = Column(String(500), nullable=True, doc='文件路径')

    file_size_mb = Column(String(255), nullable=True, doc='文件大小（MB）')

    status = Column(String(20), default='running', doc='状态')

    error_message = Column(Text, nullable=True, doc='错误信息')


    started_at = Column(String(255), default='now()', doc='开始时间')

    completed_at = Column(String(255), nullable=True, doc='完成时间')

    duration_seconds = Column(Integer, nullable=True, doc='耗时（秒）')


    created_by = Column(String(50), nullable=True, doc='创建者')


    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'backup_type': self.backup_type,
            'description': self.description,
            'file_path': self.file_path,
            'file_size_mb': self.file_size_mb,
            'status': self.status,
            'error_message': self.error_message,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'duration_seconds': self.duration_seconds,
            'created_by': self.created_by,
        }

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<AdminDatabaseBackup id={self.id}>'


