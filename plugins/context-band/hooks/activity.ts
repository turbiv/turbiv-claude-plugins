import { atom, update } from 'claude-code'
import type { EngineInterface, On, ToolResultOf } from 'claude-code'

import type { Activity, ActivityItem, ActivityKind } from '../types'
import { wake } from './awake'

// What the session has running: the main loop's tool calls in flight, and the
// background work (shells, subagents, monitors, workflows) that outlives them.
// The band reads it with the turn's own isWorking to say "Thinking" when the
// model runs with no tool in flight.
const activity = atom({ plugin: 'context-band', key: 'activity' } as const, {
  tools: [],
  background: [],
})

const LABEL_MAX_CHARS = 36

type Args = Record<string, unknown>

const text = (value: unknown): string => (typeof value === 'string' ? value.trim() : '')

const firstLine = (value: string): string => value.split('\n')[0]?.trim() ?? ''

const basename = (path: string): string => path.split('/').filter(Boolean).pop() ?? path

const hostOf = (url: string): string => {
  const match = /^[a-z]+:\/\/([^/]+)/i.exec(url)

  return match?.[1] ?? url
}

export const clipLabel = (label: string, max = LABEL_MAX_CHARS): string =>
  label.length > max ? `${label.slice(0, max - 1)}…` : label

// A few words for one tool call, from its own arguments.
export const toolLabel = (tool: string, args: Args): string => {
  const description = text(args.description)

  switch (tool) {
    case 'Bash':
      return description || firstLine(text(args.command)) || 'Running a command'
    case 'Agent':
    case 'Task':
      return description ? `Agent: ${description}` : 'Running an agent'
    case 'Read':
      return `Reading ${basename(text(args.file_path))}`
    case 'Edit':
    case 'MultiEdit':
    case 'NotebookEdit':
      return `Editing ${basename(text(args.file_path) || text(args.notebook_path))}`
    case 'Write':
      return `Writing ${basename(text(args.file_path))}`
    case 'Grep':
      return `Searching ${text(args.pattern)}`
    case 'Glob':
      return `Finding ${text(args.pattern)}`
    case 'WebSearch':
      return `Web search: ${text(args.query)}`
    case 'WebFetch':
      return `Fetching ${hostOf(text(args.url))}`
    case 'Skill':
      return `Skill ${text(args.skill)}`
    case 'Monitor':
      return description || 'Monitoring'
    case 'Workflow':
      return `Workflow ${text(args.name) || ''}`.trim()
    case 'AskUserQuestion':
      return 'Waiting for your answer'
    default: {
      // mcp__<server>__<tool>: the server and the tool, minus the prefix.
      const mcp = /^mcp__(.+?)__(.+)$/.exec(tool)

      if (mcp?.[1] !== undefined && mcp[2] !== undefined) {
        return `${mcp[1]}: ${mcp[2].replace(/_/g, ' ')}`
      }

      return description || tool
    }
  }
}

const nonEmpty = (value: unknown): string | undefined =>
  typeof value === 'string' && value !== '' ? value : undefined

type AgentLaunch = Extract<ToolResultOf<'Agent'>, { status: 'async_launched' | 'remote_launched' }>

// The engine's id for the work a call left running, read from the call's own
// result, never from its arguments: the engine can background a command the
// call did not ask for (ctrl+b, a turn abort) and refuse one it did (background
// tasks disabled). It is the id classic.Stop lists and the task's notification
// names; undefined for a call that ran to its end.
export const backgroundTaskOf = (tool: string, result: unknown): string | undefined => {
  if (typeof result !== 'object' || result === null) return undefined

  switch (tool) {
    case 'Bash':
      return nonEmpty((result as Partial<ToolResultOf<'Bash'>>).backgroundTaskId)
    case 'Monitor':
      return nonEmpty((result as Partial<ToolResultOf<'Monitor'>>).taskId)
    case 'Workflow':
      return nonEmpty((result as Partial<ToolResultOf<'Workflow'>>).taskId)
    case 'Agent':
    case 'Task': {
      const agent = result as Partial<AgentLaunch>

      if (agent.status === 'async_launched') return nonEmpty(agent.agentId)
      if (agent.status === 'remote_launched') return nonEmpty(agent.taskId)

      return undefined
    }
    default:
      return undefined
  }
}

// A workflow's name is its script's own (`meta.name`), which only the result
// carries; the call's arguments name a saved workflow alone.
const backgroundLabel = (tool: string, args: Args, result: unknown): string => {
  const name = tool === 'Workflow' ? text((result as Partial<ToolResultOf<'Workflow'>>).workflowName) : ''

  return name ? `Workflow ${name}` : toolLabel(tool, args)
}

const kindOfCall = (tool: string): ActivityKind => {
  if (tool === 'Bash') return 'shell'
  if (tool === 'Agent' || tool === 'Task') return 'agent'
  if (tool === 'Monitor') return 'monitor'
  if (tool === 'Workflow') return 'workflow'

  return 'task'
}

type BackgroundSummary = {
  id: string
  type: string
  description: string
  command?: string
  agent_type?: string
  tool?: string
  name?: string
}

const kindOfTask = (type: string): ActivityKind => {
  if (type === 'shell') return 'shell'
  if (type === 'subagent') return 'agent'
  if (type === 'monitor') return 'monitor'
  if (type === 'workflow') return 'workflow'

  return 'task'
}

export const fromSummary = (task: BackgroundSummary): ActivityItem => {
  const kind = kindOfTask(task.type)
  const description = firstLine(text(task.description))
  const label =
    kind === 'shell'
      ? description || firstLine(text(task.command))
      : kind === 'workflow'
        ? `Workflow ${text(task.name) || description}`.trim()
        : kind === 'agent'
          ? `Agent: ${description || text(task.agent_type)}`
          : description || text(task.tool) || task.type

  return { id: task.id, kind, label: label || task.type }
}

// The task a notification says has ended: the engine's task id, and how it
// ended (`completed`, `failed`, `killed`, `stopped`).
export type TaskEnd = { taskId: string; status: string }

const ENVELOPE_OPEN = '<task-notification>'

// The engine hands hooks a notification's text alone (the parsed form is the
// transcript row's, a drawing's), so its envelope is read here. Only its head
// counts: the fields the engine writes before the task's own words
// (`<summary>`, `<result>`, `<event>`, `<note>`), which can quote another
// envelope. With no status (a monitor's event, an agent's note) the task still
// runs: undefined, as for a head this cannot read, so nothing is dropped then.
export const parseTaskEnd = (text: string): TaskEnd | undefined => {
  const start = text.indexOf(ENVELOPE_OPEN)

  if (start < 0) return undefined

  const body = text.slice(start + ENVELOPE_OPEN.length)
  const headEnd = body.search(/<(summary|result|event|note)>|<\/task-notification>/)
  const head = headEnd < 0 ? body : body.slice(0, headEnd)
  const field = (tag: string): string | undefined =>
    nonEmpty(new RegExp(`<${tag}>([^<]*)</${tag}>`).exec(head)?.[1]?.trim())

  const taskId = field('task-id')
  const status = field('status')

  return taskId !== undefined && status !== undefined ? { taskId, status } : undefined
}

const PLURALS: Record<ActivityKind, [string, string]> = {
  tool: ['tool', 'tools'],
  shell: ['shell', 'shells'],
  agent: ['agent', 'agents'],
  monitor: ['monitor', 'monitors'],
  workflow: ['workflow', 'workflows'],
  task: ['task', 'tasks'],
}

// "2 shells, 1 agent": the kinds of what runs, most first.
export const breakdown = (items: ActivityItem[]): string => {
  const counts = new Map<ActivityKind, number>()

  for (const item of items) {
    counts.set(item.kind, (counts.get(item.kind) ?? 0) + 1)
  }

  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1])
    .map(([kind, n]) => `${n} ${PLURALS[kind][n === 1 ? 0 : 1]}`)
    .join(', ')
}

// What the band says runs: the tools in flight, else "Thinking" while the
// model turn runs, then the background work.
export const runningItems = (state: Activity, isWorking: boolean): ActivityItem[] => {
  const foreground: ActivityItem[] =
    state.tools.length > 0
      ? state.tools
      : isWorking
        ? [{ id: 'turn', kind: 'tool', label: 'Thinking' }]
        : []

  return [...foreground, ...state.background]
}

// A reload starts the module over: the calls it was tracking are gone. Run
// from the band's own session.start hook.
export async function resetActivity($: EngineInterface): Promise<void> {
  await update($, activity, a => ({ ...a, tools: [] }))
}

export function hookActivity(on: On): void {
  on('tool.call', async ($, e, next) => {
    // A subagent's own calls: the Agent call that started it stands for them.
    if (e.agentId !== undefined) {
      return next(e)
    }

    const args = e as unknown as Args
    const item: ActivityItem = {
      id: e.tool_use_id,
      kind: 'tool',
      label: toolLabel(e.tool, args),
    }

    await update($, activity, a => ({ ...a, tools: [...a.tools, item] }))

    try {
      const result = await next(e)
      const taskId =
        result.deny === undefined && result.isError !== true
          ? backgroundTaskOf(e.tool, result.result)
          : undefined

      if (taskId !== undefined) {
        const moved: ActivityItem = {
          id: taskId,
          kind: kindOfCall(e.tool),
          label: backgroundLabel(e.tool, args, result.result),
        }
        await update($, activity, a => ({
          ...a,
          background: [...a.background.filter(b => b.id !== moved.id), moved],
        }))
      }

      return result
    } finally {
      await update($, activity, a => ({ ...a, tools: a.tools.filter(t => t.id !== item.id) }))
    }
  })

  // A background task that ends sends a notification, delivered as a prompt
  // whose origin the engine stamps, idle or into a running turn; the band drops
  // the task at once. It does not wait for classic.Stop below, which a policy
  // plugin above this one can skip. Text that only looks like a notification
  // (typed, pasted, a tool's output) has another origin.
  on('prompt.submit', async ($, e, next) => {
    const ended = e.origin.kind === 'task-notification' ? parseTaskEnd(e.text) : undefined

    if (ended !== undefined) {
      await update($, activity, a => ({
        ...a,
        background: a.background.filter(b => b.id !== ended.taskId),
      }))
    }

    return next(e)
  })

  // At the end of each main turn the engine lists the work still in flight:
  // that list, keyed by the same task ids, replaces what the hooks above kept.
  on('classic.Stop', async ($, e, next) => {
    const tasks = (e as { background_tasks?: BackgroundSummary[] }).background_tasks

    await update($, activity, a => ({
      tools: [],
      background: tasks === undefined ? a.background : tasks.map(fromSummary),
    }))

    return next(e)
  })

  on('turn.complete', async ($, e, next) => {
    const agentId = e.agentId

    await update($, activity, a =>
      agentId === undefined
        ? // An interrupted turn leaves no tool running.
          { ...a, tools: [] }
        : // A background subagent that ended its turn.
          { ...a, background: a.background.filter(b => b.id !== agentId) },
    )

    // Your turn: the crab stays awake while you type. A background subagent's
    // turn is not yours to answer.
    if (agentId === undefined) await wake($)

    return next(e)
  })
}
