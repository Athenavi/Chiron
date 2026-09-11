import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import MessageItem from '../MessageItem.vue'
import type { ChatItem } from '../chat-types'

const assistant = (content: string): ChatItem => ({ kind: 'text', role: 'assistant', content, id: 'm1' })

const mountText = (content: string) => mount(MessageItem, { props: { item: assistant(content) } })

describe('MessageItem（正文链接处理）', () => {
  it('外部链接改为新窗口打开，并带上 noopener', () => {
    const wrapper = mountText('见 [文档](https://example.com/docs)')
    const link = wrapper.find('.msg-text a')
    expect(link.attributes('href')).toBe('https://example.com/docs')
    expect(link.attributes('target')).toBe('_blank')
    expect(link.attributes('rel')).toContain('noopener')
  })

  it('站内相对链接保持原行为（不加 target，交给应用自身导航）', () => {
    const wrapper = mountText('见 [文件](/v1/media/abc/download)')
    const link = wrapper.find('.msg-text a')
    expect(link.attributes('href')).toBe('/v1/media/abc/download')
    expect(link.attributes('target')).toBeUndefined()
  })

  it('裸链接（linkify）同样走外开规则', () => {
    const wrapper = mountText('参考 https://example.org/guide 这一节')
    const link = wrapper.find('.msg-text a')
    expect(link.attributes('target')).toBe('_blank')
  })
})

describe('MessageItem（消息操作）', () => {
  it('可以把整条消息引用到输入框', async () => {
    const wrapper = mountText('一段较长的回复正文')
    await wrapper.find('[title="引用到输入框"]').trigger('click')
    expect(wrapper.emitted('quote')?.[0]?.[0]).toBe('一段较长的回复正文')
  })

  it('流式中的消息不提供引用（内容还在变）', () => {
    const wrapper = mount(MessageItem, {
      props: { item: { kind: 'text', role: 'assistant', content: '半截', id: 'm2', streaming: true } },
    })
    expect(wrapper.find('[title="引用到输入框"]').exists()).toBe(false)
  })
})
