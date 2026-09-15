import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import ToolResultBlock from '../ToolResultBlock.vue'
import type { ToolResultItem } from '../chat-types'

const item = (content: string, isError = false): ToolResultItem =>
  ({ kind: 'tool_result', toolCallId: 'c1', content, isError })

/** 与 edit_file 的 difflib 输出形态一致（python-engine/app/tools/edit_file.py） */
const DIFF = [
  '--- a/app/main.py',
  '+++ b/app/main.py',
  '@@ -1,2 +1,2 @@',
  ' context',
  '-old',
  '+new',
  '',
].join('\n')

describe('ToolResultBlock（工具结果富渲染）', () => {
  it('edit_file 的 diff 结果按 diff 渲染，并给出增删统计与文件路径', () => {
    const wrapper = mount(ToolResultBlock, {
      props: { item: item(JSON.stringify({ path: '/w/app/main.py', success: true, diff: DIFF })) },
    })
    expect(wrapper.findAll('.diff-line').length).toBe(6)
    expect(wrapper.find('.diff-add').text()).toBe('+1')
    expect(wrapper.find('.diff-del').text()).toBe('−1')
    expect(wrapper.text()).toContain('app/main.py')
    expect(wrapper.findAll('.diff-line.add').length).toBe(1)
    expect(wrapper.findAll('.diff-line.del').length).toBe(1)
    expect(wrapper.findAll('.diff-line.hunk').length).toBe(1)
  })

  it('纯文本里携带的 patch 同样按 diff 渲染', () => {
    const wrapper = mount(ToolResultBlock, { props: { item: item(DIFF) } })
    expect(wrapper.findAll('.diff-line').length).toBe(6)
  })

  it('超长 diff 先给预览，展开后显示全部', async () => {
    const big = ['--- a/x.ts', '+++ b/x.ts', '@@ -1 +1 @@']
      .concat(Array.from({ length: 100 }, (_, i) => `+line${i}`))
      .join('\n')
    const wrapper = mount(ToolResultBlock, { props: { item: item(big) } })
    expect(wrapper.findAll('.diff-line').length).toBe(60)
    expect(wrapper.find('.diff-more').text()).toContain('还有 43 行')
    await wrapper.find('.diff-more').trigger('click')
    expect(wrapper.findAll('.diff-line').length).toBe(103)
  })

  it('失败结果显式标注错误并默认展开内容', () => {
    const wrapper = mount(ToolResultBlock, { props: { item: item('{"error":"boom"}', true) } })
    expect(wrapper.find('.result-error-bar').exists()).toBe(true)
    expect(wrapper.find('.result-code').exists()).toBe(true)
    expect(wrapper.text()).toContain('结果（失败）')
  })

  it('成功结果的文本默认收起', () => {
    const wrapper = mount(ToolResultBlock, { props: { item: item('{"a":1}') } })
    expect(wrapper.find('.result-error-bar').exists()).toBe(false)
    expect(wrapper.find('.result-code').exists()).toBe(false)
  })

  it('终端输出显示退出码与行数，非零退出码标红', () => {
    const wrapper = mount(ToolResultBlock, {
      props: { item: item(JSON.stringify({ stdout: 'a\nb\n', stderr: '', exit_code: 1 })) },
    })
    expect(wrapper.text()).toContain('exit 1')
    expect(wrapper.find('.terminal-exit').classes()).toContain('nonzero')
    expect(wrapper.find('.terminal-lines').text()).toBe('3 行')
  })
})
