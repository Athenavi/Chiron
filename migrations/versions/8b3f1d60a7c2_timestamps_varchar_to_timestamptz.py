"""timestamps varchar -> timestamptz

把 configs/orm/V1/models.yaml 中声明为 `format: date-time` 的列，从 character varying
统一转为 timestamptz。

背景：models.yaml 用 `type: string, format: date-time`（时间语义，default: now()）
表达时间戳，但 scripts/generate_orm_models.py 缺少 `format: date-time -> datetime`
归一，模板于是落到 `String(255)` 分支；据此产出的 shared/models/*.py（生成于
2026-08-27）与 a0b3a964fb54_v3_initial_full.py 都按字符串建表，库中时间戳列因而是
character varying。生成器已在本次一并修复。

而 Go 侧 internal/model/model.go 用 time.Time，两边不兼容：

- 读：pgx 报 `cannot scan varchar (OID 1043) in text format into *time.Time`。
  session.Manager.GetSession 因此返回包装后的查询错误（非 ErrSessionNotFound），
  SSEHandler 落到 InternalError → GET /events 恒 500。
  ListSessions 逐行 slog.Warn 后 continue → 会话列表恒为空。
- 写：pgx 的 text codec 对实现 fmt.Stringer 的值调用 String()，CreateSession
  于是写入 `2026-09-09 23:40:27.7524833 +0800 CST m=+16.114328001`（含 monotonic
  读数）；而 manager.go:301 的 `updated_at = NOW()` 被隐式转成
  `2026-09-10 22:56:24.394948+08`。同一列出现两种不兼容表示。

实现要点：
1. 目标列取自 models.yaml 的 date-time 声明清单（显式，可审计），而非列名正则——
   正则既会漏掉 `last_health_check`，又会误伤声明为 string 的 `applied_at`。
2. 只处理当前仍是 character varying 的列，故本迁移幂等；`media_assets.created_at`
   等已是 naive timestamp 的列（时区语义是另一个问题）会被自动跳过。
3. USING 先清洗 Go time.Time.String() 的尾巴（` +0800 CST m=+16.114328001` -> ` +0800`）。

预检（chiron0907）：清单中所有 varchar 列逐列全表扫描，0 行无法按
`YYYY-MM-DD HH:MM:SS` 前缀解析，转换无数据损失。

Revision ID: 8b3f1d60a7c2
Revises: f7c2d05a1b8e
Create Date: 2026-02-11 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '8b3f1d60a7c2'
down_revision: Union[str, Sequence[str], None] = 'f7c2d05a1b8e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# models.yaml 中所有 `format: date-time` 的 (表, 列)。共 124 项。
_DATETIME_COLUMNS = """
    ('admin_api_call_logs', 'created_at'),
    ('admin_api_keys', 'created_at'),
    ('admin_api_keys', 'expires_at'),
    ('admin_api_keys', 'updated_at'),
    ('admin_cron_jobs', 'created_at'),
    ('admin_cron_jobs', 'last_run_at'),
    ('admin_cron_jobs', 'next_run_at'),
    ('admin_cron_jobs', 'updated_at'),
    ('admin_database_backups', 'completed_at'),
    ('admin_database_backups', 'started_at'),
    ('admin_db_configs', 'created_at'),
    ('admin_db_configs', 'last_health_check'),
    ('admin_db_configs', 'updated_at'),
    ('admin_domains', 'created_at'),
    ('admin_domains', 'ssl_expires_at'),
    ('admin_domains', 'updated_at'),
    ('admin_domains', 'verified_at'),
    ('admin_model_configs', 'created_at'),
    ('admin_model_configs', 'updated_at'),
    ('admin_redis_configs', 'created_at'),
    ('admin_redis_configs', 'last_health_check'),
    ('admin_redis_configs', 'updated_at'),
    ('admin_tenant_usage', 'created_at'),
    ('admin_tenants', 'created_at'),
    ('admin_tenants', 'expires_at'),
    ('admin_tenants', 'updated_at'),
    ('admin_workflow_executions', 'completed_at'),
    ('admin_workflow_executions', 'started_at'),
    ('admin_workflows', 'created_at'),
    ('admin_workflows', 'published_at'),
    ('admin_workflows', 'updated_at'),
    ('agent_registry', 'created_at'),
    ('agent_sessions', 'created_at'),
    ('agent_sessions', 'updated_at'),
    ('agents', 'created_at'),
    ('agents', 'updated_at'),
    ('api_keys', 'created_at'),
    ('api_keys', 'expires_at'),
    ('api_keys', 'last_used_at'),
    ('audit_logs', 'created_at'),
    ('billing_records', 'created_at'),
    ('conversation_shares', 'created_at'),
    ('conversation_shares', 'revoked_at'),
    ('credit_transactions', 'created_at'),
    ('cron_jobs', 'created_at'),
    ('cron_jobs', 'last_run_at'),
    ('cron_jobs', 'updated_at'),
    ('domains', 'created_at'),
    ('domains', 'updated_at'),
    ('ent_captcha_config', 'created_at'),
    ('ent_captcha_config', 'updated_at'),
    ('ent_catalog_installs', 'installed_at'),
    ('ent_catalog_items', 'created_at'),
    ('ent_catalog_items', 'updated_at'),
    ('ent_groups', 'created_at'),
    ('ent_model_policies', 'created_at'),
    ('ent_model_policies', 'updated_at'),
    ('ent_oidc_providers', 'created_at'),
    ('ent_oidc_providers', 'updated_at'),
    ('ent_quota_allocations', 'created_at'),
    ('ent_quota_pools', 'created_at'),
    ('ent_quota_pools', 'updated_at'),
    ('ent_roles', 'created_at'),
    ('ent_roles', 'updated_at'),
    ('ent_templates', 'created_at'),
    ('ent_templates', 'updated_at'),
    ('ent_tenant_policies', 'updated_at'),
    ('ent_user_identities', 'created_at'),
    ('enterprise_tasks', 'created_at'),
    ('enterprise_tasks', 'updated_at'),
    ('guest_storage', 'created_at'),
    ('kb_articles', 'created_at'),
    ('kb_articles', 'updated_at'),
    ('knowledge_bases', 'created_at'),
    ('knowledge_bases', 'updated_at'),
    ('knowledge_chunks', 'created_at'),
    ('knowledge_documents', 'created_at'),
    ('knowledge_documents', 'updated_at'),
    ('llm_models', 'created_at'),
    ('llm_models', 'updated_at'),
    ('marketing_campaigns', 'created_at'),
    ('marketing_campaigns', 'updated_at'),
    ('media_assets', 'created_at'),
    ('media_assets', 'updated_at'),
    ('meeting_notes', 'created_at'),
    ('memory_summaries', 'created_at'),
    ('memory_summaries', 'last_accessed_at'),
    ('messages', 'created_at'),
    ('okrs', 'created_at'),
    ('okrs', 'updated_at'),
    ('payments', 'created_at'),
    ('payments', 'expired_at'),
    ('payments', 'paid_at'),
    ('sessions', 'created_at'),
    ('sessions', 'updated_at'),
    ('stripe_payments', 'completed_at'),
    ('stripe_payments', 'created_at'),
    ('support_tickets', 'created_at'),
    ('support_tickets', 'updated_at'),
    ('system_settings', 'updated_at'),
    ('tasks', 'created_at'),
    ('tasks', 'updated_at'),
    ('tenants', 'created_at'),
    ('tool_calls', 'created_at'),
    ('turns', 'created_at'),
    ('turns', 'finished_at'),
    ('turns', 'started_at'),
    ('unified_messages', 'created_at'),
    ('unified_sessions', 'created_at'),
    ('unified_sessions', 'updated_at'),
    ('uploads', 'created_at'),
    ('uploads', 'updated_at'),
    ('user_memory_profile', 'confirmed_at'),
    ('user_memory_profile', 'created_at'),
    ('user_memory_profile', 'last_referenced_at'),
    ('user_memory_profile', 'updated_at'),
    ('users', 'created_at'),
    ('users', 'updated_at'),
    ('wiki_pages', 'created_at'),
    ('wiki_pages', 'updated_at'),
    ('workflow_graphs', 'created_at'),
    ('workflow_graphs', 'updated_at'),
    ('workflow_instances', 'created_at'),
    ('workflow_instances', 'updated_at')
"""

# 用 DO $$ + quote_ident 拼接而非 format()：psycopg2 会把 SQL 里的 `%` 当占位符。
_UPGRADE_SQL = """
DO $$
DECLARE r record;
BEGIN
  FOR r IN
    SELECT v.table_name, v.column_name
    FROM (VALUES
""" + _DATETIME_COLUMNS + """
    ) AS v(table_name, column_name)
    JOIN information_schema.columns c
      ON c.table_schema = 'public'
     AND c.table_name = v.table_name
     AND c.column_name = v.column_name
     AND c.data_type = 'character varying'
  LOOP
    EXECUTE 'ALTER TABLE public.' || quote_ident(r.table_name)
         || ' ALTER COLUMN ' || quote_ident(r.column_name)
         || ' TYPE timestamptz USING (regexp_replace(' || quote_ident(r.column_name)
         || ', ''\\s+[A-Za-z]{2,5}\\s+m=[+-][0-9.]+$'', ''''))::timestamptz';
  END LOOP;
END $$
"""

# 反向：timestamptz -> varchar(255)。同一清单口径，只处理当前为 timestamptz 的列。
_DOWNGRADE_SQL = """
DO $$
DECLARE r record;
BEGIN
  FOR r IN
    SELECT v.table_name, v.column_name, c.column_default
    FROM (VALUES
""" + _DATETIME_COLUMNS + """
    ) AS v(table_name, column_name)
    JOIN information_schema.columns c
      ON c.table_schema = 'public'
     AND c.table_name = v.table_name
     AND c.column_name = v.column_name
     AND c.data_type = 'timestamp with time zone'
  LOOP
    IF r.column_default IS NOT NULL THEN
      EXECUTE 'ALTER TABLE public.' || quote_ident(r.table_name)
           || ' ALTER COLUMN ' || quote_ident(r.column_name) || ' DROP DEFAULT';
    END IF;

    EXECUTE 'ALTER TABLE public.' || quote_ident(r.table_name)
         || ' ALTER COLUMN ' || quote_ident(r.column_name)
         || ' TYPE varchar(255) USING to_char(' || quote_ident(r.column_name)
         || ', ''YYYY-MM-DD HH24:MI:SS.US+TZH:TZM'')';

    IF r.column_default IS NOT NULL THEN
      EXECUTE 'ALTER TABLE public.' || quote_ident(r.table_name)
           || ' ALTER COLUMN ' || quote_ident(r.column_name) || ' SET DEFAULT now()::varchar';
    END IF;
  END LOOP;
END $$
"""


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(_UPGRADE_SQL)


def downgrade() -> None:
    """Downgrade schema.

    反向转换会丢失时区名等附加信息（统一为 to_char 的输出），但保留 NOT NULL 语义。
    """
    op.execute(_DOWNGRADE_SQL)
