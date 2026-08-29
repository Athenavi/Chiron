"""在线评估 — 生产环境隐式打分。

评分来源：
- 用户反馈（👍/👎）
- 重生成率
- 会话成功率（是否达成用户目标）
- 工具调用成功率
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SessionScore:
    """会话评分。"""
    session_id: str
    user_id: str
    score: float  # 0.0 - 1.0
    feedback: str | None = None  # up | down | null
    regenerated: bool = False
    completed: bool = False
    tool_errors: int = 0
    token_used: int = 0
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class OnlineTracker:
    """在线评估跟踪器（进程内，生产环境应替换为 Redis/DB 持久化）。"""

    def __init__(self, window_size: int = 1000):
        self._scores: list[SessionScore] = []
        self._window_size = window_size

    def record(self, score: SessionScore) -> None:
        """记录一次会话评分。"""
        self._scores.append(score)
        if len(self._scores) > self._window_size:
            self._scores = self._scores[-self._window_size:]

    def summary(self, since: float | None = None) -> dict[str, Any]:
        """计算当前窗口的统计摘要。"""
        cutoff = since or (time.time() - 3600)  # 默认最近1小时
        recent = [s for s in self._scores if s.duration_ms > 0]  # 简化：实际应基于时间
        if not recent:
            return {"count": 0}
        avg_score = sum(s.score for s in recent) / len(recent)
        feedbacks = [s for s in recent if s.feedback]
        up = sum(1 for s in feedbacks if s.feedback == "up")
        down = sum(1 for s in feedbacks if s.feedback == "down")
        return {
            "count": len(recent),
            "avg_score": round(avg_score, 4),
            "feedback_up": up,
            "feedback_down": down,
            "regeneration_rate": round(sum(1 for s in recent if s.regenerated) / len(recent), 4),
            "completion_rate": round(sum(1 for s in recent if s.completed) / len(recent), 4),
            "tool_error_rate": round(sum(1 for s in recent if s.tool_errors > 0) / len(recent), 4),
        }


def score_session(
    session_id: str,
    user_id: str,
    *,
    feedback: str | None = None,
    regenerated: bool = False,
    completed: bool = False,
    tool_errors: int = 0,
    token_used: int = 0,
    duration_ms: float = 0.0,
) -> SessionScore:
    """计算单个会话的综合评分。"""
    score = 0.5  # 基准
    if feedback == "up":
        score += 0.3
    elif feedback == "down":
        score -= 0.3
    if regenerated:
        score -= 0.1
    if completed:
        score += 0.2
    if tool_errors > 0:
        score -= min(tool_errors * 0.1, 0.3)
    score = max(0.0, min(1.0, score))
    return SessionScore(
        session_id=session_id,
        user_id=user_id,
        score=score,
        feedback=feedback,
        regenerated=regenerated,
        completed=completed,
        tool_errors=tool_errors,
        token_used=token_used,
        duration_ms=duration_ms,
    )