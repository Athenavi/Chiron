"""Agent 评估系统 — 在线/离线评估评估、Prompt 版本管理。

支持：
- 离线评估：使用测试数据集自动评估 Agent 回复质量
- 在线评估：生产环境隐式打分（用户反馈、重生成率、会话成功率）
- Prompt 版本管理：版本化 Prompt 模板，A/B 测试
"""

from __future__ import annotations

from .offline import EvalDataset, EvalRun, EvalResult, run_offline
from .online import OnlineTracker, score_session
from .prompt_manager import PromptTemplate, PromptVersion, PromptManager

__all__ = [
    "EvalDataset", "EvalRun", "EvalResult", "run_offline",
    "OnlineTracker", "score_session",
    "PromptTemplate", "PromptVersion", "PromptManager",
]