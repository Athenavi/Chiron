/**
 * 工作台上下文的解析与组装（纯逻辑，无 DOM）。
 *
 * 对话是六大工作台的枢纽：知识库 / Agent / 技能 / 工作流都可以"带进对话"。
 * 这里定两件事：
 * 1. **URL 约定**：同名参数可重复（`?kb=a&kb=b&skill=x`），同名即同一类，可多选；
 *    单值写法（`?kb=a`）保持兼容。
 * 2. **发给引擎的形态**：单值字段取首个（老后端只认它），同时给出 `*_ids` 数组
 *    供支持多值的新后端使用 —— 两边都能工作。
 */

export type ContextChipType = 'kb' | 'agent' | 'skill' | 'workflow'

export interface ContextChip {
  type: ContextChipType
  label: string
  value: string
}

/** 参数名 → chip 类型与展示名。展示名只是占位，真实名称由调用方按 id 补全。 */
const PARAMS: { param: string; type: ContextChipType; label: (value: string) => string }[] = [
  { param: 'kb', type: 'kb', label: value => `知识库 #${value.slice(0, 8)}` },
  { param: 'agent', type: 'agent', label: value => `Agent #${value.slice(0, 8)}` },
  { param: 'skill', type: 'skill', label: value => `技能 ${value}` },
  { param: 'workflow', type: 'workflow', label: value => `工作流 ${value}` },
]

/** query 值既可能是字符串（单值），也可能是字符串数组（重复参数） */
function toList(raw: unknown): string[] {
  if (typeof raw === 'string') return raw.trim() ? [raw.trim()] : []
  if (Array.isArray(raw)) {
    return raw
      .filter((item): item is string => typeof item === 'string')
      .map(item => item.trim())
      .filter(Boolean)
  }
  return []
}

/** 从路由 query 解析上下文 chips；同类参数出现多次时全部保留 */
export function parseContextQuery(query: Record<string, unknown> | null | undefined): ContextChip[] {
  if (!query) return []
  const chips: ContextChip[] = []
  for (const { param, type, label } of PARAMS) {
    for (const value of toList(query[param])) chips.push({ type, label: label(value), value })
  }
  return chips
}

function valuesOf(chips: readonly ContextChip[], type: ContextChipType): string[] {
  const out: string[] = []
  for (const chip of chips) {
    if (chip.type === type && chip.value && !out.includes(chip.value)) out.push(chip.value)
  }
  return out
}

/**
 * 组装发给引擎的 context。
 *
 * 单值字段（`kb_id`/`agent_id`/`workflow_id`）取首个：老后端只认这三个标量，
 * 保留它们才不会因为前端升级而失效；`kb_ids`/`agent_ids`/`workflow_ids` 供新后端读多值。
 */
export function buildWorkbenchContext(chips: readonly ContextChip[]): Record<string, unknown> | undefined {
  const ctx: Record<string, unknown> = {}

  const kbIds = valuesOf(chips, 'kb')
  if (kbIds.length) {
    ctx.kb_id = kbIds[0]
    ctx.kb_ids = kbIds
  }

  const agentIds = valuesOf(chips, 'agent')
  if (agentIds.length) {
    ctx.agent_id = agentIds[0]
    ctx.agent_ids = agentIds
  }

  const workflowIds = valuesOf(chips, 'workflow')
  if (workflowIds.length) {
    ctx.workflow_id = workflowIds[0]
    ctx.workflow_ids = workflowIds
  }

  // 技能本来就是多选语义，只有一个字段
  const skillNames = valuesOf(chips, 'skill')
  if (skillNames.length) ctx.skill_names = skillNames

  return Object.keys(ctx).length ? ctx : undefined
}
