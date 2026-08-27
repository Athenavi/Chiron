# DBManager 使用指南

## 概述

`DBManager` 是统一的数据库管理器，集中处理所有数据库操作和 nil 检查，避免在各个文件中重复编写空指针检查代码。

## 核心优势

1. **统一管理**：所有数据库访问通过单一入口点
2. **自动 nil 检查**：内部自动处理连接池未初始化的情况
3. **错误处理一致**：返回统一的 `ErrDatabaseNotAvailable` 错误
4. **读写分离**：自动选择读副本或主库

## 基本用法

### 1. 使用全局实例（推荐）

```go
import "github.com/athenavi/chiron/internal/db"

// 查询操作
rows, err := db.GlobalDBManager.Query(ctx, "SELECT * FROM users WHERE id = $1", userID)
if err != nil {
    if errors.Is(err, db.ErrDatabaseNotAvailable) {
        ServiceUnavailable(w, "database not available")
        return
    }
    // 处理其他错误
}

// 单行查询
var name string
err := db.GlobalDBManager.QueryRow(ctx, "SELECT name FROM users WHERE id = $1", userID).Scan(&name)
if err != nil {
    // 处理错误
}

// 写操作
_, err := db.GlobalDBManager.Exec(ctx, "UPDATE users SET name = $1 WHERE id = $2", newName, userID)
if err != nil {
    // 处理错误
}
```

### 2. 创建新实例

```go
manager := db.NewDBManager()
pool, err := manager.GetPool()
if err != nil {
    // 处理错误
}
```

## API 参考

### 获取连接池

```go
// 获取主库连接池
pool, err := db.GlobalDBManager.GetPool()

// 获取读操作连接池（优先只读副本）
pool, err := db.GlobalDBManager.GetReadPool()
```

### 执行查询

```go
// 普通查询
rows, err := db.GlobalDBManager.Query(ctx, sql, args...)

// 单行查询
row := db.GlobalDBManager.QueryRow(ctx, sql, args...)
err := row.Scan(&field1, &field2)
```

### 执行写操作

```go
result, err := db.GlobalDBManager.Exec(ctx, sql, args...)
```

### 事务操作

```go
tx, err := db.GlobalDBManager.Begin(ctx)
if err != nil {
    // 处理错误
}
defer tx.Rollback(ctx)

// 执行事务操作
_, err = tx.Exec(ctx, sql, args...)
if err != nil {
    return err
}

return tx.Commit(ctx)
```

### 健康检查

```go
// 检查数据库是否可用
if !db.GlobalDBManager.IsAvailable() {
    ServiceUnavailable(w, "database not available")
    return
}

// Ping 测试连接
err := db.GlobalDBManager.Ping(ctx)
```

## 迁移指南

### 从旧代码迁移

#### 之前（容易出错）

```go
// ❌ 危险：可能 panic
rows, err := db.ReadPool().Query(ctx, sql, args...)
```

#### 之后（安全）

```go
// ✅ 安全：自动 nil 检查
rows, err := db.GlobalDBManager.Query(ctx, sql, args...)
if err != nil {
    if errors.Is(err, db.ErrDatabaseNotAvailable) {
        ServiceUnavailable(w, "database not available")
        return
    }
    // 处理其他错误
}
```

### 批量替换模式

查找并替换以下模式：

1. `db.Pool.Query(...)` → `db.GlobalDBManager.Query(...)`
2. `db.Pool.QueryRow(...)` → `db.GlobalDBManager.QueryRow(...)`
3. `db.Pool.Exec(...)` → `db.GlobalDBManager.Exec(...)`
4. `db.Pool.Begin(...)` → `db.GlobalDBManager.Begin(...)`
5. `db.ReadPool().Query(...)` → `db.GlobalDBManager.Query(...)`
6. `db.ReadPool().QueryRow(...)` → `db.GlobalDBManager.QueryRow(...)`

## 错误处理最佳实践

```go
rows, err := db.GlobalDBManager.Query(ctx, sql, args...)
if err != nil {
    // 区分数据库不可用和其他错误
    if errors.Is(err, db.ErrDatabaseNotAvailable) {
        // 返回 503 Service Unavailable
        ServiceUnavailable(w, "service temporarily unavailable")
        return
    }
    
    // 记录其他错误
    slog.Error("query failed", "error", err, "sql", sql)
    InternalError(w, "internal error")
    return
}
```

## 性能考虑

- `DBManager` 内部使用读写锁保护，并发安全
- 读操作自动路由到只读副本（如果配置了路由器）
- 写操作始终使用主库
- 无额外性能开销，只是简单的封装

## 注意事项

1. **不要混用**：同一函数内要么全部使用 `DBManager`，要么全部使用原始 `db.Pool`，避免混乱
2. **事务一致性**：在事务中应使用事务对象的方法，而不是 `DBManager`
3. **错误传播**：确保正确处理 `ErrDatabaseNotAvailable` 错误
4. **向后兼容**：旧的 `db.Pool` 和 `db.ReadPool()` 仍然可用，但建议逐步迁移

## 示例：完整 Handler

```go
func handleUsers(w http.ResponseWriter, r *http.Request) {
    ctx := r.Context()
    
    // 查询用户列表
    rows, err := db.GlobalDBManager.Query(ctx, 
        "SELECT id, name, email FROM users ORDER BY created_at DESC LIMIT 100")
    if err != nil {
        if errors.Is(err, db.ErrDatabaseNotAvailable) {
            ServiceUnavailable(w, "database not available")
            return
        }
        slog.Error("failed to query users", "error", err)
        InternalError(w, "internal error")
        return
    }
    defer rows.Close()
    
    var users []User
    for rows.Next() {
        var u User
        if err := rows.Scan(&u.ID, &u.Name, &u.Email); err != nil {
            slog.Error("failed to scan user", "error", err)
            continue
        }
        users = append(users, u)
    }
    
    OK(w, users)
}
```