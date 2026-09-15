"""
SQLAlchemy 模型定义 - SchemaMigration
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-08-26 16:02:06
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime

from . import Base  # 使用统一的 Base



class SchemaMigration(Base):
    """数据库迁移记录模型"""
    __tablename__ = 'schema_migrations'




    version = Column(BigInteger, primary_key=True, autoincrement=True, doc='迁移版本号')

    name = Column(String(255), nullable=True, doc='迁移名称')

    checksum = Column(String(128), nullable=True, doc='校验和')

    applied_at = Column(String(255), default='now()', doc='应用时间')


    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'version': self.version,
            'name': self.name,
            'checksum': self.checksum,
            'applied_at': self.applied_at,
        }

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<SchemaMigration version={self.version}>'


