/**
 * 把一次对话沉淀成可复用的工作流图定义。
 *
 * 产物直接对接 `POST /v1/graphs`（graph_json 存进 workflow_graphs，再由
 * `POST /v1/graphs/{id}/execute` 或 queue worker 执行）。执行器读的是
 * `node.node_type` 与 `node.config`（见 python-engine/app/workflow/engine.py）：
 * llm 节点认 `system_prompt` / `user_message`（兼容 `prompt`）/ `model`，
 * 所以这里把整段对话正文喂进 `user_message`。
 *
 * 为什么是单节点：对话本身不是 DAG，硬拆成节点链等于替用户猜"哪句是条件、
 * 哪步是工具"。先做到"这段对话可以被重复执行"，节点粒度留给用户在 DAG 编辑器里调。
 */

import type { ChatItem, TextItem } from '../components/chat/chat-types'
import { sessionToMarkdown } from './sessionMarkdown'

/** 后端 graph_json 的节点形态（与 `WorkflowView.toBackendFormat` 一致） */
export interface GraphNodeBackend {
  id: string
  label: string
  node_type: string
  config: Record<string, unknown>
}

export interface GraphDefinition {
  name: string
  nodes: GraphNodeBackend[]
  edges: unknown[]
  entry_point: string
}

/** 单节点固定 id：没有连线，入口就是它自己 */
const SOLE_NODE_ID = 'n1'

/** 给 llm 节点的 system_prompt —— 交代这段正文的来历，而不是让它当普通提问回答 */
const GRAPH_SYSTEM_PROMPT = '下面是此前的一段对话记录。请把它当作背景，在此基础上继续完成其中的工作。'

export interface SessionGraph {
  name: string
  graph_json: GraphDefinition
}

/**
 * 会话 → 工作流图。正文为空时返回 null，调用方据此禁用入口。
 *
 * 不能只看 `sessionToMarkdown` 的返回值来判断空：它带上标题后，即使一条正文都没有
 * 也会返回 `# 标题`（非空），那样会产出一个只有标题的空壳工作流。所以这里单独查正文。
 */
export function sessionToGraph(items: readonly ChatItem[], title?: string): SessionGraph | null {
  const hasBody = items.some(
    item => item.kind === 'text' && String((item as TextItem).content ?? '').trim().length > 0,
  )
  if (!hasBody) return null

  const markdown = sessionToMarkdown(items, title)
  const name = (title || '').trim() || `对话工作流 ${new Date().toLocaleString()}`
  return {
    name,
    graph_json: {
      name,
      nodes: [
        {
          id: SOLE_NODE_ID,
          label: name,
          node_type: 'llm',
          config: {
            system_prompt: GRAPH_SYSTEM_PROMPT,
            user_message: markdown,
            model: '',
          },
        },
      ],
      edges: [],
      entry_point: SOLE_NODE_ID,
    },
  }
}
