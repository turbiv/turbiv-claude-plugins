import { expect, test } from 'claude-code/testing'

import { conductBar, crabAlt, crabSvg } from '../hooks/crab'
import {
  FRESH,
  LEVEL_FROM,
  MIN_ACTIVE_RATE,
  WINDOW_MS,
  accumulate,
  levelFor,
  nextBaseline,
  parseBaselines,
  rateOf,
  stepLevel,
} from '../hooks/pace'

test('the rate is the tokens of the last minute', () => {
  const events = [
    { at: 1_000, tokens: 500 },
    { at: 70_000, tokens: 300 },
    { at: 100_000, tokens: 200 },
  ]

  expect(rateOf(events, 100_000)).toBe(500)
  expect(rateOf(events, 100_000 + WINDOW_MS)).toBe(0)
  // A correction for an overestimate cannot make the rate negative.
  expect(rateOf([{ at: 10, tokens: -50 }], 20)).toBe(0)
})

test('a level begins at its ratio and is held until clearly under it', () => {
  expect(levelFor(1.4, 0)).toBe(0)
  expect(levelFor(1.5, 0)).toBe(1)
  expect(levelFor(2, 0)).toBe(2)
  expect(levelFor(3, 0)).toBe(3)
  expect(levelFor(4, 0)).toBe(4)
  expect(levelFor(99, 0)).toBe(4)

  // Just under 2x, held at hyped; well under, let go to busy.
  expect(levelFor(1.9, 2)).toBe(2)
  expect(levelFor(LEVEL_FROM[1] * 0.85, 2)).toBe(2)
  expect(levelFor(1.6, 2)).toBe(1)
})

test('the crab heats up at once and cools one level every few seconds', () => {
  let gait = { level: 0 as const, droppedAt: 0, coolUntil: 0 } as ReturnType<typeof stepLevel>

  gait = stepLevel(gait, 5, 1_000)
  expect(gait.level).toBe(4)

  // The rate is gone, yet the crab steps down one level at a time.
  gait = stepLevel(gait, 0, 10_000)
  expect(gait.level).toBe(3)
  gait = stepLevel(gait, 0, 11_000)
  expect(gait.level).toBe(3)
  gait = stepLevel(gait, 0, 13_000)
  expect(gait.level).toBe(2)
  expect(gait.coolUntil).toBe(0)

  // Down to busy from hyped: it pants for a few seconds.
  gait = stepLevel(gait, 0, 16_000)
  expect(gait.level).toBe(1)
  expect(gait.coolUntil).toBe(20_000)

  // Heating up again ends the panting.
  gait = stepLevel(gait, 5, 17_000)
  expect(gait.level).toBe(4)
  expect(gait.coolUntil).toBe(0)
})

test('the usual rate moves gently, and a burst does not become normal', () => {
  const first = nextBaseline(FRESH, 2_500)

  expect(first.avg).toBe(2_500)
  expect(first.n).toBe(FRESH.n + 1)

  // A huge minute counts as at most three times the usual rate, and weighs
  // little once many minutes stand behind it.
  const seasoned = { avg: 2_000, n: 100 }
  const burst = nextBaseline(seasoned, 90_000)

  expect(burst.avg).toBeGreaterThan(2_000)
  expect(burst.avg).toBeLessThan(2_000 + (6_000 - 2_000) * 0.06)
})

test('only active time teaches the usual rate, a minute at a time', () => {
  let active = { ms: 0, sum: 0 }
  let sample: number | null = null

  // Idle seconds teach nothing.
  expect(accumulate(active, MIN_ACTIVE_RATE - 1, 1_000)).toEqual({ active, sample: null })

  for (let second = 0; second < 59; second += 1) {
    const step = accumulate(active, 3_000, 1_000)

    active = step.active
    sample = step.sample
  }

  expect(sample).toBeNull()

  const last = accumulate(active, 3_000, 1_000)

  expect(last.sample).toBe(3_000)
  expect(last.active).toEqual({ ms: 0, sum: 0 })
})

test('what the store holds is read as data: only well-formed baselines stay', () => {
  expect(parseBaselines(undefined)).toEqual({})
  expect(parseBaselines([1, 2])).toEqual({})
  expect(
    parseBaselines({
      'claude-opus-5-5': { avg: 1_800, n: 12 },
      broken: { avg: 'x', n: 1 },
      zero: { avg: 0, n: 1 },
      missing: { n: 1 },
    }),
  ).toEqual({ 'claude-opus-5-5': { avg: 1_800, n: 12 } })
})

const count = (text: string, part: string): number => text.split(part).length - 1

test('every mood at every level draws a balanced SVG', () => {
  for (const mood of ['idle', 'ready', 'thinking', 'working', 'background', 'several', 'waiting'] as const) {
    for (const level of [0, 1, 2, 3, 4] as const) {
      for (const cooling of [false, true]) {
        const svg = crabSvg(mood, 3, level, cooling)

        expect(count(svg, '<g')).toBe(count(svg, '</g>'))
        expect(svg.startsWith('<svg')).toBe(true)
        expect(svg.endsWith('</svg>')).toBe(true)
      }
    }
  }
})

test('the calm crab is the crab it was, and levels show on every mood but sleep', () => {
  expect(crabSvg('working', 1)).toBe(crabSvg('working', 1, 0, false))
  expect(crabSvg('working', 1)).not.toMatch(/class="[^"]*fast/)

  // Asleep, the pace changes nothing.
  expect(crabSvg('idle', 1, 4, true)).toBe(crabSvg('idle', 1, 0, false))
  expect(crabAlt('idle', 1, 4, true)).toBe(crabAlt('idle', 1, 0, false))

  // Cranking the factory or waiting for an answer, the pace shows, but the
  // crab does not pant: that is for the moods that spend tokens themselves.
  for (const mood of ['background', 'waiting'] as const) {
    expect(crabSvg(mood, 1, 3, true)).toBe(crabSvg(mood, 1, 3, false))
    expect(crabSvg(mood, 1, 3)).not.toBe(crabSvg(mood, 1, 0))
  }

  expect(crabSvg('working', 1, 1)).toMatch(/class="working hm"/)
  expect(crabSvg('thinking', 1, 1)).toMatch(/class="thinking tap"/)
  expect(crabSvg('thinking', 1, 2)).toContain('class="gear"')
  expect(crabSvg('working', 1, 4)).toContain('class="wrap rb"')
  expect(crabSvg('working', 1, 3)).toContain('class="shake on"')
  expect(crabSvg('working', 1, 3)).not.toContain('class="wrap rb"')
  expect(crabSvg('working', 1, 4, true)).toMatch(/class="cool"/)
})

test('the background crab cranks a factory that shows money from hyped and burns it from frenzy', () => {
  for (const level of [0, 1, 2, 3, 4] as const) {
    expect(crabSvg('background', 1, level)).toContain('class="mach"')
    expect(crabSvg('background', 1, level)).toContain('class="arm"')
  }
  expect(crabSvg('background', 1, 0)).toContain('--run:0.75s')
  expect(crabSvg('background', 1, 4)).toContain('--run:0.12s')
  expect(count(crabSvg('background', 1, 0), 'class="smk"')).toBe(2)
  expect(count(crabSvg('background', 1, 3), 'class="smk"')).toBe(6)
  expect(crabSvg('background', 1, 1)).not.toContain('class="cash"')
  expect(count(crabSvg('background', 1, 2), 'class="cash"')).toBe(2)
  expect(crabSvg('background', 1, 2)).not.toContain('class="bill"')
  expect(count(crabSvg('background', 1, 3), 'class="bill"')).toBe(4)
  expect(count(crabSvg('background', 1, 4), 'class="bill"')).toBe(8)
  expect(count(crabSvg('background', 1, 4), 'class="coin"')).toBe(4)
  expect(crabSvg('background', 1, 4)).toContain('class="cf"')
  expect(crabSvg('background', 1, 3)).not.toContain('class="cf"')
  expect(crabSvg('background', 1, 4)).toContain('class="wrap rb"')
  // The factory stands behind the crab.
  const svg = crabSvg('background', 1, 0)
  expect(svg.indexOf('class="mach"')).toBeLessThan(svg.indexOf('class="crab"'))
})

test('the waiting crab looks through a magnifying glass, then hurries: it waves, hops, jumps and sounds a siren', () => {
  expect(crabSvg('waiting', 1, 0)).toMatch(/class="waiting mg"/)
  expect(crabSvg('waiting', 1, 1)).toMatch(/class="waiting mgx tf"/)
  for (const level of [0, 1] as const) {
    const svg = crabSvg('waiting', 1, level)

    expect(svg).toContain('class="lens"')
    expect(svg).toContain('class="zoom"')
    expect(svg).toContain('class="beye"')
    expect(svg).toContain('class="pop"')
    expect(svg).not.toContain('class="ask"')
  }
  expect(crabSvg('waiting', 1, 0)).toContain('--g:4s')
  expect(crabSvg('waiting', 1, 2)).not.toContain('class="lens"')
  expect(crabSvg('waiting', 1, 2)).toMatch(/class="waiting wv tf hp"/)
  expect(crabSvg('waiting', 1, 3)).toMatch(/class="waiting wv tf hp both"/)
  expect(crabSvg('waiting', 1, 2)).toContain('>?</text>')
  expect(count(crabSvg('waiting', 1, 2), '>?</text>')).toBe(2)
  expect(crabSvg('waiting', 1, 3)).toContain('>?!</text>')
  expect(crabSvg('waiting', 1, 3)).not.toContain('class="sir"')
  expect(crabSvg('waiting', 1, 4)).toContain('class="sir"')
})

test('asleep, the crab lies tucked in under drifting z\'s', () => {
  const idle = crabSvg('idle', 1)

  expect(idle).toContain('class="zz"')
  expect(count(idle, '>z<') + count(idle, '>Z<')).toBe(3)
  // Lying down: the body sinks onto folded legs, one pixel high.
  expect(idle).toContain('<rect x="4" y="5" width="12" height="4"')
  expect(idle).toContain('<rect x="5" y="10" width="1" height="1"')
  expect(crabSvg('working', 1)).toContain('<rect x="4" y="4" width="12" height="4"')
})

test('awake after a turn, the crab stands, waits on you restlessly, and speeds up with the pace', () => {
  const ready = crabSvg('ready', 0)

  expect(ready).toMatch(/class="ready"/)
  expect(ready).not.toContain('class="zz"')
  // Standing, not lying down.
  expect(ready).toContain('<rect x="4" y="4" width="12" height="4"')
  expect(ready).toContain('<rect x="7" y="5" width="1" height="2"')
  // It looks about, beckons and taps its feet, even calm.
  expect(ready).toContain('.ready .fol { animation: lookabout')
  expect(ready).toContain('.ready .cl { animation: beckon')
  expect(ready).toContain('--rb:3s;--la:5s;--bk:4s;--rt:1.2s')

  // Faster with the pace: busy it sweats, from frenzy it hops, meltdown is fastest.
  expect(crabSvg('ready', 0, 1)).toContain('--rb:1.6s;--la:3.5s;--bk:3s;--rt:0.8s')
  expect(crabSvg('ready', 0, 1)).toContain('class="drip"')
  expect(crabSvg('ready', 0, 3)).toMatch(/class="ready hp"/)
  expect(crabSvg('ready', 0, 3)).toContain('class="shake on"')
  expect(crabSvg('ready', 0, 4)).toContain('--rb:0.35s;--la:1.2s;--bk:0.8s;--rt:0.2s')
  expect(crabSvg('ready', 0, 4)).toContain('class="wrap rb"')
  expect(crabAlt('ready', 0, 2)).toMatch(/your turn \(pace: hyped\)/)

  // It spends no tokens itself, so it does not pant as the pace falls back.
  expect(crabSvg('ready', 0, 3, true)).toBe(crabSvg('ready', 0, 3, false))
})

test('thinking, the crab paces sideways with its thoughts; cooling, it stands', () => {
  expect(crabSvg('thinking', 1, 0)).toContain('<g class="walk">')
  expect(crabSvg('thinking', 1, 0)).toContain('--wk:6s')
  expect(crabSvg('thinking', 1, 4)).toContain('--wk:1.4s')
  expect(crabSvg('thinking', 1, 3, true)).not.toContain('class="walk"')
  expect(crabSvg('working', 1, 0)).not.toContain('class="walk"')
})

test('at work, the crab hammers; hyped it wipes its brow, from frenzy it swings two hammers', () => {
  expect(count(crabSvg('working', 1, 0), 'class="ham ')).toBe(1)
  expect(crabSvg('working', 1, 2)).toMatch(/class="working hm hy"/)
  expect(crabSvg('working', 1, 2)).toContain('class="fling"')
  expect(count(crabSvg('working', 1, 2), 'class="ham ')).toBe(1)
  expect(crabSvg('working', 1, 3)).toMatch(/class="working hm two"/)
  expect(count(crabSvg('working', 1, 3), 'class="ham ')).toBe(2)
  // Meltdown heats the nails instead of setting the crab's head on fire.
  expect(crabSvg('working', 1, 4)).toContain('class="heat r"')
  expect(crabSvg('working', 1, 3)).not.toContain('class="heat')
  expect(crabSvg('working', 1, 3, true)).not.toContain('class="ham ')
})

test('with several things running, the crab conducts: the count sets the tempo, the pace speeds it up', () => {
  expect(crabSvg('several', 3, 0)).toMatch(/class="several cond"/)
  expect(crabSvg('several', 3, 1)).toMatch(/class="several cond tf"/)
  expect(conductBar(2, 0)).toBe(2)
  expect(conductBar(3, 0)).toBe(1.6)
  expect(conductBar(6, 0)).toBe(0.9)
  expect(conductBar(12, 0)).toBe(0.9)
  expect(conductBar(3, 4)).toBe(0.53)
  expect(crabSvg('several', 3, 4)).toContain('--bar:0.53s')
  // The ghosts conduct too, and nobody juggles.
  expect(count(crabSvg('several', 3, 4), 'stroke-width="0.45"')).toBe(3)
  expect(crabSvg('several', 3, 4)).not.toContain('class="ob"')
})

test('every crab snaps its right claw, the ghosts too', () => {
  for (const mood of ['idle', 'thinking', 'working', 'background', 'several', 'waiting'] as const) {
    expect(count(crabSvg(mood, 3, 0), 'class="pin"')).toBe(1)
  }
  expect(count(crabSvg('working', 1, 4), 'class="pin"')).toBe(3)
})

test('the alt text says the pace, and the count past nine', () => {
  expect(crabAlt('idle', 1, 0)).toBe('A crab asleep, tucked in: nothing is running')
  expect(crabAlt('working', 1, 0)).toBe('A crab hammering a nail: a tool is running')
  expect(crabAlt('working', 1, 3)).toBe('A crab hammering a nail: a tool is running (pace: frenzy)')
  expect(crabAlt('several', 3, 0)).toBe('A crab conducting under a badge of 3: several things are running')
  expect(crabAlt('working', 1, 1, true)).toMatch(/panting/)
  expect(crabAlt('waiting', 1, 0)).toBe('A crab looking through a magnifying glass: waiting for your answer')
  expect(crabAlt('waiting', 1, 2)).toBe('A crab with a question mark: waiting for your answer (pace: hyped)')
  expect(crabAlt('background', 1, 1)).toBe('A crab cranking its factory: background work is running (pace: busy)')
  expect(crabAlt('background', 1, 4, true)).toBe('A crab cranking its factory, burning money: background work is running (pace: meltdown)')
  expect(crabSvg('several', 12, 0)).toContain('>9+<')
})

// What the band draws, through the plugin: the crab's alt text.
const props = (isWorking: boolean) => ({
  hasSurvey: false,
  isCollapsed: false,
  isWorking,
  maxRows: 10,
  bodyColumns: 140,
  scroll: { offset: 0, bodyRows: 10 },
  view: {},
})

// The plugin's store, kept in memory: what a test seeds, a later session reads.
const stored = new Map<string, unknown>()

const start = async ($: any, on: any) => {
  on('store.get', (_: unknown, e: { key: string }) => ({ value: stored.get(e.key) }))
  on('store.set', (_: unknown, e: { key: string; value: unknown }) => {
    stored.set(e.key, e.value)
  })
  on('session.start', (_: unknown, e: { cwd: string }) => ({ cwd: e.cwd }))
  on('session.authorize', () => ({ value: { handle: 'h', kind: 'bearer' } }))
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

const crabNow = async ($: any, isWorking = true): Promise<string> => {
  const ui = await $.ui.mount({
    plugin: 'context-band',
    component: 'AbovePrompt',
    surface: 'desktop',
    props: props(isWorking),
  })
  const [svg] = await ui.findAll({ type: 'Svg' })
  await ui.unmount()

  return (svg as any)?.props?.alt ?? 'no crab'
}

// The engine's side of one model step: some text, then the usage it reports.
const answerWith = (on: any, outputTokens: number, text = 'x'.repeat(400)) =>
  on('turn.step', async function* () {
    yield { kind: 'text', index: 0, text }

    return {
      turnId: 't1',
      index: 0,
      answer: text,
      toolUses: [],
      stopReason: 'end_turn',
      usage: {
        input_tokens: 10,
        output_tokens: outputTokens,
        cache_read_input_tokens: 90_000,
        cache_creation_input_tokens: 0,
        model: 'claude-opus-5-5',
      },
    }
  })

const step = async ($: any, agentId?: string) => {
  const stream = $.turn.step({
    turnId: 't1',
    index: 0,
    model: 'claude-opus-5-5',
    messageCount: 3,
    ...(agentId === undefined ? {} : { agentId }),
  })

  for await (const chunk of stream) void chunk

  return stream.result
}

test('a calm session leaves the crab calm', async ($, on) => {
  stored.clear()
  answerWith(on, 1_000)
  await start($, on)

  await step($)

  expect(await crabNow($)).toBe('A crab pacing, claw on its chin: the model is working')
})

test('output well above the usual rate sets the crab off, and its pace shows', async ($, on) => {
  stored.clear()
  answerWith(on, 30_000)
  await start($, on)

  await step($)

  expect(await crabNow($)).toMatch(/pace: meltdown/)
})

test('a step in between, 1.6 times the usual rate, is busy', async ($, on) => {
  stored.clear()
  answerWith(on, 4_000, 'x'.repeat(16_000))
  await start($, on)

  await step($)

  expect(await crabNow($)).toMatch(/pace: busy/)
})

test('a subagent spends tokens too', async ($, on) => {
  stored.clear()
  answerWith(on, 30_000)
  await start($, on)

  await step($, 'agent-1')

  expect(await crabNow($)).toMatch(/pace: meltdown/)
})

test('the usual rate the band stored decides what counts as a lot', async ($, on) => {
  answerWith(on, 30_000)
  stored.set('baselines', { 'claude-opus-5-5': { avg: 120_000, n: 80 } })
  await start($, on)

  await step($)

  expect(await crabNow($)).toBe('A crab pacing, claw on its chin: the model is working')
})

test('a new session starts calm', async ($, on) => {
  stored.clear()
  answerWith(on, 30_000)
  await start($, on)
  await step($)
  expect(await crabNow($)).toMatch(/meltdown/)

  await $.session.start({ cwd: '/', surface: 'desktop', isInteractive: true })

  expect(await crabNow($)).toBe('A crab pacing, claw on its chin: the model is working')
})

test('a background task watched right after a burst of work burns money in the factory', async ($, on) => {
  stored.clear()
  answerWith(on, 30_000)
  await start($, on)

  await step($)
  await $.classic.Stop({
    stop_hook_active: false,
    background_tasks: [{ id: 'b1', type: 'shell', status: 'running', description: 'dev server' }],
  })

  expect(await crabNow($, false)).toMatch(/factory, burning money.*\(pace: meltdown\)/)
})

test('a question asked in the middle of a burst is asked in a hurry', async ($, on) => {
  stored.clear()
  let during = ''
  answerWith(on, 30_000)
  on('tool.call', async () => {
    during = await crabNow($)

    return { result: { answers: {} } }
  })
  await start($, on)

  await step($)
  await $.tool.call({ tool: 'AskUserQuestion', questions: [] })

  expect(during).toMatch(/question mark.*\(pace: meltdown\)/)
})
