package api

import "time"

// P0性能优化：集中管理超时常量，避免散落各处的魔法数字

// nullableStr returns nil for empty strings, useful for nullable DB columns.
func nullableStr(s string) *string {
	if s == "" {
		return nil
	}
	return &s
}

// intVal returns the int value of a JSON field or a default value.
func intVal(m map[string]interface{}, key string, fallback int) int {
	if v, ok := m[key]; ok {
		if f, ok := v.(float64); ok {
			return int(f)
		}
	}
	return fallback
}
