import { atom, update } from 'claude-code'
import type { EngineInterface, Timer } from 'claude-code'

// When a main turn ends the crab stays awake a while before it falls asleep:
// that is the time you spend typing the next prompt. ./activity.ts calls wake
// from its turn.complete hook (a module hooks an event once).
//
// Written here, read by ./register.tsx, which declares the same atom.
const awake = atom({ plugin: 'context-band', key: 'awake' } as const, false)

export const AWAKE_MS = 5 * 60_000

let sleepTimer: Timer | undefined

// Awake now, asleep AWAKE_MS from now; a later turn's end starts the wait over.
export async function wake($: EngineInterface): Promise<void> {
  sleepTimer?.cancel()
  await update($, awake, () => true)
  sleepTimer = $.clock.after(AWAKE_MS, () => {
    sleepTimer = undefined
    void update($, awake, () => false)
  })
}

// A reload or a new session: the timer is gone, so the crab starts asleep.
export async function resetAwake($: EngineInterface): Promise<void> {
  sleepTimer?.cancel()
  sleepTimer = undefined
  await update($, awake, () => false)
}

