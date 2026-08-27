"""
SQLAlchemy 模型定义 - EntGroupMember
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-08-27 17:22:39
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, ForeignKey
import uuid

from . import Base  # 使用统一的 Base



class EntGroupMember(Base):
    """用户组成员模型"""
    __tablename__ = 'ent_group_members'




    group_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), doc='组 ID')

    user_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), doc='用户 ID')


    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'group_id': self.group_id,
            'user_id': self.user_id,
        }

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<EntGroupMember group_id={self.group_id}>'


