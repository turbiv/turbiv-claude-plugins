import { atom, read, update } from 'claude-code'
import type {
  EngineInterface,
  Register,
  SessionContextUsage,
  SessionCost,
  SessionRateLimit,
  Timer,
} from 'claude-code'

import type { ActivityItem, Billing, Limit, Meter, Track } from '../types'
import { breakdown, clipLabel, hookActivity, resetActivity, runningItems } from './activity'
import { CRAB_HEIGHT, CRAB_WIDTH, crabAlt, crabSvg, moodOf } from './crab'
import { hookPace, loadBaselines, resetPace, startPace } from './pace'

const meter = atom({ plugin: 'context-band', key: 'meter' } as const, null)
const track = atom({ plugin: 'context-band', key: 'track' } as const, null)
// Written by ./activity.ts, which declares the same atom.
const activity = atom({ plugin: 'context-band', key: 'activity' } as const, {
  tools: [],
  background: [],
})
// Written by ./pace.ts, which declares the same atom.
const pace = atom({ plugin: 'context-band', key: 'pace' } as const, { level: 0, cooling: false })
// Whether the list of everything running is open under the band.
const isListOpen = atom({ plugin: 'context-band', key: 'isListOpen' } as const, false)

const LIST_LABEL_MAX_CHARS = 80

const BAR_CELLS = 12
// One glyph for both halves of the bar, so filled and empty cells are the
// same width in any font; only the colour tells them apart. A square sits
// on the text's baseline and rises to about capital height, so the bar
// lines up with the words beside it; the block elements (▁ to █) hang from
// the bottom of the line instead and read as too low.
const BAR_GLYPH = '■'
const SEPARATOR = '  ·  '

const AMBER_FROM = 40
const RED_FROM = 85

const SPOTIFY_GREEN = '#1DB954'
const SPOTIFY_POLL_MS = 5_000
const SPOTIFY_TIMEOUT_MS = 4_000
const TRACK_MAX_CHARS = 40

// Asks Spotify only when it is already running, so the poll never launches it.
const SPOTIFY_SCRIPT = [
  'if application "Spotify" is running then',
  'tell application "Spotify"',
  'try',
  'return (player state as string) & tab & (name of current track) & tab & (artist of current track)',
  'end try',
  'end tell',
  'end if',
  'return ""',
]

const LIMIT_LABELS: Record<string, string> = {
  five_hour: '5h',
  seven_day: '7d',
  spend_limit: 'spend',
}

// The windows only a subscription gets. Once one is reported, both are shown,
// in this order, a dash for one with no reading yet.
const PLAN_WINDOWS = ['five_hour', 'seven_day']

// What the band knows about how the session is billed. Set at session.start
// and by every reading after it; a reload runs session.start again and
// starts them afresh from what $.session.usage() reports then.
//
// The login kind alone does not tell: a claude.ai (bearer) login is a Pro/Max
// subscription or a usage-billed Team/Enterprise seat. An API key is never a
// subscription.
let isApiKey = false
// The cost when session.start read it, so a resumed session's past cost is
// not taken for a response of this run.
let usdAtStart: number | null = null
// Whether a response of this run has reported its figures.
let hasResponse = false
// Whether the API has reported a 5h or 7d window: a subscription. Kept for
// the session, so a reading without the windows (after a compaction, say)
// does not turn the band to dollars.
let hasPlanWindows = false

const detectBilling = async ($: EngineInterface, usd: number | null): Promise<void> => {
  hasResponse = false
  hasPlanWindows = false
  usdAtStart = usd

  try {
    isApiKey = (await $.session.authorize())?.kind === 'api-key'
  } catch {
    isApiKey = false
  }
}

const observe = (
  context: SessionContextUsage,
  rateLimits: SessionRateLimit[],
  cost: SessionCost | undefined,
): void => {
  if (rateLimits.some(limit => PLAN_WINDOWS.includes(limit.kind))) {
    hasPlanWindows = true
  }

  // A response reports rate-limit windows or adds to the cost; where the
  // host keeps no cost ledger, it reports the context fill.
  const isAnswered =
    rateLimits.length > 0 ||
    (cost === undefined
      ? context.tokens !== undefined
      : usdAtStart === null || cost.usd > usdAtStart)

  if (isAnswered) {
    hasResponse = true
  }
}

// `plan` once the API reports a 5h or 7d window; `api` with an API key, or
// once a response came without those windows (a usage-billed seat);
// `pending` before the first response of a claude.ai login.
const billingOf = (): Billing => {
  if (hasPlanWindows) {
    return 'plan'
  }

  return isApiKey || hasResponse ? 'api' : 'pending'
}

const toMeter = (
  context: SessionContextUsage,
  rateLimits: SessionRateLimit[],
  cost: SessionCost | undefined,
): Meter => {
  observe(context, rateLimits, cost)

  return {
    tokens: context.tokens ?? null,
    window: context.window,
    percent: context.percent ?? null,
    usd: cost?.usd ?? null,
    billing: billingOf(),
    limits: rateLimits.map(({ kind, percentUsed, resetsAt }) => ({
      kind,
      percentUsed,
      resetsAt: resetsAt ?? null,
    })),
  }
}

// On a subscription: the 5h and 7d windows first (a dash until read), then
// any other window reported. Otherwise: whatever windows were reported (a
// gateway's spend limit, say), with no placeholders.
const shownLimits = (
  m: Meter,
): Array<Limit | { kind: string; percentUsed: null; resetsAt: null }> => {
  if (m.billing !== 'plan') {
    return m.limits
  }

  const planned = PLAN_WINDOWS.map(
    kind =>
      m.limits.find(limit => limit.kind === kind) ?? { kind, percentUsed: null, resetsAt: null },
  )

  return [...planned, ...m.limits.filter(limit => !PLAN_WINDOWS.includes(limit.kind))]
}

const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

// When a window resets, in local time: the 5h window by its clock time
// (15:00), the longer ones with the weekday too (Mon 15:00). Nothing once
// the reset has passed, as the reading is stale until the next response.
const resetLabel = (kind: string, resetsAt: string | null, now: number): string | null => {
  if (resetsAt === null) {
    return null
  }

  const at = Date.parse(resetsAt)

  if (!Number.isFinite(at) || at <= now) {
    return null
  }

  const date = new Date(at)
  const time = `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`

  return kind === 'five_hour' ? time : `${WEEKDAYS[date.getDay()]} ${time}`
}

const compact = (tokens: number): string => {
  if (tokens >= 1_000_000) {
    return `${(tokens / 1_000_000).toFixed(tokens % 1_000_000 === 0 ? 0 : 1)}M`
  }

  if (tokens >= 1_000) {
    return `${Math.round(tokens / 1_000)}k`
  }

  return String(tokens)
}

const level = (percent: number): 'success' | 'warning' | 'error' => {
  if (percent >= RED_FROM) {
    return 'error'
  }

  return percent >= AMBER_FROM ? 'warning' : 'success'
}

const filledCells = (percent: number): number => {
  const cells = Math.round((percent / 100) * BAR_CELLS)

  // Any use at all shows at least one cell.
  return Math.max(percent > 0 ? 1 : 0, Math.min(BAR_CELLS, cells))
}

const clip = (text: string): string =>
  text.length > TRACK_MAX_CHARS ? `${text.slice(0, TRACK_MAX_CHARS - 1)}…` : text

const parseTrack = (stdout: string): Track | null => {
  const [state, title, artist] = stdout.trim().split('\t')

  if (!title || (state !== 'playing' && state !== 'paused')) {
    return null
  }

  return { title, artist: artist ?? '', isPlaying: state === 'playing' }
}

// The poll's own bookkeeping: a reload starts it over, and the next poll
// writes the track again.
let isPolling = false
let lastSeen = ''

const pollSpotify = async ($: EngineInterface): Promise<void> => {
  if (isPolling) {
    return
  }

  isPolling = true

  try {
    const argv = ['osascript', ...SPOTIFY_SCRIPT.flatMap(line => ['-e', line])]
    const { exitCode, stdout } = await $.process.run(argv, { timeoutMs: SPOTIFY_TIMEOUT_MS })
    const seen = exitCode === 0 ? stdout.trim() : ''

    if (seen !== lastSeen) {
      lastSeen = seen
      await update($, track, () => parseTrack(seen))
    }
  } catch {
    // No osascript (not macOS), a timeout or a refusal: show no track.
    if (lastSeen !== '') {
      lastSeen = ''
      await update($, track, () => null)
    }
  } finally {
    isPolling = false
  }
}

// The band is for the apps, not the terminal: a terminal session keeps its
// own status line, so there the mod draws nothing and never polls Spotify.
let spotifyTimer: Timer | undefined

const startSpotify = ($: EngineInterface): void => {
  if (spotifyTimer !== undefined) {
    return
  }

  spotifyTimer = $.clock.every(SPOTIFY_POLL_MS, () => void pollSpotify($))
  void pollSpotify($)
}

// One thing running: what it is. Several: how many, and of what kinds.
const activityText = (items: ActivityItem[]): string => {
  const [only] = items

  if (only === undefined) {
    return 'Idle'
  }

  if (items.length === 1) {
    return clipLabel(only.label)
  }

  const kinds = breakdown(items)

  return kinds.includes(',') ? `${items.length} running: ${kinds}` : `${kinds} running`
}

export const register: Register = on => {
  hookActivity(on)
  hookPace(on)

  on('session.start', async ($, e, next) => {
    const result = await next(e)
    await resetActivity($)
    await resetPace($)
    await loadBaselines($)
    const usage = await $.session.usage()
    await detectBilling($, usage.cost?.usd ?? null)
    await update($, meter, () => toMeter(usage.context, usage.rateLimits, usage.cost))

    if ((await $.session.surfaces()).some(surface => surface !== 'terminal')) {
      startSpotify($)
      startPace($)
    }

    return result
  })

  // A session that began in a terminal and is later opened in an app.
  on('session.attach', ($, e, next) => {
    if (e.surface !== 'terminal') {
      startSpotify($)
      startPace($)
    }

    return next(e)
  })

  on('session.measure', async ($, e, next) => {
    await update($, meter, () => toMeter(e.context, e.rateLimits, e.cost))

    return next(e)
  })

  on('session.compact', async ($, e, next) => {
    const result = await next(e)
    const usage = await $.session.usage()
    await update($, meter, () => toMeter(usage.context, usage.rateLimits, usage.cost))

    return result
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    if (e.surface === 'terminal') {
      return next(e)
    }

    const m = await read($, meter)
    const song = await read($, track)
    const running = runningItems(await read($, activity), e.props.isWorking)

    if (e.props.hasSurvey || m === null) {
      return next(e)
    }

    const { Box, Button, Svg, Text } = $.ui.resolve(e)
    const now = await $.clock.now()
    const percent = m.percent ?? 0
    const filled = filledCells(percent)
    const color = level(percent)
    const mood = moodOf(running, e.props.isWorking)
    const temper = await read($, pace)
    const isSeveral = running.length > 1
    const isOpen = isSeveral && (await read($, isListOpen))
    const label = activityText(running)

    return (
      <Box width="100%" flexDirection="column">
        <Box width="100%" justifyContent="space-between" alignItems="center" columnGap={2}>
          <Box alignItems="center" columnGap={1}>
            {Svg === undefined ? (
              <Text color={running.length > 0 ? 'suggestion' : 'subtle'}>
                {running.length > 0 ? '●' : '○'}
              </Text>
            ) : (
              <Svg
                source={crabSvg(mood, running.length, temper.level, temper.cooling)}
                alt={crabAlt(mood, running.length, temper.level, temper.cooling)}
                width={CRAB_WIDTH}
                height={CRAB_HEIGHT}
                isInteractive
              />
            )}
            {isSeveral ? (
              <Button
                key="activity"
                label={label}
                plain
                onPress={() => update($, isListOpen, open => !open)}
              >
                {label}
                <Text dimColor>{isOpen ? ' ▴' : ' ▾'}</Text>
              </Button>
            ) : (
              <Text color={running.length > 0 ? 'text' : 'subtle'}>{label}</Text>
            )}
            <Text>
              <Text dimColor>{SEPARATOR}</Text>
              <Text>🧠 </Text>
              <Text mono color={color}>
                {BAR_GLYPH.repeat(filled)}
              </Text>
              <Text mono color="subtle">
                {BAR_GLYPH.repeat(BAR_CELLS - filled)}
              </Text>
              {m.percent === null ? (
                <Text dimColor> –</Text>
              ) : (
                <Text tabular weight="semibold" color={color}>
                  {` ${m.percent}%`}
                </Text>
              )}
              <Text dimColor>{SEPARATOR}</Text>
              {m.tokens === null ? null : (
                <Text tabular color="text">
                  {compact(m.tokens)}
                </Text>
              )}
              <Text dimColor>
                {m.tokens === null ? '' : ' / '}
                {compact(m.window)}
              </Text>
              {shownLimits(m).map(limit => {
                const reset = resetLabel(limit.kind, limit.resetsAt, now)

                return (
                  <Text key={limit.kind}>
                    <Text dimColor>
                      {SEPARATOR}
                      {LIMIT_LABELS[limit.kind] ?? limit.kind}{' '}
                    </Text>
                    {limit.percentUsed === null ? (
                      <Text dimColor>–</Text>
                    ) : (
                      <Text tabular color={level(limit.percentUsed)}>
                        {`${Math.round(limit.percentUsed)}%`}
                      </Text>
                    )}
                    {reset === null ? null : <Text dimColor>{` ↻ ${reset}`}</Text>}
                  </Text>
                )
              })}
              {/* USD only on usage billing: on a subscription it is not what is
                  paid, and before the first response it is not yet known which. */}
              {m.billing !== 'api' || m.usd === null ? null : (
                <Text>
                  <Text dimColor>{SEPARATOR}</Text>
                  <Text tabular color="suggestion">
                    {`$${m.usd.toFixed(2)}`}
                  </Text>
                </Text>
              )}
            </Text>
          </Box>
          {song === null ? null : (
            <Text wrap="truncate-end">
              <Text color={song.isPlaying ? SPOTIFY_GREEN : 'subtle'}>
                {song.isPlaying ? '♫ ' : '⏸ '}
              </Text>
              <Text color={song.isPlaying ? 'text' : 'subtle'}>{clip(song.title)}</Text>
              {song.artist === '' ? null : <Text dimColor>{` — ${clip(song.artist)}`}</Text>}
            </Text>
          )}
        </Box>
        {isOpen
          ? running.map(item => (
              <Text key={item.id} wrap="truncate-end">
                <Text dimColor>{'   · '}</Text>
                <Text>{clipLabel(item.label, LIST_LABEL_MAX_CHARS)}</Text>
              </Text>
            ))
          : null}
      </Box>
    )
  })
}
