"""add_missing_tables_and_fix_settings_type

Revision ID: 78a15f2c38aa
Revises: 5d96fd6f7856
Create Date: 2026-08-27 00:24:16.301299

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '78a15f2c38aa'
down_revision: Union[str, Sequence[str], None] = '5d96fd6f7856'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 创建 ent_sms_config 表
    op.create_table('ent_sms_config',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('tenant_id', sa.String(length=36), nullable=False),
    sa.Column('provider', sa.String(length=32), nullable=True),
    sa.Column('sign_name', sa.String(length=128), nullable=True),
    sa.Column('template_id', sa.String(length=128), nullable=True),
    sa.Column('access_key_id', sa.String(length=128), nullable=True),
    sa.Column('secret_enc', sa.String(length=512), nullable=True),
    sa.Column('endpoint', sa.String(length=255), nullable=True),
    sa.Column('code_ttl_seconds', sa.Integer(), nullable=True),
    sa.Column('send_interval_seconds', sa.Integer(), nullable=True),
    sa.Column('daily_limit', sa.Integer(), nullable=True),
    sa.Column('login_enabled', sa.Boolean(), nullable=True),
    sa.Column('auto_register', sa.Boolean(), nullable=True),
    sa.Column('enabled', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tenant_id')
    )
    
    # 创建 media_assets 表
    op.create_table('media_assets',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('tenant_id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('type', sa.String(length=16), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('parent_id', sa.String(length=36), nullable=True),
    sa.Column('file_url', sa.Text(), nullable=True),
    sa.Column('file_path', sa.Text(), nullable=True),
    sa.Column('mime_type', sa.String(length=128), nullable=True),
    sa.Column('category', sa.String(length=64), nullable=True),
    sa.Column('tags', sa.JSON(), nullable=True),
    sa.Column('metadata', sa.JSON(), nullable=True),
    sa.Column('thumbnail', sa.Text(), nullable=True),
    sa.Column('size', sa.BigInteger(), nullable=True),
    sa.Column('status', sa.String(length=16), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_media_assets_tenant_user_parent', 'media_assets', ['tenant_id', 'user_id', 'parent_id'])
    op.create_index('idx_media_assets_tenant_user_type', 'media_assets', ['tenant_id', 'user_id', 'type'])
    
    # 修复 users.settings 字段类型：从 varchar 改为 jsonb
    op.alter_column('users', 'settings',
                    existing_type=sa.String(length=255),
                    type_=sa.JSON(),
                    existing_nullable=True,
                    postgresql_using='settings::jsonb')


def downgrade() -> None:
    """Downgrade schema."""
    # 恢复 users.settings 字段类型
    op.alter_column('users', 'settings',
                    existing_type=sa.JSON(),
                    type_=sa.String(length=255),
                    existing_nullable=True)
    
    # 删除索引
    op.drop_index('idx_media_assets_tenant_user_type', table_name='media_assets')
    op.drop_index('idx_media_assets_tenant_user_parent', table_name='media_assets')
    
    # 删除表
    op.drop_table('media_assets')
    op.drop_table('ent_sms_config')
