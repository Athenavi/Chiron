"""subagent 工具 — 真子 Agent 委派（对应 deepseek-harness dsh-tool-subagent）

父 agent 调用 subagent(task)，在**独立 session** 上运行一个完整的
AgentRuntime 循环（独立消息历史、模式、轮次预算），收集其文本输出返回。
子 agent 执行后父任务的工具上下文被还原。

限制：max_turns 深度上限（默认 5，等效 maxDepth 预算）；模式复用
get_mode_config（minimal 子 agent 天然精简工具集）。
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from app.tools.context import get_all, get_gateway, get_tenant_id, get_user_id, restore_context
from app.tools.registry import registry

logger = logging.getLogger(__name__)

MAX_TURNS_CAP = 10
MAX_DEPTH = 3  # S3: 委派深度上限（deepseek 默认 maxDepth=3），防无限递归


def _expert_system_prompt(expert: str) -> str:
    """按名字从本次对话的专家清单里取人格；无匹配返回空串（退回通用 child）。

    只认清单里的名字，不接受自由文本 —— 否则模型可以用任意字符串把子代理塑造成
    它想要的人格，绕开用户在会话里选定的专家范围。
    """
    name = (expert or "").strip()
    if not name:
        return ""
    from app.tools.context import get_tool_context

    for item in get_tool_context("experts", []) or []:
        if isinstance(item, dict) and str(item.get("name", "")).strip() == name:
            return str(item.get("system_prompt", "") or "")
    return ""


async def subagent(
    task: str, mode: str = "normal", max_turns: int = 5, expert: str = ""
) -> dict[str, Any]:
    """Delegate *task* to a child agent running in its own session.

    The child runs a full agent loop (own message history, mode config,
    tool set) and its text output is returned. The parent's tool context is
    restored afterwards. max_turns bounds the child's loop (depth budget).
    subagent_depth recursion is capped at MAX_DEPTH (S3 security fix).

    expert: 可委派专家名 —— 取值必须来自本次对话的专家清单（用户多选的 Agent，
    由网关查库放进 context.agent.experts 并经 tool context 传递）。名字不在清单里
    就忽略该参数，退回通用 child。
    """
    if not task.strip():
        return {"error": "task is required"}
    gw = get_gateway()
    if gw is None:
        return {"error": "subagent requires an active agent runtime"}

    from app.agent.runtime import AgentRuntime, AgentTask
    from app.tools.context import get_tool_context

    depth = int(get_tool_context("subagent_depth", 0) or 0)
    if depth >= MAX_DEPTH:
        return {"error": f"delegation depth exceeded (max {MAX_DEPTH})"}

    persona = _expert_system_prompt(expert)
    parent_ctx = get_all()
    child = AgentTask(
        id=f"sub_{uuid.uuid4().hex[:8]}",
        tenant_id=get_tenant_id(),
        user_id=get_user_id(),
        session_id=f"sub_{uuid.uuid4().hex[:12]}",
        content=task,
        system_prompt=persona,
        llm_config={"mode": mode} if mode else {},
        max_turns=max(1, min(max_turns, MAX_TURNS_CAP)),
        subagent_depth=depth + 1,
    )

    runtime = AgentRuntime(gateway=gw)
    texts: list[str] = []
    errors: list[str] = []
    turns_used = 0
    try:
        async for evt in runtime.run(child):
            if evt.type == "text" and evt.content:
                texts.append(evt.content)
            elif evt.type == "error" and evt.error:
                errors.append(evt.error)
        turns_used = child.max_turns
    finally:
        restore_context(parent_ctx)  # 子 agent 已改写 context，父任务必须还原

    output = "\n".join(texts).strip()
    if not output and errors:
        return {"error": " | ".join(errors)}
    return {
        "output": output,
        "mode": mode or "normal",
        "max_turns": turns_used,
    }


registry.register(
    name="subagent",
    description=(
        "Delegate a task to a child agent that runs in its own session with "
        "its own message history and tool budget. Use it to parallelize "
        "independent work (read & summarize several files, draft a report, "
        "research a topic) while the main agent continues. The child's final "
        "text output is returned. Choose mode for the child: normal | minimal "
        "| ptc | creative. max_turns bounds the child loop."
    ),
    parameters={
        "type": "object",
        "properties": {
            "task": {"type": "string", "description": "The task for the child agent"},
            "mode": {
                "type": "string",
                "enum": ["normal", "minimal", "ptc", "creative"],
                "default": "normal",
            },
            "max_turns": {
                "type": "integer",
                "default": 5,
                "description": "Child loop turns cap (max 10)",
            },
            "expert": {
                "type": "string",
                "default": "",
                "description": (
                    "Optional: name of an expert to delegate to, taken from the "
                    "'可委派的专家' list in your system prompt. Names outside that "
                    "list are ignored and the child falls back to a generalist."
                ),
            },
        },
        "required": ["task"],
    },
    handler=subagent,
)
