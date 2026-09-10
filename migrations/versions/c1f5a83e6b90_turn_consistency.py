"""turn consistency

Turn 一致性（000.md 第 14 条）：引入 turns 状态机表，并给 messages / tool_calls /
billing_records 加 turn_id，使同一回合的消息、工具调用与计费可归属到同一 turn，
支持幂等写入与"失败不再静默"的状态收敛。

背景：此前用户消息、tool_call、assistant 消息、计费分别异步落库，错误只记日志，
PG 抖动或重试会出现"模型已输出但历史缺失"、重复计费等不一致（000.md 第 14 条）。

模型来源：configs/orm/V1/models.yaml（Turn 模型 + 三表 turn_id 属性），
ORM 文件由 scripts/generate_orm_models.py 生成；本迁移与之一致。

Revision ID: c1f5a83e6b90
Revises: b7c4e91d2a68
Create Date: 2026-02-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1f5a83e6b90'
down_revision: Union[str, Sequence[str], None] = 'b7c4e91d2a68'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'turns',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('session_id', sa.String(length=36), nullable=True),
        sa.Column('user_id', sa.String(length=36), nullable=True),
        sa.Column('status', sa.String(length=16), nullable=True, server_default='created'),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('input_tokens', sa.BigInteger(), nullable=True, server_default='0'),
        sa.Column('output_tokens', sa.BigInteger(), nullable=True, server_default='0'),
        sa.Column('started_at', sa.String(length=255), nullable=True),
        sa.Column('finished_at', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_turns_session_id', 'turns', ['session_id'])
    op.create_index('ix_turns_status', 'turns', ['status'])

    op.add_column('messages', sa.Column('turn_id', sa.String(length=36), nullable=True))
    op.create_index('ix_messages_turn_id', 'messages', ['turn_id'])

    op.add_column('tool_calls', sa.Column('turn_id', sa.String(length=36), nullable=True))
    op.create_index('ix_tool_calls_turn_id', 'tool_calls', ['turn_id'])

    op.add_column('billing_records', sa.Column('turn_id', sa.String(length=36), nullable=True))
    op.create_index('ix_billing_records_turn_id', 'billing_records', ['turn_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_billing_records_turn_id', table_name='billing_records')
    op.drop_column('billing_records', 'turn_id')

    op.drop_index('ix_tool_calls_turn_id', table_name='tool_calls')
    op.drop_column('tool_calls', 'turn_id')

    op.drop_index('ix_messages_turn_id', table_name='messages')
    op.drop_column('messages', 'turn_id')

    op.drop_index('ix_turns_status', table_name='turns')
    op.drop_index('ix_turns_session_id', table_name='turns')
    op.drop_table('turns')
