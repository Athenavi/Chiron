"""baseline billing tables

把 `credit_transactions` / `payments` 纳入 Alembic 管理。

背景（附带技术债）：这两张表此前只由 Go 侧 `billing.PGStore.EnsureTables` 兜底创建，
造成"schema 双来源"——迁移链里没有它们，而应用启动时会建。后果：以迁移为唯一事实源
的部署（云 PG / DBA 执行迁移）会出现"迁移说没有、应用却建了"的偏差，且 `turn_id`
唯一索引一度只存在于 EnsureTables。

DDL 与 EnsureTables 保持一致且全部使用 IF NOT EXISTS：
- 对既有库 = no-op（幂等）；
- 对全新库 = 一步到位（不再依赖应用启动兜底）。

Revision ID: f7c2d05a1b8e
Revises: e4b9c16f0a2d
Create Date: 2026-02-11 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'f7c2d05a1b8e'
down_revision: Union[str, Sequence[str], None] = 'e4b9c16f0a2d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# 与 internal/billing/pgstore.go 的 EnsureTables 完全一致（含 turn_id 与唯一索引）
CREDIT_TX_DDL = """
CREATE TABLE IF NOT EXISTS credit_transactions (
    id VARCHAR(32) PRIMARY KEY,
    user_id VARCHAR(32) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    amount INTEGER NOT NULL,
    balance INTEGER NOT NULL,
    reason VARCHAR(64) NOT NULL,
    turn_id VARCHAR(36),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
"""

PAYMENTS_DDL = """
CREATE TABLE IF NOT EXISTS payments (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(32) NOT NULL,
    channel VARCHAR(16) NOT NULL,
    credits INTEGER NOT NULL,
    amount_cents BIGINT NOT NULL DEFAULT 0,
    currency VARCHAR(8) NOT NULL DEFAULT 'CNY',
    status VARCHAR(16) NOT NULL DEFAULT 'pending',
    qr_code TEXT,
    provider_order_id VARCHAR(64) NOT NULL DEFAULT '',
    trade_no VARCHAR(64) NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    paid_at TIMESTAMPTZ,
    expired_at TIMESTAMPTZ
)
"""


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(CREDIT_TX_DDL)
    op.execute("CREATE INDEX IF NOT EXISTS idx_credit_tx_user ON credit_transactions(user_id, created_at DESC)")
    # 幂等扣费键（同一 turn 只扣一次；唯一索引允许多个 NULL）
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uniq_credit_tx_turn ON credit_transactions(turn_id)")

    op.execute(PAYMENTS_DDL)
    op.execute("CREATE INDEX IF NOT EXISTS idx_payments_user ON payments(user_id, created_at DESC)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_payments_provider "
        "ON payments(provider_order_id) WHERE provider_order_id <> ''"
    )


def downgrade() -> None:
    """Downgrade schema.

    故意不 DROP 这两张表：它们在本次迁移引入前由应用兜底创建，库里很可能已有
    计费流水/充值订单数据。降级只应回退"迁移对结构的所有权"，不应删除业务数据。
    """
    pass
