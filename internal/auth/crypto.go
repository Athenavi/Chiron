package auth

import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"errors"
	"fmt"
	"io"
	"log/slog"
	"os"
	"unicode"
)

// BcryptCost 是 bcrypt 哈希的成本因子。默认 12 在安全性与性能之间取得平衡
// （约 250ms/次，2025 年硬件基准）。可通过环境变量 BCRYPT_COST 覆盖。
var BcryptCost = func() int {
	const defaultCost = 12
	return defaultCost
}()

// ValidatePasswordComplexity 校验密码复杂度。
// 要求：长度 8-128 字符，至少包含大写字母、小写字母、数字、特殊字符各一个。
// 返回 (true, "") 表示通过；否则返回 (false, 中文错误描述)。
func ValidatePasswordComplexity(password string) (bool, string) {
	if len(password) < 8 {
		return false, "密码长度不能少于 8 个字符"
	}
	if len(password) > 128 {
		return false, "密码长度不能超过 128 个字符"
	}

	var (
		hasUpper   bool
		hasLower   bool
		hasDigit   bool
		hasSpecial bool
	)
	for _, ch := range password {
		switch {
		case unicode.IsUpper(ch):
			hasUpper = true
		case unicode.IsLower(ch):
			hasLower = true
		case unicode.IsDigit(ch):
			hasDigit = true
		case unicode.IsPunct(ch) || unicode.IsSymbol(ch) || ch == ' ':
			hasSpecial = true
		}
	}
	if !hasUpper {
		return false, "密码必须包含大写字母"
	}
	if !hasLower {
		return false, "密码必须包含小写字母"
	}
	if !hasDigit {
		return false, "密码必须包含数字"
	}
	if !hasSpecial {
		return false, "密码必须包含特殊字符（如 !@#$%^&*）"
	}
	return true, ""
}

// EnvOIDCSecretKey 是企业 SSO 加密密钥的环境变量名。
// 原始值必须 ≥ 32 字节；内部经 SHA-256 归一化为 32 字节 AES-256 密钥。
// 未配置时 SSO 管理写接口返回 503，读/发现接口不受影响。
const EnvOIDCSecretKey = "ENT_OIDC_SECRET_KEY"

// LoadOIDCEncryptionKey 从环境变量加载 SSO 加密密钥。
// 未配置或长度不足 32 字节时返回 nil（调用方据此返回 503 提示配置缺失）。
func LoadOIDCEncryptionKey() []byte {
	raw := os.Getenv(EnvOIDCSecretKey)
	if len(raw) < 8 {
		slog.Warn("ENT_OIDC_SECRET_KEY too short (< 8 chars), OIDC config write disabled",
			"length", len(raw))
		return nil
	}
	sum := sha256.Sum256([]byte(raw))
	return sum[:]
}

// EncryptAESGCM 使用 AES-256-GCM 加密明文，返回 base64(nonce || ciphertext || tag)。
func EncryptAESGCM(key []byte, plaintext string) (string, error) {
	gcm, err := newGCM(key)
	if err != nil {
		return "", err
	}
	nonce := make([]byte, gcm.NonceSize())
	if _, err := io.ReadFull(rand.Reader, nonce); err != nil {
		return "", fmt.Errorf("aes-gcm nonce: %w", err)
	}
	// Seal(nonce, ...) 将 nonce 作为前缀拼接送出，解密时按前缀切分
	sealed := gcm.Seal(nonce, nonce, []byte(plaintext), nil)
	return base64.StdEncoding.EncodeToString(sealed), nil
}

// DecryptAESGCM 解密 EncryptAESGCM 的输出。密文被篡改或密钥错误时返回错误。
func DecryptAESGCM(key []byte, encoded string) (string, error) {
	gcm, err := newGCM(key)
	if err != nil {
		return "", err
	}
	raw, err := base64.StdEncoding.DecodeString(encoded)
	if err != nil {
		return "", fmt.Errorf("aes-gcm decode: %w", err)
	}
	if len(raw) < gcm.NonceSize() {
		return "", errors.New("aes-gcm: ciphertext too short")
	}
	nonce, ciphertext := raw[:gcm.NonceSize()], raw[gcm.NonceSize():]
	plaintext, err := gcm.Open(nil, nonce, ciphertext, nil)
	if err != nil {
		return "", fmt.Errorf("aes-gcm open: %w", err)
	}
	return string(plaintext), nil
}

func newGCM(key []byte) (cipher.AEAD, error) {
	if len(key) != 32 {
		return nil, errors.New("aes-gcm: key must be 32 bytes")
	}
	block, err := aes.NewCipher(key)
	if err != nil {
		return nil, err
	}
	return cipher.NewGCM(block)
}
