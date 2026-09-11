import { describe, expect, it } from 'vitest'
import { buildWorkbenchContext, parseContextQuery, type ContextChip } from '../contextChips'

const chips = (...pairs: [ContextChip['type'], string][]): ContextChip[] =>
  pairs.map(([type, value]) => ({ type, label: value, value }))

describe('parseContextQuery（URL 约定）', () => {
  it('单值写法保持兼容（老链接不受影响）', () => {
    const parsed = parseContextQuery({ kb: 'kb-1', skill: 'pdf-tools' })
    expect(parsed.map(c => [c.type, c.value])).toEqual([['kb', 'kb-1'], ['skill', 'pdf-tools']])
  })

  it('同名参数可重复，逐个成为 chip（这是多选的关键）', () => {
    const parsed = parseContextQuery({ kb: ['kb-1', 'kb-2'], skill: ['a', 'b', 'c'] })
    expect(parsed.filter(c => c.type === 'kb').map(c => c.value)).toEqual(['kb-1', 'kb-2'])
    expect(parsed.filter(c => c.type === 'skill').map(c => c.value)).toEqual(['a', 'b', 'c'])
  })

  it('忽略空串、空白与非字符串（避免产出空 chip）', () => {
    expect(parseContextQuery({ kb: '', agent: '   ', workflow: 42 })).toEqual([])
    expect(parseContextQuery({ kb: ['', 'kb-1', '  '] }).map(c => c.value)).toEqual(['kb-1'])
  })

  it('没有 query 时不报错', () => {
    expect(parseContextQuery(null)).toEqual([])
    expect(parseContextQuery(undefined)).toEqual([])
    expect(parseContextQuery({})).toEqual([])
  })

  it('chip 带可读的占位标签（真实名称由调用方补全）', () => {
    const [kb] = parseContextQuery({ kb: 'abcdef1234567890' })
    expect(kb!.label).toContain('知识库')
    expect(kb!.label).toContain('abcdef12')
  })
})

describe('buildWorkbenchContext（发给引擎的形态）', () => {
  it('单值字段取首个，同时给出多值数组（新旧后端都能工作）', () => {
    const ctx = buildWorkbenchContext(chips(['kb', 'kb-1'], ['kb', 'kb-2']))
    expect(ctx).toEqual({ kb_id: 'kb-1', kb_ids: ['kb-1', 'kb-2'] })
  })

  it('四类上下文各自成字段，技能本来就是数组', () => {
    const ctx = buildWorkbenchContext(chips(
      ['kb', 'kb-1'], ['agent', 'ag-1'], ['workflow', 'wf-1'], ['skill', 'pdf'], ['skill', 'web'],
    ))
    expect(ctx).toEqual({
      kb_id: 'kb-1',
      kb_ids: ['kb-1'],
      agent_id: 'ag-1',
      agent_ids: ['ag-1'],
      workflow_id: 'wf-1',
      workflow_ids: ['wf-1'],
      skill_names: ['pdf', 'web'],
    })
  })

  it('同类重复值去重（URL 里手写重复不该变成两次检索）', () => {
    const ctx = buildWorkbenchContext(chips(['kb', 'kb-1'], ['kb', 'kb-1']))
    expect(ctx).toEqual({ kb_id: 'kb-1', kb_ids: ['kb-1'] })
  })

  it('没有上下文时返回 undefined（调用方据此不写 context 字段）', () => {
    expect(buildWorkbenchContext([])).toBeUndefined()
    expect(buildWorkbenchContext(chips(['kb', '']))).toBeUndefined()
  })
})
