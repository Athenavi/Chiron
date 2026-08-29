"""离线评估 — 使用测试数据集评估 Agent 回复质量。

评估维度：
- 正确性（Correctness）：答案与 ground truth 的语义匹配度
- 完整性（Completeness）：是否覆盖了问题所有关键点
- 幻觉（Hallucination）：是否包含与事实不符的内容
- 工具使用（Tool Use）：工具调用是否准确高效
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class EvalExample:
    """一个评估样本：输入 + 期望输出 + 可选标签。"""
    id: str
    input: str  # 用户输入
    expected: str  # 期望的助手回复
    tools: list[dict] | None = None  # 可选：期望的工具调用
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvalDataset:
    """评估数据集。"""
    name: str
    examples: list[EvalExample]
    description: str = ""

    @classmethod
    def from_json(cls, path: str) -> EvalDataset:
        """从 JSON 文件加载数据集。"""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        examples = [
            EvalExample(
                id=ex.get("id", str(uuid.uuid4())),
                input=ex["input"],
                expected=ex["expected"],
                tools=ex.get("tools"),
                tags=ex.get("tags", []),
                metadata=ex.get("metadata", {}),
            )
            for ex in data.get("examples", [])
        ]
        return cls(name=data.get("name", "unnamed"), examples=examples, description=data.get("description", ""))

    def filter(self, tags: list[str] | None = None) -> EvalDataset:
        """按标签过滤样本。"""
        if not tags:
            return self
        return EvalDataset(
            name=self.name,
            examples=[ex for ex in self.examples if any(t in ex.tags for t in tags)],
            description=self.description,
        )


@dataclass
class EvalScore:
    """单个评估维度得分。"""
    dimension: str  # correctness | completeness | hallucination | tool_use
    score: float  # 0.0 - 1.0
    reason: str = ""


@dataclass
class EvalResult:
    """单个样本的评估结果。"""
    example_id: str
    input: str
    expected: str
    actual: str
    scores: list[EvalScore]
    overall: float  # 综合得分
    duration_ms: float = 0.0
    error: str | None = None


@dataclass
class EvalRun:
    """一次完整的评估运行。"""
    id: str
    dataset_name: str
    results: list[EvalResult]
    created_at: datetime
    summary: dict[str, float] = field(default_factory=dict)

    def compute_summary(self) -> dict[str, float]:
        """计算各维度平均分。"""
        if not self.results:
            self.summary = {}
            return self.summary
        dims = {}
        for r in self.results:
            for s in r.scores:
                if s.dimension not in dims:
                    dims[s.dimension] = []
                dims[s.dimension].append(s.score)
        self.summary = {
            "overall": sum(r.overall for r in self.results) / len(self.results),
            **{dim: sum(scores) / len(scores) for dim, scores in dims.items()},
            "count": len(self.results),
            "passed": sum(1 for r in self.results if r.overall >= 0.7),
            "failed": sum(1 for r in self.results if r.overall < 0.7),
        }
        return self.summary


# ── 评分器 ──

Scorer = Callable[[str, str, str], list[EvalScore]]


def default_scorer(actual: str, expected: str, _input: str) -> list[EvalScore]:
    """默认评分器：基于简单字符串匹配的启发式评分。

    生产环境应替换为 LLM 判分器（如 GPT-4 作为 judge）。
    """
    import difflib

    ratio = difflib.SequenceMatcher(None, actual.lower(), expected.lower()).ratio()
    return [
        EvalScore(dimension="correctness", score=min(ratio * 1.2, 1.0), reason="text similarity"),
        EvalScore(dimension="completeness", score=min(ratio, 1.0), reason="length ratio based"),
        EvalScore(dimension="hallucination", score=1.0, reason="no hallucination detection (default)"),
        EvalScore(dimension="tool_use", score=1.0, reason="no tool use check (default)"),
    ]


# ── 执行 ──


async def run_offline(
    dataset: EvalDataset,
    agent_fn: Callable[[str], Awaitable[str]],
    scorer: Scorer | None = None,
) -> EvalRun:
    """运行离线评估。

    Args:
        dataset: 评估数据集
        agent_fn: 异步函数，输入用户消息，返回助手回复
        scorer: 评分器，默认使用 default_scorer

    Returns:
        EvalRun: 评估运行结果
    """
    from asyncio import to_thread

    scorer = scorer or default_scorer
    results: list[EvalResult] = []

    for example in dataset.examples:
        start = time.time()
        try:
            actual = await agent_fn(example.input)
            elapsed = (time.time() - start) * 1000
            scores = scorer(actual, example.expected, example.input)
            overall = sum(s.score for s in scores) / len(scores)
            results.append(EvalResult(
                example_id=example.id,
                input=example.input,
                expected=example.expected,
                actual=actual,
                scores=scores,
                overall=overall,
                duration_ms=elapsed,
            ))
        except Exception as e:
            logger.error("eval example %s failed: %s", example.id, e)
            elapsed = (time.time() - start) * 1000
            results.append(EvalResult(
                example_id=example.id,
                input=example.input,
                expected=example.expected,
                actual="",
                scores=[],
                overall=0.0,
                duration_ms=elapsed,
                error=str(e),
            ))

    run = EvalRun(
        id=str(uuid.uuid4()),
        dataset_name=dataset.name,
        results=results,
        created_at=datetime.now(timezone.utc),
    )
    run.compute_summary()
    return run


from typing import Awaitable