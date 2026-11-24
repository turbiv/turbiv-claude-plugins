export type Limit = { kind: string; percentUsed: number; resetsAt: string | null }

// `plan`: a Pro/Max subscription (the API reports its 5h/7d windows), shown as
// those windows. `api`: usage billing (an API key, or a claude.ai seat whose
// responses carry no plan windows), shown in US dollars. `pending`: a
// claude.ai login before its first response, shown as neither.
export type Billing = 'plan' | 'api' | 'pending'

export type Meter = {
  tokens: number | null
  window: number
  percent: number | null
  usd: number | null
  billing: Billing
  limits: Limit[]
}

export type Track = { title: string; artist: string; isPlaying: boolean }

// `tool`: a call in flight in the main turn. The rest run in the background.
export type ActivityKind = 'tool' | 'shell' | 'agent' | 'monitor' | 'workflow' | 'task'

export type ActivityItem = { id: string; kind: ActivityKind; label: string }

export type Activity = { tools: ActivityItem[]; background: ActivityItem[] }

// What the band's crab acts out.
export type Mood = 'idle' | 'thinking' | 'working' | 'background' | 'several' | 'waiting'

// How hard the session works, from calm (0) to meltdown (4): the output tokens
// of the last minute against the usual rate for the model. `cooling`: the
// rate just fell back from a burst, and the crab pants for a few seconds.
export type Level = 0 | 1 | 2 | 3 | 4

export type Pace = { level: Level; cooling: boolean }

// What the band has learned about a model: the usual output tokens per minute
// while it works (`avg`), and how many active minutes that rests on (`n`).
export type Baseline = { avg: number; n: number }

declare module 'claude-code' {
  interface PluginState {
    'context-band': {
      meter: Meter | null
      track: Track | null
      activity: Activity
      isListOpen: boolean
      pace: Pace
    }
  }
}
