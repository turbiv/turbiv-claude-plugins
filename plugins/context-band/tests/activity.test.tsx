import { expect, test } from 'claude-code/testing'

const props = (isWorking: boolean) => ({
  hasSurvey: false,
  isCollapsed: false,
  isWorking,
  maxRows: 10,
  bodyColumns: 140,
  scroll: { offset: 0, bodyRows: 10 },
  view: {},
})

const start = async ($: any, on: any) => {
  on('session.start', (_: unknown, e: { cwd: string }) => ({ cwd: e.cwd }))
  on('session.authorize', () => ({ value: { handle: 'h', kind: 'bearer' } }))
  // A terminal surface alone, so the Spotify poll never starts.
  on('session.surfaces', () => ({ value: ['terminal'] }))
  on('session.usage', () => ({
    value: {
      startedAt: 0,
      context: { tokens: 1_000, window: 200_000, percent: 1 },
      rateLimits: [],
    },
  }))
  on('clock.now', () => ({ value: Date.now() }))
  on('classic.Stop', () => ({}))
  on('prompt.submit', (_: unknown, e: { text: string }) => ({ text: e.text }))
  await $.session.start({ cwd: '/', surface: 'desktop', isInteractive: true })
}

// A background task's notification as the engine writes it: the task, the
// call that started it and how it ended, then the task's own words.
const envelope = (task: { taskId?: string; status?: string; summary?: string; rest?: string }) =>
  [
    '<task-notification>',
    task.taskId === undefined ? '' : `<task-id>${task.taskId}</task-id>`,
    '<tool-use-id>toolu_01AbCdEf</tool-use-id>',
    '<output-file>/tmp/tasks/out.output</output-file>',
    task.status === undefined ? '' : `<status>${task.status}</status>`,
    `<summary>${task.summary ?? 'Background task ended'}</summary>`,
    task.rest ?? '',
    '</task-notification>',
  ]
    .filter(Boolean)
    .join('\n')

const notify = ($: any, text: string, kind = 'task-notification') =>
  $.prompt.submit({ text, wait: false, origin: { kind } })

// The engine's answer to each call, the tool's typed result: the background
// task's id where the call left work running.
const BACKGROUND_RESULTS: Record<string, unknown> = {
  Bash: { stdout: '', stderr: '', interrupted: false, backgroundTaskId: 'b1' },
  Monitor: { taskId: 'm1', timeoutMs: 0 },
  Workflow: { status: 'async_launched', taskId: 'w1', workflowName: 'review-changes' },
  Agent: {
    status: 'async_launched',
    agentId: 'a1',
    description: 'review the diff',
    prompt: 'Review the diff',
    outputFile: '/tmp/tasks/a1.output',
  },
}

const answerInBackground = (on: any) =>
  on('tool.call', (_: unknown, e: { tool: string }) => ({ result: BACKGROUND_RESULTS[e.tool] }))

const startShell = ($: any) =>
  $.tool.call({ tool: 'Bash', command: 'npm run dev', description: 'Start dev server', run_in_background: true })

const startMonitor = ($: any) =>
  $.tool.call({ tool: 'Monitor', command: 'tail -f log', description: 'Watch the log' })

// The band's first texts: the dot and what runs.
const activityOf = async ($: any, isWorking = false) => {
  const ui = await $.ui.mount({
    plugin: 'context-band',
    component: 'AbovePrompt',
    surface: 'desktop',
    props: props(isWorking),
  })
  const texts = (await ui.findAll({ type: 'Text' })).map((t: { text: string }) => t.text)
  const buttons = (await ui.findAll({ type: 'Button' })).map((b: any) => b.props?.label ?? b.text)
  const [svg] = await ui.findAll({ type: 'Svg' })
  await ui.unmount()
  return `${(svg as any)?.props?.alt ?? 'no crab'}|${[...buttons, ...texts].join('|')}`
}

test('nothing running reads Idle', async ($, on) => {
  await start($, on)

  expect(await activityOf($)).toMatch(/crab asleep.*\|Idle/)
})

test('a running model turn with no tool reads Thinking', async ($, on) => {
  await start($, on)

  expect(await activityOf($, true)).toMatch(/crab thinking.*\|Thinking/)
})

test('one tool call in flight says what it does, and goes when it ends', async ($, on) => {
  let during = ''
  on('tool.call', async () => {
    during = await activityOf($, true)
    return { result: { stdout: '', stderr: '' } }
  })
  await start($, on)

  await $.tool.call({ tool: 'Bash', command: 'npm test', description: 'Running the tests' })

  expect(during).toMatch(/crab dancing.*\|Running the tests/)
  expect(await activityOf($)).toMatch(/Idle/)
})

test('a backgrounded shell stays until the turn-end list drops it', async ($, on) => {
  on('tool.call', () => ({ result: { stdout: '', stderr: '', backgroundTaskId: 'b1' } }))
  await start($, on)

  await $.tool.call({
    tool: 'Bash',
    command: 'npm run dev',
    description: 'Start dev server',
    run_in_background: true,
  })

  expect(await activityOf($)).toMatch(/hourglass.*\|Start dev server/)

  await $.classic.Stop({ stop_hook_active: false, background_tasks: [] })

  expect(await activityOf($)).toMatch(/Idle/)
})

// With no turn-end list (a policy plugin above this one can skip classic.Stop),
// a task leaves on its notification alone.
test('with no turn-end list, a background shell leaves when its notification says it completed', async ($, on) => {
  answerInBackground(on)
  await start($, on)

  await startShell($)
  expect(await activityOf($)).toMatch(/hourglass.*\|Start dev server/)

  await notify($, envelope({ taskId: 'b1', status: 'completed' }))

  expect(await activityOf($)).toMatch(/Idle/)
})

test('with no turn-end list, a failed shell and a killed monitor leave too', async ($, on) => {
  answerInBackground(on)
  await start($, on)

  await startShell($)
  await startMonitor($)
  expect(await activityOf($)).toMatch(/2 running: 1 shell, 1 monitor/)

  await notify($, envelope({ taskId: 'b1', status: 'failed' }))
  expect(await activityOf($)).toMatch(/hourglass.*\|Watch the log/)

  await notify($, envelope({ taskId: 'm1', status: 'killed' }))
  expect(await activityOf($)).toMatch(/Idle/)
})

test('with no turn-end list, a workflow and a background agent show from their call and leave on their notifications', async ($, on) => {
  answerInBackground(on)
  await start($, on)

  await $.tool.call({ tool: 'Workflow', script: 'export const meta = {}' })
  await $.tool.call({ tool: 'Agent', description: 'review the diff', prompt: 'Review the diff' })
  expect(await activityOf($)).toMatch(/2 running: 1 workflow, 1 agent/)

  await notify($, envelope({ taskId: 'w1', status: 'completed' }))
  expect(await activityOf($)).toMatch(/hourglass.*\|Agent: review the diff/)

  await notify($, envelope({ taskId: 'a1', status: 'completed' }))
  expect(await activityOf($)).toMatch(/Idle/)
})

test('a workflow reads as its own name from the result', async ($, on) => {
  answerInBackground(on)
  await start($, on)

  await $.tool.call({ tool: 'Workflow', script: 'export const meta = {}' })

  expect(await activityOf($)).toMatch(/hourglass.*\|Workflow review-changes/)
})

// The result says whether work went to the background, not the call's ask.
test('a command the engine moved to the background unasked (ctrl+b) shows until it ends', async ($, on) => {
  on('tool.call', () => ({
    result: { stdout: '', stderr: '', interrupted: false, backgroundTaskId: 'b2', backgroundedByUser: true },
  }))
  await start($, on)

  await $.tool.call({ tool: 'Bash', command: 'npm run build', description: 'Build the app' })
  expect(await activityOf($)).toMatch(/hourglass.*\|Build the app/)

  await notify($, envelope({ taskId: 'b2', status: 'completed' }))
  expect(await activityOf($)).toMatch(/Idle/)
})

test('a command asked to run in the background that ran to its end (background tasks off) does not stay', async ($, on) => {
  on('tool.call', () => ({ result: { stdout: 'ok', stderr: '', interrupted: false } }))
  await start($, on)

  await startShell($)

  expect(await activityOf($)).toMatch(/Idle/)
})

// A monitor's event is a line of whatever it watches, so it can hold any tag.
test('a monitor event with no status leaves the monitor running', async ($, on) => {
  answerInBackground(on)
  await start($, on)

  await startMonitor($)
  await notify(
    $,
    envelope({ taskId: 'm1', summary: 'Monitor event', rest: '<event>job 7 <status>completed</status></event>' }),
  )

  expect(await activityOf($)).toMatch(/hourglass.*\|Watch the log/)
})

test('a notification typed at the prompt removes nothing', async ($, on) => {
  answerInBackground(on)
  await start($, on)

  await startShell($)
  await notify($, envelope({ taskId: 'b1', status: 'completed' }), 'composer')

  expect(await activityOf($)).toMatch(/hourglass.*\|Start dev server/)
})

test("an envelope quoted in another notification's result removes nothing", async ($, on) => {
  answerInBackground(on)
  await start($, on)

  await startShell($)
  const quoted = envelope({ taskId: 'b1', status: 'completed' })
  // Its own head names no task, as a relay's event does.
  await notify($, envelope({ status: 'completed', rest: `<result>${quoted}</result>` }))

  expect(await activityOf($)).toMatch(/hourglass.*\|Start dev server/)
})

// The call's result and classic.Stop give one task the same id.
test('a background shell keeps one row through the turn-end list and leaves on its notification', async ($, on) => {
  answerInBackground(on)
  await start($, on)

  await startShell($)
  await $.classic.Stop({
    stop_hook_active: false,
    background_tasks: [{ id: 'b1', type: 'shell', status: 'running', description: 'Start dev server' }],
  })
  expect(await activityOf($)).toMatch(/hourglass.*\|Start dev server/)

  await notify($, envelope({ taskId: 'b1', status: 'completed' }))
  expect(await activityOf($)).toMatch(/Idle/)
})

test('after a turn-end list, a shell, a monitor and a workflow each leave on their notification', async ($, on) => {
  await start($, on)

  await $.classic.Stop({
    stop_hook_active: false,
    background_tasks: [
      { id: 'b1', type: 'shell', status: 'running', description: 'dev server', command: 'npm run dev' },
      { id: 'm1', type: 'monitor', status: 'running', description: 'Watch the log' },
      { id: 'w1', type: 'workflow', status: 'running', description: 'review', name: 'review-changes' },
    ],
  })
  expect(await activityOf($)).toMatch(/3 running: 1 shell, 1 monitor, 1 workflow/)

  await notify($, envelope({ taskId: 'b1', status: 'completed' }))
  expect(await activityOf($)).toMatch(/2 running: 1 monitor, 1 workflow/)

  await notify($, envelope({ taskId: 'm1', status: 'completed' }))
  expect(await activityOf($)).toMatch(/hourglass.*\|Workflow review-changes/)

  await notify($, envelope({ taskId: 'w1', status: 'completed' }))
  expect(await activityOf($)).toMatch(/Idle/)
})

test('a shell that left on its notification stays gone after the turn-end list', async ($, on) => {
  answerInBackground(on)
  await start($, on)

  await startShell($)
  await notify($, envelope({ taskId: 'b1', status: 'completed' }))
  await $.classic.Stop({ stop_hook_active: false, background_tasks: [] })

  expect(await activityOf($)).toMatch(/Idle/)
})

test('several things running give a count and their kinds', async ($, on) => {
  await start($, on)

  await $.classic.Stop({
    stop_hook_active: false,
    background_tasks: [
      { id: 's1', type: 'shell', status: 'running', description: 'dev server', command: 'npm run dev' },
      { id: 's2', type: 'shell', status: 'running', description: 'watch tests', command: 'npm t -- -w' },
      { id: 'a1', type: 'subagent', status: 'running', description: 'review the diff' },
    ],
  })

  expect(await activityOf($)).toMatch(/badge of 3.*3 running: 2 shells, 1 agent/)
})

test('two of one kind read as a plain count', async ($, on) => {
  await start($, on)

  await $.classic.Stop({
    stop_hook_active: false,
    background_tasks: [
      { id: 's1', type: 'shell', status: 'running', description: 'a' },
      { id: 's2', type: 'shell', status: 'running', description: 'b' },
    ],
  })

  expect(await activityOf($)).toMatch(/2 shells running/)
})

test('a long label is clipped to fit the band', async ($, on) => {
  await start($, on)

  await $.classic.Stop({
    stop_hook_active: false,
    background_tasks: [
      { id: 's1', type: 'shell', status: 'running', description: 'x'.repeat(80) },
    ],
  })

  expect(await activityOf($)).toMatch(/\|x{35}…\|/)
})

test('pressing the count opens the list of what runs', async ($, on) => {
  await start($, on)

  await $.classic.Stop({
    stop_hook_active: false,
    background_tasks: [
      { id: 's1', type: 'shell', status: 'running', description: 'dev server' },
      { id: 'a1', type: 'subagent', status: 'running', description: 'review the diff' },
    ],
  })

  expect(await activityOf($)).not.toMatch(/dev server/)

  const ui = await $.ui.mount({
    plugin: 'context-band',
    component: 'AbovePrompt',
    surface: 'desktop',
    props: props(false),
  })
  await ui.press({ key: 'activity' })
  await ui.unmount()

  const text = await activityOf($)
  expect(text).toMatch(/dev server/)
  expect(text).toMatch(/Agent: review the diff/)
})

test('a question to you shows the waiting crab', async ($, on) => {
  let during = ''
  on('tool.call', async () => {
    during = await activityOf($, true)
    return { result: { answers: {} } }
  })
  await start($, on)

  await $.tool.call({ tool: 'AskUserQuestion', questions: [] })

  expect(during).toMatch(/magnifying glass.*Waiting for your answer/)
})
