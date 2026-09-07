"""add provider + encrypted_key to admin_api_keys

管理端 LLM provider 密钥（原明文 data/api_keys.json）改为加密存入
admin_api_keys 表：provider + encrypted_key 行承载，key_hash 存
sha256("provider:key") 用于唯一去重。AES-256-GCM 密钥由 APP_SECRET
派生（见 python-engine/app/gateway/smart_key_pool.py）。

Revision ID: 9f3c2a1e7d04
Revises: 433e78cd17b7
Create Date: 2026-09-07
"""
from alembic import op
import sqlalchemy as sa

revision = "9f3c2a1e7d04"
down_revision = "433e78cd17b7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "admin_api_keys",
        sa.Column("provider", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "admin_api_keys",
        sa.Column("encrypted_key", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("admin_api_keys", "encrypted_key")
    op.drop_column("admin_api_keys", "provider")
