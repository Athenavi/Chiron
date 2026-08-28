package config

import (
	"bufio"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/base64"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"
)

type Config struct {
	AppSecret string

	// Server
	Port         string
	ReadTimeout  time.Duration
	WriteTimeout time.Duration
	IdleTimeout  time.Duration

	// Database
	PostgresDSN      string
	PostgresMaxConn  int
	PostgresMinConn  int
	PostgresReadDSNs []string // read-replica DSNs (comma-separated)

	// Redis
	RedisMode          string // "single", "cluster", "sentinel"
	RedisAddr          string
	RedisPassword      string
	RedisDB            int
	RedisAddrs         []string // for cluster mode
	RedisMasterName    string   // for sentinel mode
	RedisSentinelAddrs []string // for sentinel mode
	RedisPoolSize      int

	// Auth
	JWTSecret     string
	JWTExpiration time.Duration
	InternalToken string

	// Registration
	DisableRegistration bool

	// Cookie
	CookieSecure bool

	// CORS
	CORSOrigins string

	// Storage
	StorageBackend string // "local" or "s3"
	StorageRoot    string // local root path
	S3Endpoint     string
	S3Bucket       string
	S3AccessKey    string
	S3SecretKey    string
	S3UseSSL       bool // S3/MinIO use SSL

	// Rate Limit
	RateLimitRPM       int
	RateLimitFailClose bool
	RateLimitGlobal    int // global requests per minute

	// TrustedProxyCIDRs trusted reverse-proxy CIDRs (comma separated).
	// X-Forwarded-For / X-Real-IP are only honored when the direct peer
	// matches one of these CIDRs; otherwise clients could spoof IP-based limits.
	TrustedProxyCIDRs []string

	// MetricsToken shared bearer token for Prometheus to scrape /metrics.
	// When empty, /metrics still requires JWT admin permission.
	MetricsToken string

	// Log
	LogLevel string // debug / info / warn / error

	PublicBaseURL         string
	FrontendURL           string
	AlipayAppID           string
	AlipayPrivateKey      string
	AlipayPublicKey       string
	AlipayGateway         string
	WechatMchID           string
	WechatAppID           string
	WechatAPIv3Key        string
	WechatMchCertSerialNo string
	WechatMchPrivateKey   string

	// Agent behavior
	AgentMaxTurns       int // max LLM-tool turns per run (default 10)
	AgentMaxTokens      int // max output tokens per LLM call (default 8192)
	AgentContextLimit   int // max messages before pruning (default 20)
	AgentMaxConcurrency int // max concurrent agent runs (default 20)

	// Python AI 寮曟�?	PythonEngineAddress string // HTTP 鍦板潃锛屽 "localhost:8000"
	PythonEngineTimeout time.Duration

	// Temporal / LLMGateway 涓洪仐鐣欐閰嶇疆锛堟湭浣跨敤锛夛紝宸茬Щ�?

	// PayPal
	PayPalClientID string
	PayPalSecret   string
	PayPalSandbox  bool

	// Plugins
	PluginsConfigPath string // path to plugins.json (MCP server config)
	PluginDataDir     string // per-user plugin config root: {PluginDataDir}/{user_id}/plugins.json

	// DataDir is the runtime data directory for install.lock, backups, etc.
	DataDir string
}

func Load() *Config {
	cfg := loadConfig()

	// APP_SECRET is required锛堥儴缃茬骇涓诲瘑閽ワ級�?
	if !cfg.ValidateAppSecret() {
		os.Stderr.WriteString("FATAL: APP_SECRET environment variable must be set to a strong, unique value (32+ chars)\n")
		os.Exit(1)
	}

	if cfg.JWTSecret == "" {
		cfg.JWTSecret = deriveSubsecret(cfg.AppSecret, "chiron-jwt")
	}
	if cfg.InternalToken == "" {
		cfg.InternalToken = deriveSubsecret(cfg.AppSecret, "chiron-internal")
	}

	// JWT_SECRET is required (derived or explicit).
	if !ValidateJWTSecret(cfg.JWTSecret) {
		os.Stderr.WriteString("FATAL: JWT_SECRET (or its source APP_SECRET) must be set to a strong, unique value\n")
		os.Exit(1)
	}

	// CORS production warning
	if cfg.CORSOrigins == "http://localhost:3000,http://localhost:5173" {
		os.Stderr.WriteString("WARNING: CORS_ORIGINS is set to development defaults. Set CORS_ORIGINS to your production domain.\n")
	}

	return cfg
}

func LoadAllowUnconfigured() *Config {
	cfg := loadConfig()

	if cfg.JWTSecret == "" {
		cfg.JWTSecret = deriveSubsecret(cfg.AppSecret, "chiron-jwt")
	}
	if cfg.InternalToken == "" {
		cfg.InternalToken = deriveSubsecret(cfg.AppSecret, "chiron-internal")
	}
	return cfg
}

func loadConfig() *Config {
	loadDotEnv()     // .env file overrides config file
	loadConfigFile() // JSON config file (lowest priority)
	cfg := &Config{
		AppSecret:           getEnv("APP_SECRET", ""),
		Port:                getEnv("PORT", "8080"),
		ReadTimeout:         getDuration("READ_TIMEOUT", 10*time.Second),
		WriteTimeout:        getDuration("WRITE_TIMEOUT", 60*time.Second),
		IdleTimeout:         getDuration("IDLE_TIMEOUT", 120*time.Second),
		PostgresDSN:         getEnv("POSTGRES_DSN", ""),
		PostgresMaxConn:     getInt("POSTGRES_MAX_CONN", 20),
		PostgresMinConn:     getInt("POSTGRES_MIN_CONN", 2),
		PostgresReadDSNs:    getStringSlice("POSTGRES_READ_DSNS", []string{}),
		RedisMode:           getEnv("REDIS_MODE", "single"),
		RedisAddr:           getEnv("REDIS_ADDR", "localhost:6379"),
		RedisPassword:       getEnv("REDIS_PASSWORD", ""),
		RedisDB:             getInt("REDIS_DB", 0),
		RedisAddrs:          getStringSlice("REDIS_ADDRS", []string{}),
		RedisMasterName:     getEnv("REDIS_MASTER_NAME", ""),
		RedisSentinelAddrs:  getStringSlice("REDIS_SENTINEL_ADDRS", []string{}),
		RedisPoolSize:       getInt("REDIS_POOL_SIZE", 50),
		JWTSecret:           getEnv("JWT_SECRET", ""),
		JWTExpiration:       getDuration("JWT_EXPIRATION", 24*time.Hour),
		InternalToken:       getEnv("INTERNAL_TOKEN", ""),
		DisableRegistration: isTruthy(getEnv("DISABLE_REGISTRATION", "")),
		CookieSecure:        isTruthy(getEnv("COOKIE_SECURE", "")),
		CORSOrigins:         getEnv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173"),
		StorageBackend:      getEnv("STORAGE_BACKEND", "local"),
		StorageRoot:         getEnv("STORAGE_ROOT", filepath.Join(GetDefaultDataDir(), "workspace")),
		S3Endpoint:          getEnv("S3_ENDPOINT", ""),
		S3Bucket:            getEnv("S3_BUCKET", "chiron"),
		S3AccessKey:         getEnv("S3_ACCESS_KEY", ""),
		S3SecretKey:         getEnv("S3_SECRET_KEY", ""),
		S3UseSSL:            isTruthy(getEnv("S3_USE_SSL", "")),
		RateLimitRPM:        getInt("RATE_LIMIT_RPM", 100),
		RateLimitFailClose:  isTruthy(getEnv("RATE_LIMIT_FAIL_CLOSE", "")),
		RateLimitGlobal:     getInt("RATE_LIMIT_GLOBAL", 10000),
		TrustedProxyCIDRs:   getStringSlice("TRUSTED_PROXY_CIDRS", []string{}),
		MetricsToken:        getEnv("METRICS_TOKEN", ""),
		LogLevel:            getEnv("LOG_LEVEL", "info"),

		// 鏀粯锛堟敮浠樺疂/寰俊锛?
		PublicBaseURL:         getEnv("PUBLIC_BASE_URL", ""),
		FrontendURL:           getEnv("FRONTEND_URL", ""),
		AlipayAppID:           getEnv("ALIPAY_APP_ID", ""),
		AlipayPrivateKey:      getEnv("ALIPAY_PRIVATE_KEY", ""),
		AlipayPublicKey:       getEnv("ALIPAY_PUBLIC_KEY", ""),
		AlipayGateway:         getEnv("ALIPAY_GATEWAY", ""),
		WechatMchID:           getEnv("WXPAY_MCH_ID", ""),
		WechatAppID:           getEnv("WXPAY_APP_ID", ""),
		WechatAPIv3Key:        getEnv("WXPAY_API_V3_KEY", ""),
		WechatMchCertSerialNo: getEnv("WXPAY_MCH_CERT_SERIAL_NO", ""),
		WechatMchPrivateKey:   getEnv("WXPAY_MCH_PRIVATE_KEY", ""),
		AgentMaxTurns:         getInt("AGENT_MAX_TURNS", 10),
		AgentMaxTokens:        getInt("AGENT_MAX_TOKENS", 8192),
		AgentContextLimit:     getInt("AGENT_CONTEXT_LIMIT", 20),
		AgentMaxConcurrency:   getInt("AGENT_MAX_CONCURRENCY", 20),

		PythonEngineAddress: getEnv("PYTHON_ENGINE_ADDRESS", "localhost:8000"),
		PythonEngineTimeout: getDuration("PYTHON_ENGINE_TIMEOUT", 5*time.Minute),

		PayPalClientID: getEnv("PAYPAL_CLIENT_ID", ""),
		PayPalSecret:   getEnv("PAYPAL_SECRET", ""),
		PayPalSandbox:  isTruthy(getEnv("PAYPAL_SANDBOX", "")),

		PluginsConfigPath: getEnv("PLUGINS_CONFIG_PATH", filepath.Join(GetDefaultDataDir(), "config", "plugins.json")),
		PluginDataDir:     getEnv("PLUGIN_DATA_DIR", filepath.Join(GetDefaultDataDir(), "plugins")),
		DataDir:           getEnv("CHIRON_DATA_DIR", GetDefaultDataDir()),
	}

	return cfg
}

// GetDefaultDataDir returns the default data directory based on environment:
// - CHIRON_DATA_DIR env var (highest priority, set by caller)
// - ~/.chiron (local development)
// - data (fallback)
// This is the canonical implementation; do not duplicate elsewhere.
func GetDefaultDataDir() string {
	if v := os.Getenv("CHIRON_DATA_DIR"); v != "" {
		return v
	}
	// Try to detect production vs development
	home, err := os.UserHomeDir()
	if err == nil {
		return filepath.Join(home, ".chiron")
	}
	return "data"
}

func (c *Config) ValidateAppSecret() bool {
	return ValidateJWTSecret(c.AppSecret)
}

func deriveSubsecret(secret, domain string) string {
	if secret == "" {
		return ""
	}
	h := hmac.New(sha256.New, []byte(secret))
	h.Write([]byte(domain))
	return base64.RawURLEncoding.EncodeToString(h.Sum(nil))
}

// DeriveLockKey 派生用于加密 install.lock �?AES 密钥
func DeriveLockKey(appSecret string) []byte {
	if appSecret == "" {
		return nil
	}
	h := hmac.New(sha256.New, []byte(appSecret))
	h.Write([]byte("chiron-install-lock-key"))
	return h.Sum(nil)
}

// ValidateJWTSecret returns true if the secret is valid for production use.
func ValidateJWTSecret(secret string) bool {
	if secret == "" {
		return false
	}
	// Reject weak/known secrets
	weakSecrets := []string{
		"dev-secret-change-in-production",
		"dev-secret-change-in-production-12345678",
		"secret",
		"test-secret",
		"change-me",
		"changeme",
	}
	for _, ws := range weakSecrets {
		if secret == ws {
			return false
		}
	}
	// Require minimum length for security (at least 32 chars for strong encryption)
	if len(secret) < 32 {
		return false
	}
	return true
}

func getEnv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func getInt(key string, fallback int) int {
	if v := os.Getenv(key); v != "" {
		if i, err := strconv.Atoi(v); err == nil {
			return i
		}
	}
	return fallback
}

func getDuration(key string, fallback time.Duration) time.Duration {
	if v := os.Getenv(key); v != "" {
		if d, err := time.ParseDuration(v); err == nil {
			return d
		}
	}
	return fallback
}

func getStringSlice(key string, fallback []string) []string {
	if v := os.Getenv(key); v != "" {
		// Split by comma and trim whitespace
		parts := strings.Split(v, ",")
		result := make([]string, 0, len(parts))
		for _, p := range parts {
			p = strings.TrimSpace(p)
			if p != "" {
				result = append(result, p)
			}
		}
		if len(result) > 0 {
			return result
		}
	}
	return fallback
}

// isTruthy returns true if s is "true", "1", "yes", or "on" (case-insensitive).
func isTruthy(s string) bool {
	switch s {
	case "true", "1", "yes", "on", "TRUE", "YES", "ON":
		return true
	}
	return false
}

// loadDotEnv reads .env file and sets environment variables if not already set.
// findFileUpward searches for a file starting from the current directory
// and walking up to the filesystem root. Returns the first match.
func findFileUpward(name string) string {
	dir, _ := os.Getwd()
	for {
		candidate := filepath.Join(dir, name)
		if _, err := os.Stat(candidate); err == nil {
			return candidate
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			break // reached filesystem root
		}
		dir = parent
	}
	return name // fall back to original relative path (will fail with useful error)
}

func loadDotEnv() {
	path := findFileUpward(".env")
	data, err := os.ReadFile(path)
	if err != nil {
		return // .env file not found, skip
	}
	scanner := bufio.NewScanner(strings.NewReader(string(data)))
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		parts := strings.SplitN(line, "=", 2)
		if len(parts) != 2 {
			continue
		}
		key := strings.TrimSpace(parts[0])
		val := strings.TrimSpace(parts[1])
		// Strip quotes if present
		if len(val) >= 2 && ((val[0] == '"' && val[len(val)-1] == '"') || (val[0] == '\'' && val[len(val)-1] == '\'')) {
			val = val[1 : len(val)-1]
		}
		// Only set if not already set (env vars take precedence)
		if os.Getenv(key) == "" {
			os.Setenv(key, val)
		}
	}
}
