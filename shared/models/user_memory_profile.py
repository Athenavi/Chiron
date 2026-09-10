"""
SQLAlchemy 模型定义 - UserMemoryProfile
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-09-10 23:04:54
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, JSON
import uuid
from datetime import datetime

from . import Base  # 使用统一的 Base



class UserMemoryProfile(Base):
    """用户记忆档案（L2 记忆）模型"""
    __tablename__ = 'user_memory_profile'




    tenant_id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()), doc='租户 ID')

    user_id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()), doc='用户 ID')

    slot = Column(String(32), primary_key=True, default=lambda: str(uuid.uuid4()), doc='槽位类型')

    item_key = Column(String(128), primary_key=True, default=lambda: str(uuid.uuid4()), doc='键')

    item_value = Column(JSON, doc='值（JSONB）')


    confidence = Column(Integer, default=50, doc='置信度 0-100')


    source = Column(String(16), default='derived', doc='来源')

    version = Column(Integer, default=1, doc='版本号')


    confirmed_at = Column(DateTime, nullable=True, doc='确认时间')    

    last_referenced_at = Column(DateTime, nullable=True, doc='最近引用时间')    

    created_at = Column(DateTime, default=datetime.utcnow, doc='创建时间')    

    updated_at = Column(DateTime, default=datetime.utcnow, doc='更新时间')    


    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'tenant_id': self.tenant_id,
            'user_id': self.user_id,
            'slot': self.slot,
            'item_key': self.item_key,
            'item_value': self.item_value,
            'confidence': self.confidence,
            'source': self.source,
            'version': self.version,
            'confirmed_at': self.confirmed_at.isoformat() if self.confirmed_at else None,
            'last_referenced_at': self.last_referenced_at.isoformat() if self.last_referenced_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<UserMemoryProfile tenant_id={self.tenant_id}>'


