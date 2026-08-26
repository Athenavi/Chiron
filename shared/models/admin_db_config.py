"""
SQLAlchemy 模型定义 - AdminDbConfig
由代码生成器自动生成 (基于 models.yaml / routes.yaml) - 请勿手动修改
生成时间：2026-08-26 16:02:06
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime
import uuid

from . import Base  # 使用统一的 Base



class AdminDbConfig(Base):
    """数据库配置管理模型"""
    __tablename__ = 'admin_db_configs'




    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), doc='配置 ID')

    dsn = Column(String(500), nullable=True, doc='DSN')

    host = Column(String(100), nullable=True, doc='主机')

    port = Column(Integer, default=5432, doc='端口')


    dbname = Column(String(100), nullable=True, doc='数据库名')

    max_open_connections = Column(Integer, default=25, doc='最大打开连接数')


    max_idle_connections = Column(Integer, default=5, doc='最大空闲连接数')


    conn_max_lifetime = Column(String(255), default='00:05:00', doc='连接最大生命周期')

    status = Column(String(20), default='active', doc='状态')

    last_health_check = Column(String(255), nullable=True, doc='最后健康检查')

    avg_query_time_ms = Column(String(255), default='0', doc='平均查询时间（毫秒）')

    database_size_mb = Column(String(255), default='0', doc='数据库大小（MB）')

    total_tables = Column(Integer, default=0, nullable=True, doc='总表数')


    sequential_scans = Column(BigInteger, default=0, nullable=True, doc='顺序扫描次数')


    created_at = Column(String(255), default='now()', doc='创建时间')

    updated_at = Column(String(255), default='now()', doc='更新时间')


    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'dsn': self.dsn,
            'host': self.host,
            'port': self.port,
            'dbname': self.dbname,
            'max_open_connections': self.max_open_connections,
            'max_idle_connections': self.max_idle_connections,
            'conn_max_lifetime': self.conn_max_lifetime,
            'status': self.status,
            'last_health_check': self.last_health_check,
            'avg_query_time_ms': self.avg_query_time_ms,
            'database_size_mb': self.database_size_mb,
            'total_tables': self.total_tables,
            'sequential_scans': self.sequential_scans,
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
        return f'<AdminDbConfig id={self.id}>'


