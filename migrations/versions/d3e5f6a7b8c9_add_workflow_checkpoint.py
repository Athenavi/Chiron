"""add checkpoint to workflow_instances

Workflow 断点续跑（多引擎实例/崩溃恢复）：
- checkpoint jsonb 保存 {state, done_nodes}：每完成一个节点由执行方写回（updated_at 即最后心跳）；
- worker 重投/续跑时读取 checkpoint 跳过已完成节点继续（engine 节点为纯函数可重放）；
- NULL = 尚未产生断点（从头执行）。

Revision ID: d3e5f6a7b8c9
Revises: b2e4d6f8a0c2
Create Date: 2026-09-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "d3e5f6a7b8c9"
down_revision = "b2e4d6f8a0c2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workflow_instances",
        sa.Column("checkpoint", postgresql.JSONB, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("workflow_instances", "checkpoint")
