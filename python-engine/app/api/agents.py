"""Agents API endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.tools.agent import agent_list

router = APIRouter(tags=["agents"])


@router.get("/v1/agents")
async def list_agents() -> dict[str, Any]:
    """Agent 列表（页面主链路已由 Go 的 DB agents 表提供；此端点保留给工具链）。"""
    return await agent_list()


class AgentDispatchRequest(BaseModel):
    task: str
    agent_type: str = ""
    # 完整 Agent 配置（Go 从 DB agents 表读取后传入）→ SubAgent 真执行
    name: str = ""
    description: str = ""
    system_prompt: str = ""
    tools: list[dict] = []
    model: str = ""
    max_turns: int = 5
    max_tokens: int = 4096
    temperature: float = 0.7
    tenant_id: str = ""
    session_id: str = ""


@router.post("/v1/agents/dispatch")
async def dispatch_agent(body: AgentDispatchRequest) -> dict[str, Any]:
    """
    派发 Agent 任务。

    - 携带 system_prompt（Go 传入 DB 配置）：用 SubAgent 执行完整 agent loop
      （LLM 流式 + 工具调用 + 多轮），返回真实结果。
    - 否则（工具链调用）：回退到内存 registry 的假派发。
    """
    if body.system_prompt.strip():
        # 标记用户活跃（驱动 MCP 插件轮询范围）
        from app.main import touch_user

        touch_user(body.tenant_id)

        # 延迟导入：避免 app.main ↔ app.api 循环依赖
        from app.agent.multi_agent import SubAgent
        from app.main import get_gateway

        try:
            gateway = await get_gateway()
        except RuntimeError:
            gateway = None
        if gateway is None:
            return {
                "success": False,
                "error": "LLM gateway not initialized",
                "output": "",
            }

        agent = SubAgent(
            name=body.name or body.agent_type or "agent",
            description=body.description or "",
            system_prompt=body.system_prompt,
            tools=body.tools or None,
            gateway=gateway,
            model=body.model or "deepseek-chat",
            max_turns=body.max_turns or 5,
            max_tokens=body.max_tokens or 4096,
            temperature=body.temperature or 0.7,
        )
        result = await agent.run(
            task=body.task,
            context={"session_id": body.session_id} if body.session_id else None,
            tenant_id=body.tenant_id,
        )
        return {
            "success": result.success,
            "output": result.output,
            "error": result.error,
            "tool_calls": result.tool_calls,
            "token_usage": result.token_usage,
            "duration": result.duration,
            "session_id": body.session_id,
        }

    from app.tools.agent import agent_dispatch

    return await agent_dispatch(task=body.task, agent_type=body.agent_type)


class AgentApprovalRequest(BaseModel):
    """工具审批决策请求（Go 网关 /v1/agent/approval 转发而来）。"""

    tool_call_id: str
    approved: bool
    reason: str = ""
    session_id: str = ""
    user_id: str = ""


@router.post("/v1/agent/approval")
async def submit_agent_approval(body: AgentApprovalRequest) -> dict[str, Any]:
    """处理工具审批决策（三态栅栏"确认"态的回调）。

    多副本语义：优先唤醒**本实例**正在等待的 runtime（零延迟）；若本实例无人等待
    （决策被路由到其它副本），则写 Redis 决策键，由正在等待的副本取走 ——
    这样审批不再依赖会话亲和路由，副本扩缩容期间也能正确送达。
    """
    from app.agent.runtime import submit_approval_global

    if not body.tool_call_id:
        return {"ok": False, "error": "tool_call_id is required"}

    ok = await submit_approval_global(body.tool_call_id, body.approved, body.reason)
    return {
        "ok": ok,
        "tool_call_id": body.tool_call_id,
        "approved": body.approved,
    }
