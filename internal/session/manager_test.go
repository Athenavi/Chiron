package session

import (
	"encoding/json"
	"testing"
)

// 回归保护：tool_calls.input 是 jsonb 列，模型的 arguments 可能是空串（无参调用）
// 或被截断的半成品 JSON —— 直接 $4::jsonb 会让整条 INSERT 失败并只打日志，
// 表现为"工具调用历史与结果刷新后全部丢失"。normalizeToolInput 必须保证写入合法。
func TestNormalizeToolInput(t *testing.T) {
	cases := []struct {
		name string
		in   string
		want string
	}{
		{"空串降级为空对象", "", "{}"},
		{"仅空白降级为空对象", "   \n\t", "{}"},
		{"合法对象原样保留", `{"path":"a.txt"}`, `{"path":"a.txt"}`},
		{"合法空对象原样保留", `{}`, `{}`},
		{"合法数组原样保留", `[1,2]`, `[1,2]`},
		{"截断的半成品包一层 raw", `{"path":`, `{"raw":"{\"path\":"}`},
		{"非 JSON 文本包一层 raw", "not-json", `{"raw":"not-json"}`},
	}
	for _, c := range cases {
		if got := normalizeToolInput(c.in); got != c.want {
			t.Errorf("%s: normalizeToolInput(%q) = %q, want %q", c.name, c.in, got, c.want)
		}
	}

	// 无论输入如何，输出都必须是合法 JSON（jsonb 写入前提）
	for _, in := range []string{"", "   ", `{"a":1}`, `{"path":`, "x", "null-ish", `"str"`} {
		out := normalizeToolInput(in)
		if !json.Valid([]byte(out)) {
			t.Errorf("normalizeToolInput(%q) 输出非法 JSON: %q", in, out)
		}
	}
}
