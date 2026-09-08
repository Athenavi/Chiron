package billing

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log/slog"
	"time"

	"github.com/athenavi/chiron/internal/db"
	"github.com/jackc/pgx/v5"
)

// PGStore implements Store using the chiron PostgreSQL database.
// It uses the existing users table for balance and adds a new billing table.

type PGStore struct{}

func NewPGStore() *PGStore {
	return &PGStore{}
}

// EnsureTables creates the billing tables if they don't exist.
func (s *PGStore) EnsureTables(ctx context.Context) error {
	if db.Pool == nil {
		return nil // no database available, skip table initialization
	}

	// Add balance column to users table if not exists
	_, err := db.GlobalDBManager.Exec(ctx,
		`ALTER TABLE users ADD COLUMN IF NOT EXISTS credits INTEGER NOT NULL DEFAULT 1000`)
	if err != nil {
		return fmt.Errorf("add credits column: %w", err)
	}

	// Create credit_transactions table
	_, err = db.GlobalDBManager.Exec(ctx,
		`CREATE TABLE IF NOT EXISTS credit_transactions (
			id VARCHAR(32) PRIMARY KEY,
			user_id VARCHAR(32) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
			amount INTEGER NOT NULL,
			balance INTEGER NOT NULL,
			reason VARCHAR(64) NOT NULL,
			created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
		)`)
	if err != nil {
		return fmt.Errorf("create credit_transactions: %w", err)
	}

	// Create payments table（支付宝/微信/PayPal 通用充值订单）
	_, err = db.GlobalDBManager.Exec(ctx,
		`CREATE TABLE IF NOT EXISTS payments (
			id VARCHAR(64) PRIMARY KEY,
			user_id VARCHAR(32) NOT NULL,
			channel VARCHAR(16) NOT NULL,
			credits INTEGER NOT NULL,
			amount_cents BIGINT NOT NULL DEFAULT 0,
			currency VARCHAR(8) NOT NULL DEFAULT 'CNY',
			status VARCHAR(16) NOT NULL DEFAULT 'pending',
			qr_code TEXT,
			provider_order_id VARCHAR(64) NOT NULL DEFAULT '',
			trade_no VARCHAR(64) NOT NULL DEFAULT '',
			created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
			paid_at TIMESTAMPTZ,
			expired_at TIMESTAMPTZ
		)`)
	if err != nil {
		return fmt.Errorf("create payments: %w", err)
	}
	_, err = db.GlobalDBManager.Exec(ctx,
		`CREATE INDEX IF NOT EXISTS idx_payments_user ON payments(user_id, created_at DESC)`)
	if err != nil {
		return fmt.Errorf("create payments user index: %w", err)
	}
	_, err = db.GlobalDBManager.Exec(ctx,
		`CREATE INDEX IF NOT EXISTS idx_payments_provider ON payments(provider_order_id) WHERE provider_order_id <> ''`)
	if err != nil {
		return fmt.Errorf("create payments provider index: %w", err)
	}

	// Index for fast history lookups
	_, err = db.GlobalDBManager.Exec(ctx,
		`CREATE INDEX IF NOT EXISTS idx_credit_tx_user ON credit_transactions(user_id, created_at DESC)`)
	if err != nil {
		return fmt.Errorf("create index: %w", err)
	}

	return nil
}

func (s *PGStore) GetBalance(ctx context.Context, userID string) (int, error) {
	var balance int
	err := db.GlobalDBManager.QueryRow(ctx,
		`SELECT COALESCE(credits, 0) FROM users WHERE id = $1`, userID).Scan(&balance)
	if err != nil {
		return 0, fmt.Errorf("get user credits: %w", err)
	}
	return balance, nil
}

func (s *PGStore) SetBalance(ctx context.Context, userID string, balance int) error {
	_, err := db.GlobalDBManager.Exec(ctx,
		`UPDATE users SET credits = $1 WHERE id = $2`, balance, userID)
	return err
}

func (s *PGStore) GetHistory(ctx context.Context, userID string, limit int) ([]CreditChange, error) {
	if limit <= 0 {
		limit = 50
	}

	rows, err := db.GlobalDBManager.Query(ctx,
		`SELECT id, user_id, amount, balance, reason, created_at
		 FROM credit_transactions WHERE user_id = $1 AND reason <> 'free_chat'
		 ORDER BY created_at DESC LIMIT $2`, userID, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var result []CreditChange
	for rows.Next() {
		var tx CreditChange
		if err := rows.Scan(&tx.ID, &tx.UserID, &tx.Amount, &tx.Balance, &tx.Reason, &tx.CreatedAt); err != nil {
			slog.Warn("scan transaction row skipped", "error", err)
			continue
		}
		result = append(result, tx)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate transactions: %w", err)
	}
	return result, nil
}

// DailyFreeCount returns the number of free conversations used today (UTC).
func (s *PGStore) DailyFreeCount(ctx context.Context, userID string) (int, error) {
	var count int
	todayUTC := time.Now().UTC().Truncate(24 * time.Hour)
	err := db.GlobalDBManager.QueryRow(ctx,
		`SELECT COUNT(*) FROM credit_transactions
		 WHERE user_id = $1 AND reason = 'free_chat' AND created_at >= $2`, userID, todayUTC).Scan(&count)
	if err != nil {
		return 0, err
	}
	return count, nil
}

// MarkFreeUsage records a free conversation usage for today.
func (s *PGStore) MarkFreeUsage(ctx context.Context, userID string) error {
	tx := &CreditChange{
		ID:        fmt.Sprintf("free_%d", time.Now().UnixNano()),
		UserID:    userID,
		Amount:    0,
		Balance:   0,
		Reason:    "free_chat",
		CreatedAt: time.Now(),
	}
	_, err := db.GlobalDBManager.Exec(ctx,
		`INSERT INTO credit_transactions (id, user_id, amount, balance, reason, created_at)
		 VALUES ($1, $2, $3, $4, $5, $6)`,
		tx.ID, tx.UserID, tx.Amount, tx.Balance, tx.Reason, tx.CreatedAt)
	return err
}

// RecordBillingRecord 写入一条企业成本中心记录（billing_records）。
// tenant_id 取自 users；group_id 取用户主群组（ent_group_members 首条，无则 NULL）。
// 单语句原子完成；用户不存在返回错误。调用方为扣费成功后的网关（submit 链路）。
func (s *PGStore) RecordBillingRecord(ctx context.Context, userID, sessionID string, inputTokens, outputTokens, costCents int) error {
	var sid *string
	if sessionID != "" {
		sid = &sessionID
	}
	tag, err := db.GlobalDBManager.Exec(ctx,
		`INSERT INTO billing_records (tenant_id, user_id, session_id, input_tokens, output_tokens, cost_cents, group_id)
		 SELECT u.tenant_id, u.id, $2, $3, $4, $5,
		        (SELECT g.group_id FROM ent_group_members g
		          WHERE g.user_id = u.id ORDER BY g.group_id LIMIT 1)
		 FROM users u WHERE u.id = $1`,
		userID, sid, inputTokens, outputTokens, costCents)
	if err != nil {
		return fmt.Errorf("insert billing record: %w", err)
	}
	if tag.RowsAffected() == 0 {
		return fmt.Errorf("billing record: user %s not found", userID)
	}
	return nil
}

// applyCreditTx 在同一事务内完成余额变更 + 流水落库：
// 余额以 PG 原子语句为唯一事实源，流水与余额同生共死，杜绝"已扣/已加未记流水"窗口。
// guardMin>0：仅当余额 >= guardMin 才允许（扣减防负）；否则无条件加减（充值/退款）。
func (s *PGStore) applyCreditTx(ctx context.Context, userID string, delta int, guardMin int, reason string) (int, error) {
	var newBalance int
	txID := fmt.Sprintf("tx_%d", time.Now().UnixNano())
	err := db.GlobalDBManager.WithTransaction(ctx, func(tx pgx.Tx) error {
		var q string
		args := []interface{}{delta, userID}
		if guardMin > 0 {
			q = `UPDATE users SET credits = credits + $1 WHERE id = $2 AND credits >= $3 RETURNING credits`
			args = append(args, guardMin)
		} else {
			q = `UPDATE users SET credits = credits + $1 WHERE id = $2 RETURNING credits`
		}
		if err := tx.QueryRow(ctx, q, args...).Scan(&newBalance); err != nil {
			return fmt.Errorf("apply credit balance: %w", err)
		}
		_, err := tx.Exec(ctx,
			`INSERT INTO credit_transactions (id, user_id, amount, balance, reason, created_at)
			 VALUES ($1, $2, $3, $4, $5, NOW())`,
			txID, userID, delta, newBalance, reason)
		if err != nil {
			return fmt.Errorf("insert credit transaction: %w", err)
		}
		return nil
	})
	if err != nil {
		return 0, err
	}
	return newBalance, nil
}

// AtomicDeductBalance 在同一事务内扣减余额并写入流水（reason）。
// 余额不足/用户不存在返回错误。多副本部署下不超扣、不重复扣费、流水不缺失。
func (s *PGStore) AtomicDeductBalance(ctx context.Context, userID string, amount int, reason string) (int, error) {
	if amount <= 0 {
		return 0, fmt.Errorf("invalid deduction amount: %d", amount)
	}
	b, err := s.applyCreditTx(ctx, userID, -amount, amount, reason)
	if err != nil {
		return 0, fmt.Errorf("atomic deduct failed (insufficient credits or user not found): %w", err)
	}
	return b, nil
}

// AtomicAddBalance 在同一事务内增加余额并写入流水（reason）。
// Returns the new balance, or an error if user not found.
func (s *PGStore) AtomicAddBalance(ctx context.Context, userID string, amount int, reason string) (int, error) {
	if amount <= 0 {
		return 0, fmt.Errorf("invalid add amount: %d", amount)
	}
	return s.applyCreditTx(ctx, userID, amount, 0, reason)
}

// JSON serialization helpers for API responses
type BalanceResponse struct {
	UserID  string `json:"user_id"`
	Balance int    `json:"balance"`
}

func FormatBalance(userID string, balance int) string {
	data, _ := json.Marshal(BalanceResponse{UserID: userID, Balance: balance})
	return string(data)
}

// ── PaymentStore ──────────────────────────────────────────────────────────

const _paymentColumns = `id, user_id, channel, credits, amount_cents, currency, status,
	COALESCE(qr_code, ''), provider_order_id, trade_no, created_at, paid_at, expired_at`

func scanPayment(row interface{ Scan(...any) error }) (*Payment, error) {
	var p Payment
	var qr string
	var paidAt, expiredAt *time.Time
	err := row.Scan(&p.ID, &p.UserID, &p.Channel, &p.Credits, &p.AmountCents, &p.Currency,
		&p.Status, &qr, &p.ProviderOrderID, &p.TradeNo, &p.CreatedAt, &paidAt, &expiredAt)
	if err != nil {
		return nil, err
	}
	p.QRCode = qr
	p.PaidAt = paidAt
	p.ExpiredAt = expiredAt
	return &p, nil
}

func (s *PGStore) CreatePayment(ctx context.Context, p *Payment) error {
	_, err := db.GlobalDBManager.Exec(ctx,
		`INSERT INTO payments (id, user_id, channel, credits, amount_cents, currency, status,
			qr_code, provider_order_id, trade_no, created_at, paid_at, expired_at)
		 VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)`,
		p.ID, p.UserID, p.Channel, p.Credits, p.AmountCents, p.Currency, p.Status,
		p.QRCode, p.ProviderOrderID, p.TradeNo, p.CreatedAt, p.PaidAt, p.ExpiredAt)
	return err
}

func (s *PGStore) GetPayment(ctx context.Context, id string) (*Payment, error) {
	row := db.GlobalDBManager.QueryRow(ctx,
		`SELECT `+_paymentColumns+` FROM payments WHERE id = $1`, id)
	return scanPayment(row)
}

func (s *PGStore) GetPaymentByProviderOrderID(ctx context.Context, providerOrderID string) (*Payment, error) {
	row := db.GlobalDBManager.QueryRow(ctx,
		`SELECT `+_paymentColumns+` FROM payments WHERE provider_order_id = $1`, providerOrderID)
	return scanPayment(row)
}

// MarkPaymentPaid 幂等推进 pending→paid。返回 nil 表示订单非 pending（已处理/不存在）。
func (s *PGStore) MarkPaymentPaid(ctx context.Context, id, tradeNo string) (*Payment, error) {
	row := db.GlobalDBManager.QueryRow(ctx,
		`UPDATE payments SET status = 'paid', trade_no = $2, paid_at = NOW()
		 WHERE id = $1 AND status = 'pending'
		 RETURNING `+_paymentColumns,
		id, tradeNo)
	p, err := scanPayment(row)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, nil // 已处理或不存在
		}
		return nil, err
	}
	return p, nil
}

func (s *PGStore) MarkPaymentFailed(ctx context.Context, id string) error {
	_, err := db.GlobalDBManager.Exec(ctx,
		`UPDATE payments SET status = 'failed' WHERE id = $1 AND status = 'pending'`, id)
	return err
}

func (s *PGStore) UpdatePaymentProvider(ctx context.Context, id, qrCode, providerOrderID string) error {
	_, err := db.GlobalDBManager.Exec(ctx,
		`UPDATE payments SET qr_code = $2, provider_order_id = $3 WHERE id = $1 AND status = 'pending'`,
		id, qrCode, providerOrderID)
	return err
}
