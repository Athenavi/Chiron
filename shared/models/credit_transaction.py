"""
SQLAlchemy 模型定义 - CreditTransaction
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-08-26 16:02:06
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, ForeignKey
import uuid

from . import Base  # 使用统一的 Base



class CreditTransaction(Base):
    """Credits 交易记录模型"""
    __tablename__ = 'credit_transactions'




    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), doc='交易 ID')

    user_id = Column(String(36), ForeignKey('users.id'), doc='用户 ID')


    amount = Column(Integer, doc='金额')


    balance = Column(Integer, doc='余额')


    reason = Column(String(64), nullable=True, doc='原因')

    created_at = Column(String(255), default='now()', doc='创建时间')


    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'amount': self.amount,
            'balance': self.balance,
            'reason': self.reason,
            'created_at': self.created_at,
        }

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<CreditTransaction id={self.id}>'


