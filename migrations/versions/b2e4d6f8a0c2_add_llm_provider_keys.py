"""add llm_provider_keys

管理端 LLM provider 密钥专用表(集中派):密文由 Go internal/settings
(AES-256-GCM, APP_SECRET 派生)加解密, 明文永不落库。
key_hash = sha256("provider:key") 用于唯一去重与 keyset key_id。
status: active / rate_limited / circuit_open(自动停用带冷却窗)。

Revision ID: b2e4d6f8a0c2
Revises: c1a0b2d3e4f5
Create Date: 2026-09-09
"""
from alembic import op
import sqlalchemy as sa

revision = "b2e4d6f8a0c2"
down_revision = "c1a0b2d3e4f5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "llm_provider_keys",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("encrypted_key", sa.Text(), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key_hash"),
    )
    op.create_index("ix_llm_provider_keys_provider", "llm_provider_keys", ["provider"])


def downgrade() -> None:
    op.drop_index("ix_llm_provider_keys_provider", table_name="llm_provider_keys")
    op.drop_table("llm_provider_keys")
