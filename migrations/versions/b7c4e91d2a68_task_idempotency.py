"""task_idempotency

后台任务幂等闸门表：`engine:tasks` 消费组是 at-least-once（ACK 前崩溃会被 reclaim
重投），若无唯一约束，有副作用的任务（workflow_run/tool_job/rag_index）会重复执行。
`idempotency_key` 主键即唯一约束，worker 执行前用
`INSERT ... ON CONFLICT DO UPDATE ... WHERE status <> 'completed'` 抢占，
已完成的任务再次投递会被跳过（见 python-engine/app/queue/idempotency.py）。

Revision ID: b7c4e91d2a68
Revises: a0b3a964fb54
Create Date: 2026-02-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7c4e91d2a68'
down_revision: Union[str, Sequence[str], None] = 'a0b3a964fb54'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'task_idempotency',
        sa.Column('idempotency_key', sa.String(length=255), nullable=False),
        sa.Column('task_id', sa.String(length=64), nullable=True),
        sa.Column('task_type', sa.String(length=64), nullable=True),
        sa.Column('tenant_id', sa.String(length=64), nullable=True),
        sa.Column('status', sa.String(length=16), nullable=False, server_default='running'),
        sa.Column('attempt', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('result_ref', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint('idempotency_key'),
    )
    op.create_index('ix_task_idempotency_task_id', 'task_idempotency', ['task_id'])
    op.create_index('ix_task_idempotency_status', 'task_idempotency', ['status'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_task_idempotency_status', table_name='task_idempotency')
    op.drop_index('ix_task_idempotency_task_id', table_name='task_idempotency')
    op.drop_table('task_idempotency')
