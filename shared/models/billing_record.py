"""
SQLAlchemy 模型定义 - BillingRecord
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-09-10 23:04:54
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, ForeignKey
import uuid
from datetime import datetime

from . import Base  # 使用统一的 Base



class BillingRecord(Base):
    """计费记录模型"""
    __tablename__ = 'billing_records'




    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), doc='记录 ID')

    tenant_id = Column(String(36), ForeignKey('tenants.id'), doc='租户 ID')


    user_id = Column(String(36), ForeignKey('users.id'), doc='用户 ID')


    session_id = Column(String(36), ForeignKey('sessions.id'), nullable=True, doc='会话 ID')


    input_tokens = Column(BigInteger, default=0, doc='输入 Tokens')


    output_tokens = Column(BigInteger, default=0, doc='输出 Tokens')


    cost_cents = Column(Integer, default=0, doc='费用（分）')


    created_at = Column(DateTime, default=datetime.utcnow, doc='创建时间')    

    group_id = Column(String(36), nullable=True, doc='分组 ID')

    turn_id = Column(String(36), nullable=True, doc='所属回合 ID（turn 一致性：消息/工具/计费同回合可幂等叙事）')


    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'input_tokens': self.input_tokens,
            'output_tokens': self.output_tokens,
            'cost_cents': self.cost_cents,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'group_id': self.group_id,
            'turn_id': self.turn_id,
        }

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<BillingRecord id={self.id}>'


