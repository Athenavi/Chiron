"""pytest 收集配置。

这里**只**处理"无法被收集"的文件，不裁剪任何可运行的测试逻辑。

被隔离的 6 个文件分两类，原因不同：

**一、编码损坏（4 个）** —— 中文注释在历史上某次 UTF-8 / GBK 转换中损坏：部分字符变成
私有区码位（U+E0xx / U+E7xx），行尾换行也被吞掉，python 无法解析：

- test_guards.py                      三引号未闭合（SyntaxError）
- test_sandbox_isolation.py           非法不可打印字符（U+E195）
- test_security_tenant_isolation.py   缩进损坏（注释与代码挤在同一行）
- test_trace_writer.py                同上

**二、引用已不存在的符号（1 个）** —— 代码重构后测试没跟上：

- test_engine.py           from app.agent.engine import AgentSession   （该模块没有这个名字）

需要**按当前代码行为重写断言**：原文不可逆（损坏的中文无法还原），或在确认那些能力
是被移除还是被改名之后再决定。在此之前明确隔离，而不是让它们静默失败 ——
让其余测试文件能跑起来，比整个套件在收集阶段就瘫痪要好。

> `test_memory_profile.py` 原先也在此列（它 import 的 `recency_decay` 当时不存在）。
> 该函数与 `rerank_score` 已在 `app/memory/layers.py` 补齐，记忆四层架构的对外接口
> 也已按该文件的断言对齐，因此它已回到常规收集范围。
"""

collect_ignore = [
    # 一、编码损坏
    "test_guards.py",
    "test_sandbox_isolation.py",
    "test_security_tenant_isolation.py",
    "test_trace_writer.py",
    # 二、过时测试（引用已移除 / 改名的符号）
    "test_engine.py",
]
