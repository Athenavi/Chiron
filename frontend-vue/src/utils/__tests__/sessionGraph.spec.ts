import { describe, expect, it } from 'vitest'
import { sessionToGraph } from '../sessionGraph'
import type { ChatItem } from '../../components/chat/chat-types'

const text = (role: 'user' | 'assistant', content: string): ChatItem =>
  ({ kind: 'text', role, content } as ChatItem)
const other = (kind: string): ChatItem => ({ kind } as ChatItem)

const conversation = () => [
  text('user', '把这份报表汇总成周报'),
  text('assistant', '已汇总，见附件'),
]

describe('sessionToGraph（对话沉淀为工作流）', () => {
  it('产出一个 llm 单节点，正文进入 user_message', () => {
    const result = sessionToGraph(conversation(), '周报整理')
    expect(result).not.toBeNull()
    const node = result!.graph_json.nodes[0]
    expect(result!.graph_json.nodes).toHaveLength(1)
    expect(node.node_type).toBe('llm')
    expect(String(node.config.user_message)).toContain('把这份报表汇总成周报')
    expect(String(node.config.user_message)).toContain('已汇总，见附件')
  })

  it('入口指向唯一节点，且没有连线', () => {
    const graph = sessionToGraph(conversation(), '周报整理')!.graph_json
    expect(graph.entry_point).toBe(graph.nodes[0].id)
    expect(graph.edges).toEqual([])
  })

  it('图名与节点标签都用会话标题', () => {
    const result = sessionToGraph(conversation(), '  周报整理  ')!
    expect(result.name).toBe('周报整理')
    expect(result.graph_json.name).toBe('周报整理')
    expect(result.graph_json.nodes[0].label).toBe('周报整理')
  })

  it('没有标题时用兜底名字（不产出空名）', () => {
    const result = sessionToGraph(conversation())!
    expect(result.name.trim().length).toBeGreaterThan(0)
    expect(result.graph_json.nodes[0].label).toBe(result.name)
  })

  it('跳过思考与工具卡片（只沉淀正文）', () => {
    const result = sessionToGraph([text('user', '问题'), other('reasoning'), other('tool_call')], 'T')!
    const body = String(result.graph_json.nodes[0].config.user_message)
    expect(body).toContain('问题')
    expect(body).not.toContain('reasoning')
    expect(body).not.toContain('tool_call')
  })

  it('正文为空时返回 null（调用方据此禁用入口）', () => {
    expect(sessionToGraph([], 'T')).toBeNull()
    expect(sessionToGraph([other('reasoning')], 'T')).toBeNull()
    expect(sessionToGraph([text('user', '   ')], 'T')).toBeNull()
  })

  it('system_prompt 交代正文来历，不空着', () => {
    const config = sessionToGraph(conversation(), 'T')!.graph_json.nodes[0].config
    expect(typeof config.system_prompt).toBe('string')
    expect(String(config.system_prompt).trim().length).toBeGreaterThan(0)
  })
})

describe('sessionToGraph 继承对话知识库', () => {
  const KB = 'kb-123'

  it('挂了知识库时生成 input → knowledge → llm 三点链', () => {
    const graph = sessionToGraph(conversation(), '周报整理', { kbId: KB })!.graph_json
    expect(graph.nodes.map(n => n.node_type)).toEqual(['input', 'knowledge', 'llm'])
    expect(graph.edges).toEqual([
      { source_id: 'n_input', target_id: 'n_kb' },
      { source_id: 'n_kb', target_id: 'n1' },
    ])
  })

  it('入口指向 input 节点（否则整条链不会从用户输入开始）', () => {
    const graph = sessionToGraph(conversation(), 'T', { kbId: KB })!.graph_json
    const inputNode = graph.nodes.find(n => n.node_type === 'input')!
    expect(graph.entry_point).toBe(inputNode.id)
  })

  it('knowledge 的 kb_id 与留空的 query（引擎据此回退到上游输入）', () => {
    const graph = sessionToGraph(conversation(), 'T', { kbId: KB })!.graph_json
    const kb = graph.nodes.find(n => n.node_type === 'knowledge')!
    expect(kb.config.kb_id).toBe(KB)
    // 留空是契约：engine.py 的 _knowledge_node 会落到 _prev_output（运行时输入）
    expect(kb.config.query).toBe('')
  })

  it('llm 的 user_message 留空、正文挪进 system_prompt', () => {
    const graph = sessionToGraph(conversation(), 'T', { kbId: KB })!.graph_json
    const llm = graph.nodes.find(n => n.node_type === 'llm')!
    // user_message 的位置让给了检索片段，正文不挪走就会丢
    expect(llm.config.user_message).toBe('')
    expect(String(llm.config.system_prompt)).toContain('把这份报表汇总成周报')
  })

  it('不把 kb_id 塞进 llm 节点（引擎根本不读那个键）', () => {
    const graph = sessionToGraph(conversation(), 'T', { kbId: KB })!.graph_json
    const llm = graph.nodes.find(n => n.node_type === 'llm')!
    expect(llm.config.kb_id).toBeUndefined()
  })

  it('kbId 缺省或空白时保持单节点旧行为', () => {
    for (const options of [undefined, {}, { kbId: '' }, { kbId: '   ' }]) {
      const graph = sessionToGraph(conversation(), 'T', options)!.graph_json
      expect(graph.nodes).toHaveLength(1)
      expect(graph.nodes[0].node_type).toBe('llm')
      expect(graph.edges).toEqual([])
    }
  })
})
