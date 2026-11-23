import { expect, test } from 'claude-code/testing'

const BAND = {
  plugin: 'context-band',
  component: 'AbovePrompt',
  surface: 'desktop',
  props: {
    hasSurvey: false,
    isCollapsed: false,
    isWorking: false,
    maxRows: 10,
    bodyColumns: 140,
    scroll: { offset: 0, bodyRows: 10 },
    view: {},
  },
} as const

const CONTEXT = { tokens: 50_000, window: 200_000, percent: 25 }
const IN_TWO_HOURS = new Date(Date.now() + 2 * 3_600_000)
const IN_THREE_DAYS = new Date(Date.now() + 3 * 86_400_000)
const hhmm = (d: Date) =>
  `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

// The session starts with $1.50 already spent, as a resumed one does, so a
// response of this run is the one that adds to it.
const start = async ($: any, on: any, kind: 'bearer' | 'api-key') => {
  on('session.start', (_: unknown, e: { cwd: string }) => ({ cwd: e.cwd }))
  on('session.authorize', () => ({ value: { handle: 'h', kind } }))
  // A terminal surface alone, so the Spotify poll never starts.
  on('session.surfaces', () => ({ value: ['terminal'] }))
  on('session.usage', () => ({
    value: { startedAt: 0, context: CONTEXT, rateLimits: [], cost: { usd: 1.5 } },
  }))
  on('session.measure', (_: unknown, e: { changed: string[] }) => ({ changed: e.changed }))
  on('clock.now', () => ({ value: Date.now() }))
  await $.session.start({ cwd: '/', surface: 'desktop', isInteractive: true })
}

const PLAN_LIMITS = [
  { kind: 'five_hour', percentUsed: 42, resetsAt: IN_TWO_HOURS.toISOString() },
  { kind: 'seven_day', percentUsed: 9, resetsAt: IN_THREE_DAYS.toISOString() },
]

const textOf = async ($: any) => {
  const ui = await $.ui.mount(BAND)
  const texts = (await ui.findAll({ type: 'Text' })).map((t: { text: string }) => t.text)
  await ui.unmount()
  return texts.join('|')
}

test('a claude.ai login shows neither plan windows nor dollars before its first response', async ($, on) => {
  await start($, on, 'bearer')
  const text = await textOf($)

  expect(text).not.toMatch(/5h/)
  expect(text).not.toMatch(/7d/)
  expect(text).not.toMatch(/\$/)
})

test('a reading with no new cost is not yet a response', async ($, on) => {
  await start($, on, 'bearer')
  await $.session.measure({ context: CONTEXT, rateLimits: [], cost: { usd: 1.5 }, changed: ['context'] })
  const text = await textOf($)

  expect(text).not.toMatch(/5h/)
  expect(text).not.toMatch(/\$/)
})

test('a Max session shows each window with its reset', async ($, on) => {
  await start($, on, 'bearer')
  await $.session.measure({
    context: CONTEXT,
    rateLimits: PLAN_LIMITS,
    cost: { usd: 3.25 },
    changed: ['rateLimits', 'cost'],
  })
  const text = await textOf($)

  expect(text).toMatch(/42%/)
  // The 5h reset as a clock time alone, the 7d one with its weekday.
  expect(text).toContain(`42%| ↻ ${hhmm(IN_TWO_HOURS)}|`)
  expect(text).toContain(`↻ ${DAYS[IN_THREE_DAYS.getDay()]} ${hhmm(IN_THREE_DAYS)}`)
  expect(text).toMatch(/9%/)
  expect(text).not.toMatch(/\$3\.25/)
})

test('a subscription that reports only the 5h window shows 7d as a dash', async ($, on) => {
  await start($, on, 'bearer')
  await $.session.measure({
    context: CONTEXT,
    rateLimits: [PLAN_LIMITS[0]],
    cost: { usd: 3.25 },
    changed: ['rateLimits', 'cost'],
  })
  const text = await textOf($)

  expect(text).toMatch(/42%/)
  expect(text).toMatch(/7d \|–/)
  expect(text).not.toMatch(/\$/)
})

test('a subscription stays one when a later reading has no windows', async ($, on) => {
  await start($, on, 'bearer')
  await $.session.measure({ context: CONTEXT, rateLimits: PLAN_LIMITS, cost: { usd: 3.25 }, changed: ['rateLimits', 'cost'] })
  await $.session.measure({ context: CONTEXT, rateLimits: [], cost: { usd: 4 }, changed: ['rateLimits', 'cost'] })
  const text = await textOf($)

  expect(text).toMatch(/5h/)
  expect(text).not.toMatch(/\$4\.00/)
})

test('a usage-billed claude.ai seat shows dollars and no plan windows after a response', async ($, on) => {
  await start($, on, 'bearer')
  await $.session.measure({ context: CONTEXT, rateLimits: [], cost: { usd: 3.25 }, changed: ['context', 'cost'] })
  const text = await textOf($)

  expect(text).toMatch(/\$3\.25/)
  expect(text).not.toMatch(/5h/)
  expect(text).not.toMatch(/7d/)
})

test('a usage-billed seat behind a gateway shows its spend limit and dollars', async ($, on) => {
  await start($, on, 'bearer')
  await $.session.measure({
    context: CONTEXT,
    rateLimits: [{ kind: 'spend_limit', percentUsed: 30 }],
    cost: { usd: 1.5 },
    changed: ['rateLimits'],
  })
  const text = await textOf($)

  expect(text).toMatch(/spend /)
  expect(text).toMatch(/30%/)
  expect(text).toMatch(/\$1\.50/)
  expect(text).not.toMatch(/5h/)
})

test('an API key shows dollars and no plan windows from the start', async ($, on) => {
  await start($, on, 'api-key')
  const text = await textOf($)

  expect(text).toMatch(/\$1\.50/)
  expect(text).not.toMatch(/5h/)
})
