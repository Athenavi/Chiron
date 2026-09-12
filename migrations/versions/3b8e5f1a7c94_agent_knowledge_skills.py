"""agent knowledge & skills binding

给 agents 表加两列，让 Agent 能自带知识库与技能 —— 此前 Agent 只能靠用户每次
在对话里手动带上下文（而 Agent 派发走的是独立链路，根本带不进去）：

- `kb_id`：默认知识库，派发时用它做 RAG 检索（引擎侧 `_get_rag_context` 已支持）；
- `skills`：技能名数组，派发时只启用这些技能（引擎侧 `_get_skills_context` 已支持筛选）。

两列都允许为空 = 保持既有行为（不绑定任何知识库/技能），因此本迁移对存量数据是 no-op。
DDL 全部使用 IF NOT EXISTS，与仓库既有迁移（f7c2d05a1b8e 起的风格）保持一致。

Revision ID: 3b8e5f1a7c94
Revises: 9c1d7a4e5b21
Create Date: 2026-02-12 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '3b8e5f1a7c94'
down_revision: Union[str, Sequence[str], None] = '9c1d7a4e5b21'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE agents ADD COLUMN IF NOT EXISTS kb_id TEXT")
    op.execute("ALTER TABLE agents ADD COLUMN IF NOT EXISTS skills JSONB")


def downgrade() -> None:
    op.execute("ALTER TABLE agents DROP COLUMN IF EXISTS skills")
    op.execute("ALTER TABLE agents DROP COLUMN IF EXISTS kb_id")
