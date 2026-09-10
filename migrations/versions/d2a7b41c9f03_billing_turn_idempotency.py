"""billing idempotency by turn

B4：计费按回合幂等。同一 turn 的重复扣费/重复记账在 PG 层被唯一索引挡住：
- credit_transactions.turn_id + 唯一索引（允许多个 NULL，非 turn 流水不受影响）
  → DeductTokens 走 `ON CONFLICT (turn_id) DO NOTHING`，占位失败即"已扣过"，
    不再改余额、返回当前余额（重试安全）。
- billing_records.turn_id 由普通索引升级为唯一索引
  → RecordTokenUsage 用 `ON CONFLICT (turn_id) DO NOTHING`，同一回合只记一条明细。

背景：此前重试（网关超时重发、SSE 中断后重试）会再次扣费与重复记账（000.md 第 14 条）。

注意：credit_transactions 由 Go 侧 billing.PGStore.EnsureTables 兜底建表，
并非基线迁移创建，故此处用 ALTER TABLE IF EXISTS / DO 块保证任意库都能升级。
Go 侧 EnsureTables 也同步加了同样的列与唯一索引（双保险）。

Revision ID: d2a7b41c9f03
Revises: c1f5a83e6b90
Create Date: 2026-02-11 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd2a7b41c9f03'
down_revision: Union[str, Sequence[str], None] = 'c1f5a83e6b90'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1) credit_transactions.turn_id（表可能由 Go EnsureTables 创建，故用 IF EXISTS）
    op.execute("ALTER TABLE IF EXISTS credit_transactions ADD COLUMN IF NOT EXISTS turn_id VARCHAR(36)")
    op.execute("""
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables
             WHERE table_schema = 'public' AND table_name = 'credit_transactions') THEN
    IF NOT EXISTS (SELECT 1 FROM pg_indexes
                   WHERE schemaname = 'public' AND indexname = 'uniq_credit_tx_turn') THEN
      CREATE UNIQUE INDEX uniq_credit_tx_turn ON credit_transactions(turn_id);
    END IF;
  END IF;
END $$;
""")

    # 2) billing_records.turn_id：普通索引 -> 唯一索引（允许多 NULL）
    op.drop_index('ix_billing_records_turn_id', table_name='billing_records')
    op.create_index('uniq_billing_records_turn', 'billing_records', ['turn_id'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('uniq_billing_records_turn', table_name='billing_records')
    op.create_index('ix_billing_records_turn_id', 'billing_records', ['turn_id'])

    op.execute("DROP INDEX IF EXISTS uniq_credit_tx_turn")
    op.execute("ALTER TABLE IF EXISTS credit_transactions DROP COLUMN IF EXISTS turn_id")
