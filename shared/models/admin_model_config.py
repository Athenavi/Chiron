"""
SQLAlchemy 模型定义 - AdminModelConfig
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-08-27 17:22:39
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, JSON
import uuid

from . import Base  # 使用统一的 Base



class AdminModelConfig(Base):
    """模型配置模型"""
    __tablename__ = 'admin_model_configs'




    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), doc='配置 ID')

    model_id = Column(String(50), unique=True, nullable=True, doc='模型 ID')

    display_name = Column(String(100), nullable=True, doc='显示名称')

    provider = Column(String(50), nullable=True, doc='提供商')

    priority = Column(Integer, default=0, doc='优先级')


    weight = Column(Integer, default=100, doc='权重')


    fallback_chain = Column(String(255), nullable=True, doc='回退链')

    max_rpm = Column(Integer, default=1000, doc='每分钟最大请求数')


    max_tpm = Column(Integer, default=500000, doc='每分钟最大 Tokens')


    concurrent_limit = Column(Integer, default=50, doc='并发限制')


    status = Column(String(20), default='active', doc='状态')

    is_default = Column(Boolean, default=False, doc='是否默认')


    input_cost_per_1m = Column(String(255), default='0', doc='输入成本（每百万）')

    output_cost_per_1m = Column(String(255), default='0', doc='输出成本（每百万）')

    config_json = Column(JSON, default={}, doc='JSON 配置')


    created_at = Column(String(255), default='now()', doc='创建时间')

    updated_at = Column(String(255), default='now()', doc='更新时间')


    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'model_id': self.model_id,
            'display_name': self.display_name,
            'provider': self.provider,
            'priority': self.priority,
            'weight': self.weight,
            'fallback_chain': self.fallback_chain,
            'max_rpm': self.max_rpm,
            'max_tpm': self.max_tpm,
            'concurrent_limit': self.concurrent_limit,
            'status': self.status,
            'is_default': self.is_default,
            'input_cost_per_1m': self.input_cost_per_1m,
            'output_cost_per_1m': self.output_cost_per_1m,
            'config_json': self.config_json,
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
        return f'<AdminModelConfig id={self.id}>'


