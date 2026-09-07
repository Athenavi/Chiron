"""add run_lease_at to cron_jobs

多网关实例下定时任务去重：行级 CAS 租约列（跨实例仅一个实例执行）。
execute() 前以 UPDATE ... WHERE run_lease_at IS NULL OR run_lease_at < now()-interval
抢租约，影响行数=1 才执行；执行结束/失败后清空。

Revision ID: c1a0b2d3e4f5
Revises: 433e78cd17b7
Create Date: 2026-09-08
"""
from alembic import op
import sqlalchemy as sa

revision = "c1a0b2d3e4f5"
down_revision = "433e78cd17b7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cron_jobs",
        sa.Column("run_lease_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("cron_jobs", "run_lease_at")
