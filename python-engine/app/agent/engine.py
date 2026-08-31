"""
Engine module — 旧版 Agent 引擎，现为 runtime 模块的别名。

所有公共类已统一到 app.agent.runtime 中。
此模块保留为向后兼容的 re-export 层。
"""

from __future__ import annotations

from app.agent.runtime import (
    AgentEvent,
    AgentRuntime as AgentEngine,
    AgentSession,
    AgentTask,
    CompactionConfig,
    _compact_messages as compress_messages,
    _estimate_tokens,
    _snip_tool_results,
    _truncate_text,
    _truncate_tool_result,
)
from app.prompts import PromptEngine

# 旧版 ContextManager 由 CompactionConfig 替代
ContextManager = CompactionConfig

    
