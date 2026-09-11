import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'

vi.mock('../../api', () => ({
  uploadFile: vi.fn(),
  listModels: vi.fn(async () => []),
}))

import ChatInput from '../ChatInput.vue'

const HISTORY_KEY = 'chiron:composer-history:v1'

function mountInput(props: Record<string, unknown> = {}) {
  return mount(ChatInput, {
    props: { loading: false, mode: 'normal', modeOptions: [], sessionId: 's1', ...props } as any,
  })
}

const valueOf = (wrapper: ReturnType<typeof mountInput>) =>
  (wrapper.find('textarea').element as HTMLTextAreaElement).value

beforeEach(() => {
  localStorage.clear()
})

describe('ChatInput（输入区交互）', () => {
  it('↑ 召回最近发送的内容，↓ 越过最近一条后回到自己的草稿', async () => {
    const wrapper = mountInput()
    const ta = wrapper.find('textarea')

    await ta.setValue('第一个问题')
    await ta.trigger('keydown', { key: 'Enter' })
    expect(wrapper.emitted('send')?.[0]?.[0]).toBe('第一个问题')

    await ta.setValue('正在写一半的草稿')
    await ta.trigger('keydown', { key: 'ArrowUp' })
    expect(valueOf(wrapper)).toBe('第一个问题')

    await ta.trigger('keydown', { key: 'ArrowDown' })
    expect(valueOf(wrapper)).toBe('正在写一半的草稿')
  })

  it('Esc 放弃召回并恢复草稿', async () => {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(['历史内容']))
    const wrapper = mountInput()
    const ta = wrapper.find('textarea')

    await ta.setValue('我的草稿')
    await ta.trigger('keydown', { key: 'ArrowUp' })
    expect(valueOf(wrapper)).toBe('历史内容')

    await ta.trigger('keydown', { key: 'Escape' })
    expect(valueOf(wrapper)).toBe('我的草稿')
  })

  it('光标不在首行时 ↑ 不召回（留给光标移动）', async () => {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(['历史内容']))
    const wrapper = mountInput()
    const ta = wrapper.find('textarea')

    await ta.setValue('第一行\n第二行')
    await ta.trigger('keydown', { key: 'ArrowUp' })
    expect(valueOf(wrapper)).toBe('第一行\n第二行')
  })

  it('输入法组合期按 Enter 不发送（选词确认不该提交）', async () => {
    const wrapper = mountInput()
    const ta = wrapper.find('textarea')

    await ta.setValue('中文候选')
    await ta.trigger('keydown', { key: 'Enter', isComposing: true })
    expect(wrapper.emitted('send')).toBeUndefined()
  })

  it('发送后写入历史，重复内容只保留最近一条', async () => {
    const wrapper = mountInput()
    const ta = wrapper.find('textarea')

    for (const text of ['a', 'b', 'a']) {
      await ta.setValue(text)
      await ta.trigger('keydown', { key: 'Enter' })
    }
    expect(JSON.parse(localStorage.getItem(HISTORY_KEY) as string)).toEqual(['b', 'a'])
  })

  it('草稿按会话持久化并在切回时恢复', async () => {
    const wrapper = mountInput()
    const ta = wrapper.find('textarea')

    await ta.setValue('未发完的草稿')
    await new Promise(resolve => setTimeout(resolve, 350))   // 草稿写入有 300ms 防抖
    expect(localStorage.getItem('chiron:draft:s1')).toBe('未发完的草稿')

    await wrapper.setProps({ sessionId: 's2' })
    expect(valueOf(wrapper)).toBe('')

    await wrapper.setProps({ sessionId: 's1' })
    expect(valueOf(wrapper)).toBe('未发完的草稿')
  })
})
