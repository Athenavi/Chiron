-- ============================================
-- PostgreSQL Row Level Security (RLS) 启用脚本
-- ============================================
-- 警告：此脚本会显著影响性能，建议在充分测试后在生产环境启用
-- 使用前请确保所有查询都设置了 app.current_tenant_id
-- 
-- 使用方法：
-- 1. 备份数据库
-- 2. 在测试环境充分测试
-- 3. 确认所有应用层代码都已设置 tenant context
-- 4. 在生产环境低峰期执行
-- 5. 密切监控性能指标

-- 1. 启用扩展（如果需要）
-- CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 2. 为每个需要租户隔离的表启用RLS
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE agents ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_bases ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE media_assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE uploads ENABLE ROW LEVEL SECURITY;
ALTER TABLE workflows ENABLE ROW LEVEL SECURITY;
ALTER TABLE workflow_instances ENABLE ROW LEVEL SECURITY;
ALTER TABLE cron_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE billing_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE credit_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;

-- 3. 创建租户隔离策略
-- 注意：owner角色可以访问所有数据（用于系统管理）

CREATE POLICY tenant_isolation_users ON users
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid 
           OR current_setting('app.current_role') = 'owner');

CREATE POLICY tenant_isolation_sessions ON sessions
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid
           OR current_setting('app.current_role') = 'owner');

CREATE POLICY tenant_isolation_agents ON agents
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid
           OR visibility = 'public'
           OR current_setting('app.current_role') = 'owner');

CREATE POLICY tenant_isolation_agent_sessions ON agent_sessions
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid
           OR current_setting('app.current_role') = 'owner');

CREATE POLICY tenant_isolation_conversations ON conversations
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid
           OR current_setting('app.current_role') = 'owner');

CREATE POLICY tenant_isolation_messages ON messages
    USING (EXISTS (
        SELECT 1 FROM conversations c 
        WHERE c.id = messages.conversation_id 
        AND c.tenant_id = current_setting('app.current_tenant_id')::uuid
    ) OR current_setting('app.current_role') = 'owner');

CREATE POLICY tenant_isolation_knowledge_bases ON knowledge_bases
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid
           OR current_setting('app.current_role') = 'owner');

CREATE POLICY tenant_isolation_knowledge_documents ON knowledge_documents
    USING (EXISTS (
        SELECT 1 FROM knowledge_bases kb 
        WHERE kb.id = knowledge_documents.knowledge_base_id 
        AND kb.tenant_id = current_setting('app.current_tenant_id')::uuid
    ) OR current_setting('app.current_role') = 'owner');

CREATE POLICY tenant_isolation_knowledge_chunks ON knowledge_chunks
    USING (EXISTS (
        SELECT 1 FROM knowledge_documents kd
        JOIN knowledge_bases kb ON kb.id = kd.knowledge_base_id
        WHERE kd.id = knowledge_chunks.document_id 
        AND kb.tenant_id = current_setting('app.current_tenant_id')::uuid
    ) OR current_setting('app.current_role') = 'owner');

CREATE POLICY tenant_isolation_media_assets ON media_assets
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid
           OR current_setting('app.current_role') = 'owner');

CREATE POLICY tenant_isolation_uploads ON uploads
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid
           OR current_setting('app.current_role') = 'owner');

CREATE POLICY tenant_isolation_workflows ON workflows
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid
           OR current_setting('app.current_role') = 'owner');

CREATE POLICY tenant_isolation_workflow_instances ON workflow_instances
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid
           OR current_setting('app.current_role') = 'owner');

CREATE POLICY tenant_isolation_cron_jobs ON cron_jobs
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid
           OR current_setting('app.current_role') = 'owner');

CREATE POLICY tenant_isolation_audit_logs ON audit_logs
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid
           OR current_setting('app.current_role') = 'owner');

CREATE POLICY tenant_isolation_billing ON billing_records
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid
           OR current_setting('app.current_role') = 'owner');

CREATE POLICY tenant_isolation_credits ON credit_transactions
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid
           OR current_setting('app.current_role') = 'owner');

CREATE POLICY tenant_isolation_payments ON payments
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid
           OR current_setting('app.current_role') = 'owner');

-- 4. 创建BYPASS RLS策略（用于系统维护任务）
-- 注意：需要创建一个专门的维护角色
CREATE ROLE chiron_maintenance;

CREATE POLICY bypass_rls_for_maintenance ON users
    FOR ALL
    TO chiron_maintenance
    USING (true);

-- 对其他关键表重复上述BYPASS策略...
-- （根据实际需求添加更多表的bypass策略）

-- 5. 验证RLS状态
SELECT schemaname, tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public' 
ORDER BY tablename;

-- 6. 性能测试查询
-- 在执行此脚本前后，运行以下查询对比性能：
-- EXPLAIN ANALYZE SELECT * FROM users WHERE tenant_id = 'xxx';
-- EXPLAIN ANALYZE SELECT * FROM sessions WHERE tenant_id = 'xxx';

-- 7. 回滚脚本（如需撤销RLS）
/*
DO $$
DECLARE
    tbl TEXT;
BEGIN
    FOR tbl IN 
        SELECT tablename FROM pg_tables 
        WHERE schemaname = 'public' 
        AND rowsecurity = true
    LOOP
        EXECUTE format('DROP POLICY IF EXISTS tenant_isolation_%I ON %I', tbl, tbl);
        EXECUTE format('DROP POLICY IF EXISTS bypass_rls_for_maintenance ON %I', tbl);
        EXECUTE format('ALTER TABLE %I DISABLE ROW LEVEL SECURITY', tbl);
    END LOOP;
END $$;
*/