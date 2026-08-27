"""
SQLAlchemy 模型定义 - AdminRedisConfig
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-08-27 08:42:35
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime
import uuid

from . import Base  # 使用统一的 Base



class AdminRedisConfig(Base):
    """Redis 配置管理模型"""
    __tablename__ = 'admin_redis_configs'




    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), doc='配置 ID')

    host = Column(String(100), nullable=True, doc='主机')

    port = Column(Integer, default=6379, doc='端口')


    password_hash = Column(String(256), nullable=True, doc='密码哈希')

    db_index = Column(Integer, default=0, doc='数据库索引')


    pool_size = Column(Integer, default=100, doc='连接池大小')


    min_idle_connections = Column(Integer, default=10, doc='最小空闲连接数')


    max_conn_age = Column(String(255), default='00:05:00', doc='最大连接时长')

    status = Column(String(20), default='active', doc='状态')

    last_health_check = Column(String(255), nullable=True, doc='最后健康检查')

    avg_latency_ms = Column(String(255), default='0', doc='平均延迟（毫秒）')

    memory_used_mb = Column(String(255), default='0', doc='内存使用量（MB）')

    connected_clients = Column(Integer, default=0, doc='已连接客户端数')


    hits = Column(BigInteger, default=0, doc='命中次数')


    misses = Column(BigInteger, default=0, doc='未命中次数')


    created_at = Column(String(255), default='now()', doc='创建时间')

    updated_at = Column(String(255), default='now()', doc='更新时间')


    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'host': self.host,
            'port': self.port,
            'password_hash': self.password_hash,
            'db_index': self.db_index,
            'pool_size': self.pool_size,
            'min_idle_connections': self.min_idle_connections,
            'max_conn_age': self.max_conn_age,
            'status': self.status,
            'last_health_check': self.last_health_check,
            'avg_latency_ms': self.avg_latency_ms,
            'memory_used_mb': self.memory_used_mb,
            'connected_clients': self.connected_clients,
            'hits': self.hits,
            'misses': self.misses,
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
        return f'<AdminRedisConfig id={self.id}>'


