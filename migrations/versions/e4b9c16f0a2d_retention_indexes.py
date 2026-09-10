"""retention indexes

A7/C1：保留策略清理所需的索引。
- turns 按 (status, created_at) 删除保留期外已完结的回合（见 internal/api/retention.go）；
- task_idempotency 按 (status, updated_at) 删除保留期外记录
  （见 python-engine/app/queue/idempotency.py 的 purge_older_than）。

背景：这两张表都是"每回合/每任务一行"，无保留策略时企业化长期运行会持续膨胀。

Revision ID: e4b9c16f0a2d
Revises: d2a7b41c9f03
Create Date: 2026-02-11 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e4b9c16f0a2d'
down_revision: Union[str, Sequence[str], None] = 'd2a7b41c9f03'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index('ix_turns_status_created', 'turns', ['status', 'created_at'])
    op.create_index('ix_task_idempotency_status_updated', 'task_idempotency', ['status', 'updated_at'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_task_idempotency_status_updated', table_name='task_idempotency')
    op.drop_index('ix_turns_status_created', table_name='turns')
