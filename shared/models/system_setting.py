"""
SQLAlchemy 模型定义 - SystemSetting
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-08-27 08:42:35
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime

from . import Base  # 使用统一的 Base



class SystemSetting(Base):
    """系统设置模型"""
    __tablename__ = 'system_settings'




    id = Column(Integer, primary_key=True, autoincrement=True, doc='设置 ID')

    category = Column(String(32), nullable=True, doc='分类')

    key = Column(String(64), nullable=True, doc='键')

    value = Column(String(255), nullable=True, doc='值（JSONB）')

    updated_at = Column(String(255), default='now()', doc='更新时间')

    updated_by = Column(String(36), nullable=True, doc='更新者')

    encrypted = Column(Boolean, default=False, doc='是否加密')



    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'category': self.category,
            'key': self.key,
            'value': self.value,
            'updated_at': self.updated_at,
            'updated_by': self.updated_by,
            'encrypted': self.encrypted,
        }

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<SystemSetting id={self.id}>'


