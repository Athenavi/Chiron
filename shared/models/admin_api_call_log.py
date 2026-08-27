"""
SQLAlchemy 模型定义 - AdminApiCallLog
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-08-27 17:22:39
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, ForeignKey
import uuid

from . import Base  # 使用统一的 Base



class AdminApiCallLog(Base):
    """API 调用日志模型"""
    __tablename__ = 'admin_api_call_logs'




    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), doc='日志 ID')

    api_key_id = Column(String(36), ForeignKey('admin_api_keys.id'), nullable=True, doc='API 密钥 ID')


    model_id = Column(String(50), nullable=True, doc='模型 ID')

    workflow_id = Column(String(50), nullable=True, doc='工作流 ID')

    endpoint = Column(String(100), nullable=True, doc='端点')

    method = Column(String(10), default='POST', doc='HTTP 方法')

    request_size_bytes = Column(Integer, nullable=True, doc='请求大小')


    response_size_bytes = Column(Integer, nullable=True, doc='响应大小')


    duration_ms = Column(Integer, nullable=True, doc='耗时（毫秒）')


    status_code = Column(Integer, nullable=True, doc='状态码')


    retry_count = Column(Integer, default=0, doc='重试次数')


    input_tokens = Column(Integer, default=0, doc='输入 Tokens')


    output_tokens = Column(Integer, default=0, doc='输出 Tokens')


    credits_consumed = Column(BigInteger, default=0, doc='消耗 Credits')


    created_at = Column(String(255), default='now()', doc='创建时间')


    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'api_key_id': self.api_key_id,
            'model_id': self.model_id,
            'workflow_id': self.workflow_id,
            'endpoint': self.endpoint,
            'method': self.method,
            'request_size_bytes': self.request_size_bytes,
            'response_size_bytes': self.response_size_bytes,
            'duration_ms': self.duration_ms,
            'status_code': self.status_code,
            'retry_count': self.retry_count,
            'input_tokens': self.input_tokens,
            'output_tokens': self.output_tokens,
            'credits_consumed': self.credits_consumed,
            'created_at': self.created_at,
        }

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<AdminApiCallLog id={self.id}>'


