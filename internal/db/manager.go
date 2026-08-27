package db

import (
	"context"
	"errors"
	"fmt"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgconn"
	"github.com/jackc/pgx/v5/pgxpool"
)

// ErrDatabaseNotAvailable 数据库未初始化错误
var ErrDatabaseNotAvailable = errors.New("database not available")

// DBManager 统一数据库管理器，集中处理所有数据库操作和 nil 检查
type DBManager struct{}

// NewDBManager 创建数据库管理器实例
func NewDBManager() *DBManager {
	return &DBManager{}
}

// GetPool 获取主数据库连接池，如果未初始化则返回错误
func (m *DBManager) GetPool() (*pgxpool.Pool, error) {
	PoolMu.RLock()
	p := Pool
	PoolMu.RUnlock()
	if p == nil {
		return nil, ErrDatabaseNotAvailable
	}
	return p, nil
}

// GetReadPool 获取读操作连接池（优先使用只读副本），如果未初始化则返回错误
func (m *DBManager) GetReadPool() (*pgxpool.Pool, error) {
	PoolMu.RLock()
	p := Pool
	PoolMu.RUnlock()
	if Router != nil {
		pool := Router.ReadPreferred()
		if pool == nil {
			return nil, ErrDatabaseNotAvailable
		}
		return pool, nil
	}
	if p == nil {
		return nil, ErrDatabaseNotAvailable
	}
	return p, nil
}

// Query 执行查询并返回结果集
func (m *DBManager) Query(ctx context.Context, sql string, args ...interface{}) (pgx.Rows, error) {
	pool, err := m.GetReadPool()
	if err != nil {
		return nil, fmt.Errorf("db manager: %w", err)
	}
	return pool.Query(ctx, sql, args...)
}

// QueryRow 执行查询并返回单行结果
func (m *DBManager) QueryRow(ctx context.Context, sql string, args ...interface{}) pgx.Row {
	pool, err := m.GetReadPool()
	if err != nil {
		return errorRow{err: err}
	}
	return pool.QueryRow(ctx, sql, args...)
}

// Exec 执行写操作（INSERT/UPDATE/DELETE）
func (m *DBManager) Exec(ctx context.Context, sql string, args ...interface{}) (pgconn.CommandTag, error) {
	pool, err := m.GetPool()
	if err != nil {
		return pgconn.CommandTag{}, fmt.Errorf("db manager: %w", err)
	}
	return pool.Exec(ctx, sql, args...)
}

// Begin 开始事务
func (m *DBManager) Begin(ctx context.Context) (pgx.Tx, error) {
	pool, err := m.GetPool()
	if err != nil {
		return nil, fmt.Errorf("db manager: %w", err)
	}
	return pool.Begin(ctx)
}

// Ping 检查数据库连接状态
func (m *DBManager) Ping(ctx context.Context) error {
	pool, err := m.GetPool()
	if err != nil {
		return err
	}
	return pool.Ping(ctx)
}

// IsAvailable 检查数据库是否可用
func (m *DBManager) IsAvailable() bool {
	PoolMu.RLock()
	p := Pool
	PoolMu.RUnlock()
	return p != nil
}

// errorRow 实现 pgx.Row 接口，用于返回错误
type errorRow struct {
	err error
}

func (r errorRow) Scan(dest ...interface{}) error {
	return r.err
}

// GlobalDBManager 全局数据库管理器实例
var GlobalDBManager = NewDBManager()