import { describe, it, expect } from 'vitest'
import { splitThinking } from '../chat-types'

// 回归保护：引擎（python-engine/app/agent/runtime.py）按 ~80 字一段下发
// "[thinking]片段[/thinking]"，因此流式 buffer 与落库文本都会出现多段思考块。
// 旧 loose 实现用「配对提取 + 孤立标签剥离」，非 loose 实现只看开头，
// 两者在第二段起都会把 "[/thinking][thinking]" 残留在正文里。
describe('splitThinking（loose 状态机）', () => {
  it('多段思考块全部归 reasoning，正文不残留标签', () => {
    const { reasoning, body } = splitThinking('[thinking]想a[/thinking][thinking]想b[/thinking]最终回答', { loose: true })
    expect(reasoning).toBe('想a想b')
    expect(body).toBe('最终回答')
    expect(body).not.toContain('thinking')
  })

  it('末段未闭合时仍算 reasoning（流式中）', () => {
    const { reasoning, body } = splitThinking('[thinking]想a[/thinking][thinking]还在想', { loose: true })
    expect(reasoning).toBe('想a还在想')
    expect(body).toBe('')
  })

  it('纯正文原样返回', () => {
    const { reasoning, body } = splitThinking('只有正文', { loose: true })
    expect(reasoning).toBe('')
    expect(body).toBe('只有正文')
  })

  it('思考块之间/之后无正文时不产生空正文项', () => {
    const { reasoning, body } = splitThinking('[thinking]a[/thinking][thinking]b[/thinking]', { loose: true })
    expect(reasoning).toBe('ab')
    expect(body).toBe('')
  })

  it('非 loose 保持原语义（仅解析开头思考块）', () => {
    const closed = splitThinking('[thinking]想一下[/thinking]回答')
    expect(closed.reasoning).toBe('想一下')
    expect(closed.body).toBe('回答')

    const open = splitThinking('[thinking]还在想')
    expect(open.reasoning).toBe('还在想')
    expect(open.body).toBe('')

    const plain = splitThinking('正文里提到 [thinking] 标签的写法')
    expect(plain.reasoning).toBe('')
    expect(plain.body).toBe('正文里提到 [thinking] 标签的写法')
  })
})
