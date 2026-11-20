export type Limit = { kind: string; percentUsed: number; resetsAt: string | null }

// `plan`: a Pro/Max subscription, shown as its 5h/7d windows. `api`: API-key
// billing, shown in US dollars.
export type Billing = 'plan' | 'api'

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

declare module 'claude-code' {
  interface PluginState {
    'context-band': { meter: Meter | null; track: Track | null; activity: Activity; isListOpen: boolean }
  }
}
