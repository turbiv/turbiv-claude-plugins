import { atom, update } from 'claude-code'
import type { EngineInterface, On, Timer } from 'claude-code'

import type { Baseline, Level, Pace } from '../types'

// How hard the session works: the output tokens (the model's answer, its
// thinking and its tool calls, subagents' too) of the last minute, against the
// usual rate for the model, which the band learns from the sessions it sees and
// keeps in the plugin's own store. The crab acts out the ratio.
//
// Written here, read by ./register.tsx, which declares the same atom.
const pace = atom({ plugin: 'context-band', key: 'pace' } as const, { level: 0, cooling: false })

export const WINDOW_MS = 60_000
const TICK_MS = 1_000
const CHARS_PER_TOKEN = 4

// Below this many tokens a minute the model is idle for the baseline's sake:
// waiting on you must not drag the usual rate down.
export const MIN_ACTIVE_RATE = 300
const ACTIVE_MS = 60_000

// Until the band has seen the model, a usual rate of its own guess, counted as
// this many active minutes so that the first real ones move it gently.
export const FRESH: Baseline = { avg: 2_500, n: 3 }
const SLOWEST_WEIGHT = 0.05
const OUTLIER_FACTOR = 3

// The ratio to the usual rate at which levels 1 to 4 begin.
export const LEVEL_FROM = [1.5, 2, 3, 4] as const
// A level is held until the ratio falls this far below where it began.
const RELEASE = 0.85
const STEP_DOWN_MS = 3_000
const COOL_MS = 4_000

const STORE_KEY = 'baselines'

export type Gait = { level: Level; droppedAt: number; coolUntil: number }

// Tokens a minute: what arrived in the window that ends now.
export const rateOf = (events: readonly { at: number; tokens: number }[], now: number): number =>
  Math.max(
    0,
    events.reduce((sum, e) => (e.at > now - WINDOW_MS && e.at <= now ? sum + e.tokens : sum), 0),
  )

// The level a ratio asks for. Rising is at once; a level already held stays
// until the ratio is clearly under where it began, so a rate hovering at a
// boundary does not flicker.
export const levelFor = (ratio: number, held: Level): Level => {
  let target: Level = 0

  for (const [i, from] of LEVEL_FROM.entries()) {
    if (ratio >= from) target = (i + 1) as Level
  }

  if (target >= held || held === 0) return target

  const from = LEVEL_FROM[held - 1] ?? 0

  return ratio >= from * RELEASE ? held : target
}

// One tick of the crab's temper: up at once, down one level every few seconds,
// and a spell of panting when it comes down from hyped or more.
export const stepLevel = (prev: Gait, ratio: number, now: number): Gait => {
  const target = levelFor(ratio, prev.level)

  if (target === prev.level) return prev
  if (target > prev.level) return { ...prev, level: target, coolUntil: 0 }
  if (now - prev.droppedAt < STEP_DOWN_MS) return prev

  const level = (prev.level - 1) as Level

  return {
    level,
    droppedAt: now,
    coolUntil: level <= 1 && prev.level >= 2 ? now + COOL_MS : prev.coolUntil,
  }
}

// A new active minute's rate into the usual one: a plain mean while it rests
// on few minutes, then a slow moving average. A burst counts for at most
// OUTLIER_FACTOR times the usual rate, so a meltdown does not become normal.
export const nextBaseline = (baseline: Baseline, sample: number): Baseline => {
  const n = baseline.n + 1
  const weight = Math.max(1 / n, SLOWEST_WEIGHT)
  const clipped = Math.min(Math.max(sample, 0), baseline.avg * OUTLIER_FACTOR)

  return { avg: baseline.avg + (clipped - baseline.avg) * weight, n }
}

export type Active = { ms: number; sum: number }

// Time spent actively working, with the rate weighted by that time. Once a
// minute of it has gathered, its mean rate is a sample for the baseline.
export const accumulate = (
  active: Active,
  rate: number,
  dtMs: number,
): { active: Active; sample: number | null } => {
  if (rate < MIN_ACTIVE_RATE || dtMs <= 0) return { active, sample: null }

  const next = { ms: active.ms + dtMs, sum: active.sum + rate * dtMs }

  return next.ms >= ACTIVE_MS
    ? { active: { ms: 0, sum: 0 }, sample: next.sum / next.ms }
    : { active: next, sample: null }
}

const isBaseline = (value: unknown): value is Baseline => {
  const b = value as Partial<Baseline> | null

  return (
    typeof b === 'object' &&
    b !== null &&
    typeof b.avg === 'number' &&
    Number.isFinite(b.avg) &&
    b.avg > 0 &&
    typeof b.n === 'number' &&
    Number.isFinite(b.n) &&
    b.n >= 0
  )
}

// What the store holds, read as data that may be anything: only well-formed
// entries are kept.
export const parseBaselines = (stored: unknown): Record<string, Baseline> => {
  if (typeof stored !== 'object' || stored === null || Array.isArray(stored)) return {}

  return Object.fromEntries(Object.entries(stored).filter(([, value]) => isBaseline(value)))
}

// The bookkeeping below is the module's own: a reload starts it over, the
// store keeps the baselines.
let events: { at: number; tokens: number }[] = []
let gait: Gait = { level: 0, droppedAt: 0, coolUntil: 0 }
let shown: Pace = { level: 0, cooling: false }
let model = 'default'
let baselines: Record<string, Baseline> = {}
let active: Active = { ms: 0, sum: 0 }
let lastTick = 0
let paceTimer: Timer | undefined

const record = (tokens: number, now: number): void => {
  if (tokens !== 0) events.push({ at: now, tokens })
}

// One look at the rate: the crab's level, and what the minute teaches.
async function tick($: EngineInterface, now: number): Promise<void> {
  events = events.filter(e => e.at > now - WINDOW_MS)

  const rate = rateOf(events, now)
  const usual = (baselines[model] ?? FRESH).avg

  gait = stepLevel(gait, rate / usual, now)

  const cooling = now < gait.coolUntil

  if (gait.level !== shown.level || cooling !== shown.cooling) {
    shown = { level: gait.level, cooling }
    await update($, pace, () => shown)
  }

  const dt = lastTick === 0 ? 0 : Math.min(now - lastTick, 5 * TICK_MS)

  lastTick = now

  const learned = accumulate(active, rate, dt)

  active = learned.active

  if (learned.sample !== null) {
    baselines = { ...baselines, [model]: nextBaseline(baselines[model] ?? FRESH, learned.sample) }

    try {
      await $.store.set(STORE_KEY, baselines)
    } catch {
      // The store is a convenience: what was learned stays for this session.
    }
  }
}

export async function loadBaselines($: EngineInterface): Promise<void> {
  try {
    baselines = parseBaselines(await $.store.get(STORE_KEY))
  } catch {
    // No store to read: the crab starts from the fresh guess.
    baselines = {}
  }
}

// A reload or a new session: the crab starts calm, the minute's tokens gone.
export async function resetPace($: EngineInterface): Promise<void> {
  events = []
  gait = { level: 0, droppedAt: 0, coolUntil: 0 }
  shown = { level: 0, cooling: false }
  active = { ms: 0, sum: 0 }
  lastTick = 0
  await update($, pace, () => shown)
}

// The rate falls when nothing arrives, so the level must be looked at on a
// clock too, not only when tokens do.
export function startPace($: EngineInterface): void {
  if (paceTimer !== undefined) return

  paceTimer = $.clock.every(TICK_MS, () => void tick($, Date.now()))
}

export function hookPace(on: On): void {
  on('turn.step', async function* ($, e, next) {
    if (e.agentId === undefined) model = e.model

    const stream = next(e)
    let estimated = 0

    for await (const chunk of stream) {
      const size =
        chunk.kind === 'text' || chunk.kind === 'thinking'
          ? chunk.text.length
          : chunk.kind === 'input'
            ? chunk.json.length
            : 0

      if (size > 0) {
        const tokens = Math.ceil(size / CHARS_PER_TOKEN)

        estimated += tokens
        record(tokens, Date.now())
      }

      yield chunk
    }

    const result = await stream.result
    const actual = result.usage?.output_tokens

    // The API's own count replaces the estimate of what the step streamed.
    if (actual !== undefined) record(actual - estimated, Date.now())

    await tick($, Date.now())

    return result
  })
}
