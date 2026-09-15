"""
SQLAlchemy 声明式基类
所有 ORM 模型统一继承此 Base
"""

from sqlalchemy.orm import declarative_base

Base = declarative_base()