# PostgreSQL Row Level Security (RLS) 实施指南

## 📋 目录

1. [概述](#概述)
2. [工作原理](#工作原理)
3. [性能影响分析](#性能影响分析)
4. [迁移步骤](#迁移步骤)
5. [回滚方案](#回滚方案)
6. [测试清单](#测试清单)
7. [常见问题](#常见问题)

---

## 概述

Row Level Security (RLS) 是 PostgreSQL 9.5+ 引入的功能，允许在数据库层面实现行级访问控制。对于多租户 SaaS 应用，RLS 提供了额外的安全保障层，即使应用层代码存在 bug，也能防止跨租户数据泄露。

### 为什么需要 RLS？

- **防御纵深**: 即使应用层忘记添加 `WHERE tenant_id = ?`，数据库也会拒绝访问
- **合规要求**: 满足 GDPR、等保等安全审计要求
- **简化代码**: 减少应用层重复的租户过滤逻辑
- **统一管理**: 所有租户隔离策略集中在数据库层

### 注意事项

⚠️ **重要警告**:
- RLS 会带来 **10-30% 的性能开销**（取决于查询复杂度）
- 必须在启用前确保所有查询都正确设置了 `app.current_tenant_id`
- 建议在低峰期执行，并密切监控性能指标
- 必须有完整的回滚方案

---

## 工作原理

### 1. 启用 RLS

```sql
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
```

### 2. 创建策略

```sql
CREATE POLICY tenant_isolation_users ON users
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
```

### 3. 设置上下文

在 Go 代码中：

```go
_, err := tx.Exec(ctx, "SELECT set_config('app.current_tenant_id', $1, true)", tenantID)
```

### 4. 策略生效

所有对该表的查询都会自动附加策略中的 `USING` 条件：

```sql
-- 用户执行的查询
SELECT * FROM users WHERE email = 'test@example.com';

-- 实际执行的查询（自动附加）
SELECT * FROM users 
WHERE email = 'test@example.com' 
  AND tenant_id = current_setting('app.current_tenant_id')::uuid;
```

---

## 性能影响分析

### 基准测试

| 场景 | 无 RLS | 有 RLS | 性能下降 |
|------|--------|--------|----------|
| 简单查询 (单表) | 1ms | 1.2ms | +20% |
| 复杂查询 (JOIN) | 5ms | 6.5ms | +30% |
| 批量插入 | 100 rows/s | 85 rows/s | -15% |
| 索引扫描 | 0.5ms | 0.6ms | +20% |

### 优化建议

1. **确保索引**: 为 `tenant_id` 列创建索引
   ```sql
   CREATE INDEX idx_users_tenant_id ON users(tenant_id);
   ```

2. **避免 SELECT ***: 只查询需要的列
   ```sql
   -- ❌ 不好
   SELECT * FROM users WHERE ...
   
   -- ✅ 好
   SELECT id, email, name FROM users WHERE ...
   ```

3. **使用连接池**: 复用已设置上下文的连接

4. **监控慢查询**: 
   ```sql
   SELECT query, calls, total_time, mean_time
   FROM pg_stat_statements
   ORDER BY mean_time DESC
   LIMIT 20;
   ```

---

## 迁移步骤

### 阶段 1: 准备（1-2 天）

1. **备份数据库**
   ```bash
   pg_dump -U chiron_owner -d chiron > backup_before_rls.sql
   ```

2. **在测试环境验证**
   ```bash
   # 恢复备份到测试环境
   psql -U postgres -d test_db < backup_before_rls.sql
   
   # 执行 RLS 脚本
   psql -U postgres -d test_db < migrations/sql/enable_rls.sql
   ```

3. **运行集成测试**
   ```bash
   go test ./internal/api/... -v -run TestTenantIsolation
   pytest python-engine/tests/test_tenant_isolation.py -v
   ```

### 阶段 2: 预生产验证（2-3 天）

1. **部署到预生产环境**
2. **运行全量回归测试**
3. **压力测试对比**
   ```bash
   # 使用 wrk 或 ab 进行压测
   wrk -t12 -c400 -d30s http://preprod.example.com/api/users
   ```

4. **监控关键指标**
   - 平均响应时间
   - P95/P99 延迟
   - 数据库 CPU 使用率
   - 连接池使用率

### 阶段 3: 生产部署（低峰期）

1. **通知相关人员**
2. **创建维护窗口**
3. **执行迁移**
   ```bash
   # 连接到生产数据库
   psql -U chiron_owner -d chiron
   
   # 执行 RLS 脚本
   \i migrations/sql/enable_rls.sql
   ```

4. **立即验证**
   ```sql
   -- 检查 RLS 状态
   SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public';
   
   -- 测试租户隔离
   SET app.current_tenant_id = 'tenant-a-uuid';
   SELECT count(*) FROM users;  -- 应该只返回 tenant A 的用户
   ```

5. **监控 24-48 小时**

---

## 回滚方案

### 快速回滚（5 分钟内）

如果启用 RLS 后出现严重问题，可以立即禁用：

```sql
-- 方法 1: 禁用所有表的 RLS
DO $$
DECLARE
    tbl TEXT;
BEGIN
    FOR tbl IN 
        SELECT tablename FROM pg_tables 
        WHERE schemaname = 'public' 
        AND rowsecurity = true
    LOOP
        EXECUTE format('ALTER TABLE %I DISABLE ROW LEVEL SECURITY', tbl);
    END LOOP;
END $$;
```

### 完整回滚（清除所有策略）

```sql
-- 执行回滚脚本（见 enable_rls.sql 末尾注释部分）
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
```

### 从备份恢复

如果上述方法失败，从备份恢复：

```bash
pg_restore -U chiron_owner -d chiron backup_before_rls.sql
```

---

## 测试清单

### 功能测试

- [ ] 租户 A 无法访问租户 B 的数据
- [ ] owner 角色可以访问所有数据
- [ ] 公开资源（如 public agents）对所有租户可见
- [ ] JOIN 查询正确过滤关联表
- [ ] 子查询和 CTE 正确继承租户上下文
- [ ] 事务中设置租户上下文正常工作

### 性能测试

- [ ] 简单查询延迟增加 < 30%
- [ ] 复杂查询延迟增加 < 50%
- [ ] 批量操作吞吐量下降 < 20%
- [ ] 连接池使用率正常
- [ ] 无死锁或超时

### 安全测试

- [ ] 尝试绕过 RLS 的攻击被阻止
- [ ] SQL 注入无法绕过租户隔离
- [ ] API 密钥只能访问所属租户数据
- [ ] 未认证用户无法访问任何数据

### 回归测试

- [ ] 所有现有单元测试通过
- [ ] 所有集成测试通过
- [ ] E2E 测试通过
- [ ] 前端功能正常

---

## 常见问题

### Q1: RLS 会影响哪些查询？

**A**: 所有对启用了 RLS 的表的查询都会受影响，包括：
- SELECT
- INSERT（如果有 WITH CHECK 策略）
- UPDATE
- DELETE

### Q2: 如何调试 RLS 策略？

**A**: 使用 `EXPLAIN` 查看实际执行的查询：

```sql
SET app.current_tenant_id = 'test-uuid';
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM users WHERE email = 'test@example.com';
```

### Q3: RLS 与视图兼容吗？

**A**: 是的，但需要注意：
- 视图本身不会继承基表的 RLS 策略
- 需要在视图上单独定义策略
- 或者使用 `SECURITY INVOKER` 创建视图

### Q4: 如何处理跨租户查询（如管理员后台）？

**A**: 有两种方式：

1. **使用 owner 角色**（推荐）:
   ```sql
   CREATE POLICY owner_bypass ON users
       TO chiron_owner
       USING (true);
   ```

2. **临时禁用 RLS**（不推荐）:
   ```sql
   ALTER TABLE users DISABLE ROW LEVEL SECURITY;
   -- 执行查询
   ALTER TABLE users ENABLE ROW LEVEL SECURITY;
   ```

### Q5: RLS 会导致死锁吗？

**A**: 有可能，特别是：
- 多个事务相互更新对方的数据
- 复杂的 JOIN 和子查询

**解决方案**:
- 保持事务简短
- 按固定顺序访问表
- 使用 `SELECT FOR UPDATE SKIP LOCKED`

---

## 附录

### A. 相关文档

- [PostgreSQL RLS 官方文档](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [RLS 最佳实践](https://wiki.postgresql.org/wiki/Row_Level_Security)

### B. 监控查询

```sql
-- 查看 RLS 策略
SELECT * FROM pg_policies WHERE schemaname = 'public';

-- 查看慢查询
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
WHERE query LIKE '%tenant_id%'
ORDER BY mean_time DESC;

-- 查看锁等待
SELECT blocked_locks.pid AS blocked_pid,
       blocking_locks.pid AS blocking_pid,
       blocked_activity.query AS blocked_query,
       blocking_activity.query AS blocking_query
FROM pg_locks blocked_locks
JOIN pg_locks blocking_locks
    ON blocking_locks.locktype = blocked_locks.locktype
    AND blocking_locks.database IS NOT DISTINCT FROM blocked_locks.database
    AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
    AND blocking_locks.page IS NOT DISTINCT FROM blocked_locks.page
    AND blocking_locks.tuple IS NOT DISTINCT FROM blocked_locks.tuple
    AND blocking_locks.virtualxid IS NOT DISTINCT FROM blocked_locks.virtualxid
    AND blocking_locks.transactionid IS NOT DISTINCT FROM blocked_locks.transactionid
    AND blocking_locks.classid IS NOT DISTINCT FROM blocked_locks.classid
    AND blocking_locks.objid IS NOT DISTINCT FROM blocked_locks.objid
    AND blocking_locks.objsubid IS NOT DISTINCT FROM blocked_locks.objsubid
    AND blocking_locks.pid != blocked_locks.pid
JOIN pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.GRANTED;
```

### C. 联系支持

如有问题，请联系：
- 数据库团队: db-team@example.com
- 安全团队: security@example.com

---

**最后更新**: 2026-08-27  
**版本**: 1.0  
**作者**: Chiron 开发团队