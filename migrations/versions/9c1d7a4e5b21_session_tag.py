"""session tag

会话标签持久化：此前 tag 只存在前端 localStorage，而会话列表每次都用
`GET /v1/conversations` 的返回整体覆盖前端 sessions 数组（该返回不含 tag），
导致刷新后标签必然丢失。

本迁移给 sessions 增加 tag 列，使标签随会话详情/列表返回并支持更新。

模型来源：configs/orm/V1/models.yaml（Session.tag），ORM 文件由
scripts/generate_orm_models.py 生成；本迁移与之一致。

Revision ID: 9c1d7a4e5b21
Revises: 8b3f1d60a7c2
Create Date: 2026-02-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9c1d7a4e5b21'
down_revision: Union[str, Sequence[str], None] = '8b3f1d60a7c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('sessions', sa.Column('tag', sa.String(length=64), nullable=True))
    op.create_index('ix_sessions_tag', 'sessions', ['tag'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_sessions_tag', table_name='sessions')
    op.drop_column('sessions', 'tag')
