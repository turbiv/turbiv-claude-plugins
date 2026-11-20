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
  await $.session.start({ cwd: '/', surface: 'desktop', isInteractive: true })
}

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

  expect(during).toMatch(/question mark.*Waiting for your answer/)
})
