import type { ActivityItem, Level, Mood } from '../types'

// The band's crab: a small pixel crab, drawn as one SVG per mood, that acts
// out what the session is doing. The desktop and mobile apps run its CSS
// animation; hovered, it waves.
//
// Each mood has its own act: asleep it lies tucked in; just after a turn it
// stands awake and restless, looking about, tapping its feet and beckoning
// you with a claw, still bouncing to the pace of the turn it just left; thinking it paces; at work it hammers; with background work it cranks a little factory; with several
// things running it conducts them; waiting for you it looks through a
// magnifying glass. Whatever it does, every few seconds its right claw snaps
// shut twice.
//
// Awake, it also acts out how hard the session works (the pace, from 0 calm to
// 4 meltdown): faster, sweating, then steaming, red with sparks, and at
// meltdown rainbow coloured with ghosts. The working, thinking and
// several-things crabs pant for a few seconds when the pace falls back from a
// burst.

// The drawing's box, in the cell's own units: the crab stands in the 22 x 16
// cell, and the margin around it holds what the higher levels add (sparks,
// the hammers' blocks, the factory, the rays above). The crab keeps the size
// it had.
const VIEW = { x: -3, y: -2, w: 28, h: 18 }

export const CRAB_HEIGHT = 25
export const CRAB_WIDTH = Math.round((VIEW.w * CRAB_HEIGHT) / VIEW.h)

const CORAL = '#D97757'
const SHADE = '#B65D40'
const HOT = '#E0654A'
const HOT_SHADE = '#B84F38'
const RED = '#E5483A'
const RED_SHADE = '#B8321F'
const EYE = '#2B1D17'
const INK = '#9A8F86'
const GOLD = '#FFD23F'
const SWEAT = '#6FA8DC'
const PAPER = '#FAF9F5'
const WOOD = '#7A5236'
const IRON = '#5C4B42'
const STEEL = '#C9C2BB'
const EMBER = '#F28C28'
const MONEY = '#7BC47F'
const MONEY_SHADE = '#4E9A54'

const LEVEL_NAMES = ['calm', 'busy', 'hyped', 'frenzy', 'meltdown'] as const

// What the crab acts out: someone waiting on you first, then how much runs.
// With nothing running it sleeps, unless a turn ended a moment ago (`isAwake`).
export const moodOf = (items: ActivityItem[], isWorking: boolean, isAwake = false): Mood => {
  if (items.some(item => item.label === 'Waiting for your answer')) return 'waiting'
  if (items.length === 0) return isAwake ? 'ready' : 'idle'
  if (items.length > 1) return 'several'

  const [only] = items

  if (only?.id === 'turn') return 'thinking'

  return only?.kind === 'tool' || isWorking ? 'working' : 'background'
}

// The pace shows on every mood but sleep: a crab that waits for your answer,
// or for your next prompt, right after a burst of work is still wound up.
// Only the moods that spend tokens themselves pant when the pace falls back
// from a burst.
const hasPace = (mood: Mood): boolean => mood !== 'idle'

const canCool = (mood: Mood): boolean =>
  mood === 'working' || mood === 'thinking' || mood === 'several'

const rect = (x: number, y: number, w: number, h: number, fill: string, cls = ''): string =>
  `<rect${cls === '' ? '' : ` class="${cls}"`} x="${x}" y="${y}" width="${w}" height="${h}" fill="${fill}"/>`

type Box = [number, number, number, number]

const rects = (boxes: Box[], fill: string): string => boxes.map(([x, y, w, h]) => rect(x, y, w, h, fill)).join('')

// The right side's boxes from the left side's, across the crab's middle.
const mirror = (boxes: Box[]): Box[] => boxes.map(([x, y, w, h]): Box => [20 - x - w, y, w, h])

const coats = (level: Level): [string, string] =>
  level >= 3 ? [RED, RED_SHADE] : level === 2 ? [HOT, HOT_SHADE] : [CORAL, SHADE]

const EYES_OPEN = [rect(7, 5, 1, 2, EYE), rect(12, 5, 1, 2, EYE)].join('')
const EYES_UP = [rect(7, 4, 1, 2, EYE), rect(12, 4, 1, 2, EYE)].join('')
const EYES_SHUT = [rect(6.5, 6, 2, 0.7, EYE), rect(11.5, 6, 2, 0.7, EYE)].join('')
// Worried brows over the eyes: busy and hyped.
const BROWS = [rect(6.4, 4.2, 2.2, 0.5, EYE), rect(11.4, 4.2, 2.2, 0.5, EYE)].join('')
const BROWS_UP = [rect(6.4, 3.3, 2.2, 0.5, EYE), rect(11.4, 3.3, 2.2, 0.5, EYE)].join('')

const spiral = (x: number): string =>
  `<g class="sp">${rect(x, 5, 2, 2, PAPER)}${rect(x, 5, 1, 1, EYE)}${rect(x + 1, 6, 1, 1, EYE)}</g>`

const eyesOf = (mood: Mood, level: Level, cooling: boolean): string => {
  if (cooling || mood === 'idle') return `<g class="eyes">${EYES_SHUT}</g>`
  if (hasPace(mood) && level >= 3) return `<g class="eyes spiral">${spiral(6.5)}${spiral(11.5)}</g>`

  const brows = hasPace(mood) && level >= 1
  const up = mood === 'thinking'

  return `<g class="eyes">${up ? EYES_UP : EYES_OPEN}${brows ? (up ? BROWS_UP : BROWS) : ''}</g>`
}

// The conductor's baton: white, outlined so it shows on a light band and a
// dark one, with a brown grip in the claw.
const BATON =
  `<g shape-rendering="geometricPrecision">` +
  `<line x1="18.3" y1="0.6" x2="22.6" y2="-4.2" stroke="${EYE}" stroke-width="0.85" stroke-linecap="round"/>` +
  `<line x1="18.3" y1="0.6" x2="22.6" y2="-4.2" stroke="${PAPER}" stroke-width="0.45" stroke-linecap="round"/>` +
  `<circle cx="18.4" cy="0.5" r="0.6" fill="${WOOD}"/></g>`

// Standing, the claws are up; tucked in to sleep, they rest on the ground as
// closed pincers, and the body sinks one pixel onto folded legs.
const CLAW_UP: Box[] = [[0, 0, 1, 2], [2, 0, 1, 2], [0, 2, 3, 1], [1, 3, 1, 2], [2, 4, 2, 1]]
const CLAW_DOWN: Box[] = [[0, 8, 3, 1], [2, 9, 2, 1], [0, 10, 3, 1], [3, 8, 1, 1]]

// One crab, its parts in groups the stylesheet moves. The right claw's inner
// pincer standing, or its top jaw lying down, is a group of its own so it can
// snap.
const crab = (coral: string, shade: string, eyes: string, { baton = false, tucked = false } = {}): string => {
  const left = tucked ? CLAW_DOWN : CLAW_UP
  const right = mirror(left)
  const pin = tucked ? 0 : 1
  const rightClaw =
    `<g class="pin">${rects([right[pin]!], coral)}</g>` + rects(right.filter((_, i) => i !== pin), coral)
  const sink = tucked ? 1 : 0
  const leg = tucked ? 1 : 2
  const body = rects([[5, 3 + sink, 10, 1], [4, 4 + sink, 12, 4], [5, 8 + sink, 10, 1]], coral)
  const legsA = rects([[5, 9 + sink, 1, leg], [12, 9 + sink, 1, leg]], shade)
  const legsB = rects([[7, 9 + sink, 1, leg], [14, 9 + sink, 1, leg]], shade)
  const face = tucked ? `<g transform="translate(0 1)">${eyes}</g>` : eyes

  return [
    `<g class="legs-a">${legsA}</g>`,
    `<g class="legs-b">${legsB}</g>`,
    `<g class="body">${body}<g class="fol">${face}</g></g>`,
    `<g class="cl">${rects(left, coral)}</g>`,
    `<g class="cr">${rightClaw}${baton ? BATON : ''}</g>`,
  ].join('')
}

const sweat = (x: number, cls: string): string =>
  `<path class="${cls}" d="M${x} 8 q-1 1.6 0 2.2 q1 -0.6 0 -2.2z" fill="${SWEAT}"/>`

const STEAM = [
  `<circle class="puff" cx="3" cy="6" r="1" fill="${STEEL}"/>`,
  `<circle class="puff2" cx="20" cy="6" r="1" fill="${STEEL}"/>`,
].join('')

const spark = (x: number, y: number, delay: number): string =>
  `<rect class="spk" style="animation-delay:${delay}s" x="${x}" y="${y}" width="0.9" height="0.9" fill="${GOLD}"/>`

const bang = (x: number, y: number): string =>
  `<text class="bang" x="${x}" y="${y}" text-anchor="middle" font-size="4" font-weight="bold" font-family="-apple-system, system-ui, sans-serif" fill="${RED}">!!</text>`

const BOLTS = [
  `<path class="bolt" d="M12 -0.5 L10.4 3 L12 3 L10.8 6.4 L14 2.4 L12.4 2.4 L13.6 -0.5z" fill="${GOLD}"/>`,
  `<path class="bolt2" d="M16 0 L15 2.4 L16 2.4 L15.2 4.6 L17.6 1.8 L16.6 1.8 L17.4 0z" fill="${GOLD}"/>`,
].join('')

const RAYS = [
  rect(10.7, -0.8, 0.6, 2.2, GOLD, 'ray'),
  rect(6, 3, 1.8, 0.6, GOLD, 'ray2'),
  rect(14.2, 3, 1.8, 0.6, GOLD, 'ray2'),
  rect(8, 0.6, 0.6, 1.8, GOLD, 'ray'),
  rect(13.4, 0.6, 0.6, 1.8, GOLD, 'ray'),
  rect(3.6, 5, 1.8, 0.6, GOLD, 'ray'),
  rect(16.6, 5, 1.8, 0.6, GOLD, 'ray'),
].join('')

const gear = (color: string): string =>
  [
    rect(1, 1, 3, 3, color),
    rect(2, 0, 1, 1, color),
    rect(2, 4, 1, 1, color),
    rect(0, 2, 1, 1, color),
    rect(4, 2, 1, 1, color),
    rect(2, 2, 1, 1, PAPER),
  ].join('')

const GEARS = [
  `<g transform="translate(10 0.5)"><g class="gear">${gear(INK)}</g></g>`,
  `<g transform="translate(14.4 3)"><g class="gear rev">${gear(CORAL)}</g></g>`,
].join('')

const badge = (count: number): string => {
  const text = count > 9 ? '9+' : String(count)

  return [
    `<g class="badge" shape-rendering="geometricPrecision">`,
    `<circle cx="11" cy="4.4" r="3.4" fill="${PAPER}" stroke="${CORAL}" stroke-width="0.7"/>`,
    `<text x="11" y="${text.length > 1 ? 5.75 : 5.85}" text-anchor="middle" font-size="${text.length > 1 ? 3.2 : 4.2}" `,
    `font-weight="bold" font-family="-apple-system, system-ui, sans-serif" fill="${SHADE}">${text}</text>`,
    `</g>`,
  ].join('')
}

const SIREN = [
  `<g transform="translate(11 0.6)">`,
  rect(-1.4, 0.6, 2.8, 0.8, INK),
  `<path class="sir" d="M-1.2 0.6 Q0 -1.9 1.2 0.6 Z" fill="${RED}"/>`,
  rect(-3, -0.6, 1, 0.4, RED, 'sir2'),
  rect(2, -0.6, 1, 0.4, RED, 'sir'),
  rect(-0.2, -2.4, 0.4, 0.9, RED, 'sir2'),
  `</g>`,
].join('')

const askMark = (text: string, x: number, y: number, size: number, color: string, cls: string): string =>
  `<text class="${cls}" x="${x}" y="${y}" font-size="${size}" font-weight="bold" font-family="monospace" fill="${color}">${text}</text>`

// The background crab's factory, standing behind its right side: a chimney, a
// gauge whose needle swings, a furnace window glowing. The crab cranks it.
const MACHINE = [
  `<g class="mach">`,
  `<rect x="15.6" y="6.6" width="7.6" height="9.4" rx="0.6" fill="#7D736B" stroke="${IRON}" stroke-width="0.4" shape-rendering="geometricPrecision"/>`,
  rect(21.4, 3.8, 1.3, 2.8, IRON),
  `<circle cx="21.4" cy="9.6" r="1.4" fill="${PAPER}" stroke="${IRON}" stroke-width="0.3" shape-rendering="geometricPrecision"/>`,
  `<g class="ndl"><line x1="21.4" y1="9.6" x2="21.4" y2="8.5" stroke="${RED}" stroke-width="0.35" stroke-linecap="round" shape-rendering="geometricPrecision"/></g>`,
  rect(19.6, 12, 3.2, 3, '#3A2E28'),
  rect(19.9, 12.3, 2.6, 2.4, EMBER, 'glow'),
  `</g>`,
].join('')

// The crank on top of the factory: an arm turning round a hub, the claw on
// its knob.
const CRANK = [
  `<g class="arm" shape-rendering="geometricPrecision">`,
  `<line x1="0" y1="0" x2="0" y2="-1.3" stroke="${IRON}" stroke-width="0.5" stroke-linecap="round"/>`,
  `<circle cx="0" cy="-1.3" r="0.45" fill="${WOOD}"/></g>`,
  `<circle cx="20.5" cy="6.6" r="0.5" fill="${IRON}" shape-rendering="geometricPrecision"/>`,
].join('')

// The claw's path round the crank, in its own units.
const CRANK_PATH = Array.from({ length: 9 }, (_, i) => {
  const a = (Math.PI * 2 * i) / 8

  return `${(12.5 * i).toFixed(1)}% { transform: translate(${(1.3 * Math.cos(a)).toFixed(2)}px, ${(-2 + 1.3 * Math.sin(a)).toFixed(2)}px) }`
}).join(' ')

// Puffs of smoke from the chimney, each drifting its own way.
const DRIFT = [-1.5, -0.4, -2.1, 0.3, -1.1, -1.8, -0.8, 0.1]

const smoke = (n: number, color: string, r: number): string =>
  Array.from(
    { length: n },
    (_, i) =>
      `<circle class="smk" style="--dx:${DRIFT[i]}px;animation-delay:calc(var(--sm) * -${(i / n).toFixed(3)})" ` +
      `cx="22" cy="3.2" r="${r}" fill="${color}"/>`,
  ).join('')

const bill = (x: number, y: number): string => rect(x, y, 1.6, 0.9, MONEY) + rect(x + 0.6, y + 0.25, 0.4, 0.4, MONEY_SHADE)

// The money: hyped, a little tumbles in the furnace; from frenzy bills fly out
// of the chimney and burn to ash; at meltdown coins pop out of the furnace too.
const inFurnace = (n: number): string =>
  `<clipPath id="furn"><rect x="19.9" y="12.3" width="2.6" height="2.4"/></clipPath><g clip-path="url(#furn)">` +
  Array.from(
    { length: n },
    (_, i) => `<g class="cash" style="animation-delay:calc(var(--mn) * -${(i / n).toFixed(3)})">${bill(20 + (i % 2) * 0.9, 13.2)}</g>`,
  ).join('') +
  `</g>`

const burning = (n: number): string =>
  Array.from(
    { length: n },
    (_, i) =>
      `<g class="bill" style="--dx:${(DRIFT[i]! * 1.8).toFixed(2)}px;animation-delay:calc(var(--mn) * -${(i / n).toFixed(3)})">` +
      `${bill(21.3, 3.2)}</g>`,
  ).join('')

const coins = (n: number): string =>
  Array.from(
    { length: n },
    (_, i) =>
      `<circle class="coin" style="animation-delay:calc(var(--mn) * -${(i / n).toFixed(3)})" cx="${20.2 + (i % 3) * 0.9}" ` +
      `cy="14.6" r="0.45" fill="${GOLD}" stroke="#C9A227" stroke-width="0.15"/>`,
  ).join('')

const CHIMNEY_FIRE = `<path class="cf" d="M21.2 3.8 L21.6 1.6 L22.05 3 L22.5 1.2 L22.9 3.8z" fill="${EMBER}"/>`

const ZZZ = [
  `<text class="zz" x="14" y="9" font-size="3" font-weight="bold" font-family="monospace" fill="${INK}">z</text>`,
  `<text class="zz zz2" x="14" y="9" font-size="3.6" font-weight="bold" font-family="monospace" fill="${INK}">z</text>`,
  `<text class="zz zz3" x="14" y="9" font-size="2.6" font-weight="bold" font-family="monospace" fill="${INK}">Z</text>`,
].join('')

const thinkingDots = [
  `<circle class="dot d1" cx="12.5" cy="6.6" r="0.8" fill="${INK}"/>`,
  `<circle class="dot d2" cx="14.6" cy="4.8" r="0.9" fill="${INK}"/>`,
  `<circle class="dot d3" cx="17" cy="2.6" r="1.1" fill="${INK}"/>`,
].join('')

// The hammer crab's work: a nail on a block beside it, the hammer in its claw
// swung by the stylesheet. The left side mirrors the right; at meltdown the
// nails glow red hot and the block gives off heat.
const station = (side: 'r' | 'l', hot: boolean): string => {
  const x = (v: number, w = 0): number => (side === 'r' ? v : 22 - v - w)
  const nail = hot ? '#FF6B3D' : STEEL
  const sparks =
    rect(x(22.2, 0.7), 9.6, 0.7, 0.7, GOLD) + rect(x(19.8, 0.6), 9.4, 0.6, 0.6, GOLD) + rect(x(21.4, 0.5), 8.6, 0.5, 0.5, GOLD)
  const embers =
    rect(x(23, 0.6), 8.4, 0.6, 0.6, EMBER) + rect(x(20.4, 0.5), 7.6, 0.5, 0.5, GOLD) + rect(x(22.4, 0.5), 7.2, 0.5, 0.5, EMBER)

  return [
    hot ? rect(x(18.2, 6), 11.8, 6, 2.4, EMBER, `heat ${side}`) : '',
    rect(x(18.6, 5.2), 12.8, 5.2, 0.8, '#7D736B'),
    rect(x(19.2, 4), 13.6, 4, 2.2, INK),
    `<g class="nail ${side}">${rect(x(20.6, 1.3), 10.6, 1.3, 0.4, nail)}${rect(x(21, 0.5), 11, 0.5, 1.8, nail)}</g>`,
    `<g class="ham ${side}" shape-rendering="geometricPrecision">`,
    `<line x1="0" y1="0" x2="0" y2="3.6" stroke="${WOOD}" stroke-width="0.6" stroke-linecap="round"/>`,
    `<rect x="-1.2" y="3.3" width="2.4" height="1.2" rx="0.2" fill="${IRON}"/></g>`,
    `<g class="hit ${side}">${sparks}${hot ? embers : ''}</g>`,
  ].join('')
}

// Hyped, between strikes the left claw wipes its brow and a drop flies off;
// from frenzy it takes a second hammer to a second block.
const FLING = `<path class="fling" d="M3 9 q-1 1.6 0 2.2 q1 -0.6 0 -2.2z" fill="${SWEAT}"/>`

const workingExtras = (level: Level): string => {
  const job = station('r', level === 4) + (level >= 3 ? station('l', level === 4) : '') + (level === 2 ? FLING : '')

  switch (level) {
    case 0:
      return job
    case 1:
      return job + sweat(18.4, 'drip')
    case 2:
      return job + STEAM + sweat(18.4, 'drip')
    case 3:
      return job + spark(2, 7, 0) + spark(19.5, 8, 0.2) + spark(11, 3.5, 0.4) + spark(16, 5, 0.1) +
        sweat(18.4, 'drip') + sweat(3.4, 'drip2')
    case 4:
      return job + bang(11, 2.6) + STEAM
  }
}

const thinkingExtras = (level: Level): string => {
  switch (level) {
    case 0:
      return thinkingDots
    case 1:
      return thinkingDots + sweat(18.4, 'drip')
    case 2:
      return GEARS + STEAM + sweat(18.4, 'drip')
    case 3:
      return BOLTS + spark(2, 7, 0) + spark(19.5, 8, 0.3) + sweat(18.4, 'drip') + sweat(3.4, 'drip2')
    case 4:
      return RAYS + bang(11, -0.6) + spark(2, 7, 0) + spark(20, 9, 0.3)
  }
}

// The factory's smoke grows with the pace; from hyped it shows money, from
// frenzy it burns it.
const backgroundExtras = (level: Level): string => {
  switch (level) {
    case 0:
      return CRANK + smoke(2, STEEL, 0.8)
    case 1:
      return CRANK + smoke(2, STEEL, 0.8) + sweat(3.4, 'drip')
    case 2:
      return CRANK + smoke(4, INK, 1.1) + inFurnace(2) + sweat(3.4, 'drip')
    case 3:
      return CRANK + smoke(6, IRON, 1.3) + inFurnace(4) + burning(4) + spark(2, 7, 0) + spark(23.4, 12, 0.3) +
        sweat(3.4, 'drip') + sweat(18.4, 'drip2')
    case 4:
      return CRANK + smoke(6, IRON, 1.3) + CHIMNEY_FIRE + inFurnace(4) + burning(8) + coins(4) + bang(8, 2.6) +
        spark(2, 7, 0) + spark(23.4, 12, 0.3)
  }
}

const QUESTION = askMark('?', 12.6, 7.2, 6, CORAL, 'ask')

// The magnifying glass, in its own units: the claw grips it at the origin and
// the lens sits up and to the left. The stylesheet carries it from beside the
// crab's head to its right eye and back.
const LENS = [
  `<g class="lens" shape-rendering="geometricPrecision">`,
  `<line x1="0.3" y1="0.3" x2="-3.4" y2="-3.4" stroke="${WOOD}" stroke-width="0.8" stroke-linecap="round"/>`,
  `<circle cx="-5" cy="-5" r="2.2" fill="#CFE3F2" fill-opacity="0.35" stroke="${IRON}" stroke-width="0.6"/>`,
  `<path d="M-6.4 -5.4 Q-6.1 -6.3 -5.2 -6.5" fill="none" stroke="${PAPER}" stroke-width="0.4" stroke-linecap="round"/>`,
  `</g>`,
].join('')

// What the lens shows over the right eye: the eye, twice its size, and it blinks.
const ZOOM = [
  `<clipPath id="lens-in"><circle cx="13.5" cy="11" r="2"/></clipPath>`,
  `<g class="zoom" clip-path="url(#lens-in)">`,
  `<circle cx="13.5" cy="11" r="2" fill="${CORAL}"/>`,
  `<g class="beye">${rect(12.5, 9.2, 2, 3.6, EYE)}${rect(12.75, 9.5, 0.7, 0.7, PAPER)}</g>`,
  `</g>`,
].join('')

const GLASS = ZOOM + LENS + askMark('?', 7.4, 7.4, 5, CORAL, 'pop')

// Calm and busy, the crab looks itself in the eye through the glass, then
// asks; hurrying, the question mark grows into more of them.
const waitingExtras = (level: Level): string => {
  switch (level) {
    case 0:
      return GLASS
    case 1:
      return GLASS + sweat(18.4, 'drip')
    case 2:
      return QUESTION + askMark('?', 16.8, 4.4, 4.5, CORAL, 'ask') + STEAM + sweat(18.4, 'drip')
    case 3:
      return askMark('?!', 12, 7.2, 6, RED, 'ask') + spark(2, 7, 0) + spark(19.5, 8, 0.3) +
        sweat(18.4, 'drip') + sweat(3.4, 'drip2')
    case 4:
      return SIREN + askMark('?!', 12, 7.2, 6, RED, 'ask') + spark(2, 7, 0) + spark(20, 9, 0.3)
  }
}

// Awake after a turn: nothing calm, a drop of sweat busy, steam hyped, sparks
// from frenzy; the stylesheet does the rest, faster with the pace.
const readyExtras = (level: Level): string => {
  switch (level) {
    case 0:
      return ''
    case 1:
      return sweat(18.4, 'drip')
    case 2:
      return STEAM + sweat(18.4, 'drip')
    case 3:
      return spark(2, 7, 0) + spark(19.5, 8, 0.3) + sweat(18.4, 'drip') + sweat(3.4, 'drip2')
    case 4:
      return bang(11, 2.6) + spark(2, 7, 0) + spark(20, 9, 0.3)
  }
}

const severalExtras = (count: number, level: Level): string => {
  switch (level) {
    case 0:
      return badge(count)
    case 1:
      return badge(count) + sweat(18.4, 'drip')
    case 2:
      return badge(count) + STEAM + sweat(18.4, 'drip')
    case 3:
      return badge(count) + spark(2, 7, 0) + spark(19.5, 8, 0.3) +
        sweat(18.4, 'drip') + sweat(3.4, 'drip2')
    case 4:
      return badge(count) + spark(2, 7, 0) + spark(20, 9, 0.3)
  }
}

// What floats above the crab or beside it, in the cell's own units (the crab
// stands at y 5).
const extras = (mood: Mood, count: number, level: Level, cooling: boolean): string => {
  if (cooling) return sweat(18.4, 'drip') + sweat(3.4, 'drip2')

  switch (mood) {
    case 'idle':
      return ZZZ
    case 'ready':
      return readyExtras(level)
    case 'thinking':
      return thinkingExtras(level)
    case 'working':
      return workingExtras(level)
    case 'several':
      return severalExtras(count, level)
    case 'background':
      return backgroundExtras(level)
    case 'waiting':
      return waitingExtras(level)
  }
}

const STYLE = `
g { transform-box: fill-box; transform-origin: center; }
.spk, .puff, .puff2, .beye, .pop { transform-box: fill-box; transform-origin: center; }
@keyframes up { 0%, 100% { transform: translateY(0) } 50% { transform: translateY(-1.5px) } }
@keyframes lift { 0%, 100% { transform: translateY(0) } 50% { transform: translateY(-0.6px) } }
@keyframes blink { 0%, 94%, 100% { transform: scaleY(1) } 97% { transform: scaleY(0.1) } }
@keyframes pulse { 0%, 100% { opacity: 0.25 } 50% { opacity: 1 } }
@keyframes bob { 0%, 100% { transform: translateY(0) } 50% { transform: translateY(-0.7px) } }
@keyframes wave { 0%, 100% { transform: rotate(-18deg) translateY(-1px) } 50% { transform: rotate(18deg) translateY(-1px) } }
@keyframes wavew { 0%, 100% { transform: rotate(-18deg) translateY(-2px) } 50% { transform: rotate(18deg) translateY(-2px) } }
@keyframes wavel { 0%, 100% { transform: rotate(18deg) translateY(-2px) } 50% { transform: rotate(-18deg) translateY(-2px) } }
@keyframes hop { 0%, 50%, 100% { transform: translateY(0) } 25%, 75% { transform: translateY(-1.6px) } }
@keyframes snap { 0%, 84%, 88%, 92%, 100% { transform: translateX(0) } 86%, 90% { transform: translateX(1px) } }

.ready .eyes, .thinking .eyes, .working .eyes, .background .eyes, .waiting .eyes, .several .eyes {
  animation: blink 4s infinite;
}
.pin { animation: snap 5s steps(1) infinite; }

/* Awake after a turn, waiting on you: it bobs, taps its feet, looks left,
   right and down at the prompt, and now and then beckons with its left claw,
   all faster with the pace; from frenzy it hops. */
@keyframes lookabout {
  0%, 30% { transform: translate(0, 0) } 31%, 45% { transform: translate(-0.7px, 0) }
  46%, 55% { transform: translate(0, 0) } 56%, 70% { transform: translate(0.7px, 0) }
  71%, 90% { transform: translate(0, 0.6px) } 91%, 100% { transform: translate(0, 0) }
}
@keyframes beckon {
  0%, 70%, 80%, 90%, 100% { transform: rotate(0) translateY(0) }
  75%, 85% { transform: rotate(-28deg) translateY(-1px) }
}
.ready .crab { animation: bob var(--rb) ease-in-out infinite; }
.ready .fol { animation: lookabout var(--la) steps(1) infinite; }
.ready .cl { animation: beckon var(--bk) ease-in-out infinite; }
.ready .legs-a { animation: lift var(--rt) steps(1) infinite; }
.ready .legs-b { animation: lift var(--rt) steps(1) infinite calc(var(--rt) / 2); }
svg.ready:hover .cl { animation: wavel 0.4s ease-in-out infinite; }

/* Asleep: tucked in, breathing slowly, z's drifting up; now and then the
   right claw twitches, and its top jaw snaps. */
@keyframes breathe { 0%, 100% { transform: scaleY(1) } 50% { transform: scaleY(1.07) } }
@keyframes twitch { 0%, 88%, 91%, 94%, 100% { transform: translateY(0) } 89%, 92% { transform: translateY(-1px) } }
@keyframes snapdown { 0%, 84%, 88%, 92%, 100% { transform: translateY(0) } 86%, 90% { transform: translateY(1px) } }
@keyframes drift { 0% { opacity: 0; transform: translate(0, 0) } 15%, 85% { opacity: 1 } 100% { opacity: 0; transform: translate(3px, -6px) } }
.idle .body { transform-origin: 50% 100%; animation: breathe 3.6s ease-in-out infinite; }
.idle .cr { animation: twitch 7s steps(1) infinite; }
.idle .pin { animation: snapdown 5s steps(1) infinite; }
.idle .zz { animation: drift 4.5s ease-out infinite; }
.idle .zz2 { animation-delay: -1.5s; }
.idle .zz3 { animation-delay: -3s; }

/* Thinking: it paces sideways there and back, claw on its chin (shaded, so it
   shows in front of the body), eyes looking where it goes. */
@keyframes walk { 0%, 100% { transform: translateX(-2.5px) } 50% { transform: translateX(2.5px) } }
@keyframes glance { 0%, 49% { transform: translateX(0.6px) } 50%, 100% { transform: translateX(-0.6px) } }
@keyframes tapc { 0%, 100% { transform: translate(-2px, 2px) } 50% { transform: translate(-2px, 0.8px) } }
.walk { animation: walk var(--wk) ease-in-out infinite; }
.thinking .cr { transform: translate(-2px, 2px); filter: brightness(0.78); }
.thinking .fol { animation: glance var(--wk) steps(1) infinite; }
.thinking .legs-a { animation: lift calc(var(--wk) / 12) steps(1) infinite; }
.thinking .legs-b { animation: lift calc(var(--wk) / 12) steps(1) infinite calc(var(--wk) / 24); }
.thinking .dot { animation: pulse var(--d) ease-in-out infinite; }
.thinking .d2 { animation-delay: calc(var(--d) / 6); }
.thinking .d3 { animation-delay: calc(var(--d) / 3); }
.thinking.tap .cr { animation: tapc 0.4s steps(1) infinite; }

/* Working: it hammers a nail, sparks on each strike, the nail sinking; hyped it
   wipes its brow between strikes; from frenzy two hammers strike in turn. */
@keyframes swing { 0% { transform: translate(19.5px, 6px) rotate(-150deg) } 55% { transform: translate(19.5px, 5.4px) rotate(-165deg) } 80% { transform: translate(19.5px, 6.4px) rotate(-27deg) } 86% { transform: translate(19.5px, 6.2px) rotate(-38deg) } 100% { transform: translate(19.5px, 6px) rotate(-150deg) } }
@keyframes swingl { 0% { transform: translate(2.5px, 6px) rotate(150deg) } 55% { transform: translate(2.5px, 5.4px) rotate(165deg) } 80% { transform: translate(2.5px, 6.4px) rotate(27deg) } 86% { transform: translate(2.5px, 6.2px) rotate(38deg) } 100% { transform: translate(2.5px, 6px) rotate(150deg) } }
@keyframes strike { 0%, 100% { transform: translateY(-1px) } 55% { transform: translateY(-1.6px) } 80% { transform: translateY(0.4px) } }
@keyframes hit { 0%, 79% { opacity: 0; transform: scale(0.5) } 80%, 88% { opacity: 1; transform: scale(1.2) } 89%, 100% { opacity: 0 } }
@keyframes sink { 0% { transform: translateY(0) } 100% { transform: translateY(1.6px) } }
@keyframes thump { 0%, 79%, 100% { transform: translateY(0) } 82% { transform: translateY(0.4px) } }
@keyframes turns { 0%, 29%, 80%, 100% { transform: translateX(0.6px) } 30%, 79% { transform: translateX(-0.6px) } }
@keyframes wipe { 0%, 35%, 85%, 100% { transform: translate(0, 0); filter: none } 50% { transform: translate(4px, 3.4px); filter: brightness(0.78) } 65% { transform: translate(8px, 3.4px); filter: brightness(0.78) } 75% { transform: translate(1px, 0.5px); filter: none } }
@keyframes fling { 0%, 74% { opacity: 0; transform: translate(0, 0) } 76% { opacity: 1; transform: translate(0, 0) } 100% { opacity: 0; transform: translate(-3px, 2px) } }
.ham { transform-box: view-box; transform-origin: 0 0; transform: translate(19.5px, 6px) rotate(-150deg); }
.ham.l { transform: translate(2.5px, 6px) rotate(150deg); }
.hit, .fling { opacity: 0; }
.hit { transform-box: fill-box; transform-origin: center; }
.hm .ham { animation: swing var(--jb) ease-in infinite; }
.hm .ham.l { animation: swingl var(--jb) ease-in infinite calc(var(--jb) / -2); }
.hm .cr, svg.hm:hover .cr { animation: strike var(--jb) ease-in infinite; }
.hm .hit { animation: hit var(--jb) steps(1) infinite; }
.hm .hit.l { animation-delay: calc(var(--jb) / -2); }
.hm .nail { animation: sink calc(var(--jb) * 6) steps(6) infinite; }
.hm .heat { opacity: 0.5; animation: flick 0.2s steps(1) infinite; }
.hm .crab { animation: thump var(--jb) ease-in infinite; }
.hm .fol { transform: translateX(0.6px); }
svg.hm:hover .cl { animation: wavel 0.4s ease-in-out infinite; }
.hy .cl { animation: wipe calc(var(--jb) * 2) ease-in-out infinite; }
.hy .fling { transform-box: fill-box; animation: fling calc(var(--jb) * 2) ease-out infinite; }
.two .cl, svg.two:hover .cl { animation: strike var(--jb) ease-in infinite calc(var(--jb) / -2); }
.two .crab { animation: thump calc(var(--jb) / 2) ease-in infinite; }
.two .fol { animation: turns var(--jb) steps(1) infinite; }

/* Background work: it cranks its factory, the gauge swinging, the furnace
   glowing, smoke rising; from hyped money tumbles in the furnace, from frenzy
   bills fly out of the chimney and burn, at meltdown the chimney is on fire. */
@keyframes crank { from { transform: translate(20.5px, 6.6px) rotate(0) } to { transform: translate(20.5px, 6.6px) rotate(360deg) } }
@keyframes cranked { ${CRANK_PATH} }
@keyframes needle { 0%, 100% { transform: rotate(-60deg) } 50% { transform: rotate(60deg) } }
@keyframes glow { 0%, 100% { opacity: 0.55 } 50% { opacity: 0.95 } }
@keyframes smk { 0% { opacity: 0; transform: translate(0, 0) scale(0.4) } 15% { opacity: 0.9 } 100% { opacity: 0; transform: translate(var(--dx), -5px) scale(1.6) } }
@keyframes cash { 0%, 100% { transform: translate(0, 0.6px) rotate(-10deg) } 50% { transform: translate(0.4px, -0.6px) rotate(12deg) } }
@keyframes bill { 0% { opacity: 0; transform: translate(0, 0) rotate(0); filter: none } 10% { opacity: 1 } 55% { filter: none } 80% { filter: brightness(0.25) } 100% { opacity: 0; transform: translate(var(--dx), -5.4px) rotate(540deg); filter: brightness(0.2) } }
@keyframes coin { 0% { opacity: 0; transform: translate(0, 0) } 15% { opacity: 1 } 60% { transform: translate(1.4px, -3.4px) } 100% { opacity: 0; transform: translate(2.4px, 1.2px) } }
@keyframes flame { 0%, 100% { transform: scaleY(0.75) } 50% { transform: scaleY(1.25) } }
.arm { transform-box: view-box; transform-origin: 0 0; transform: translate(20.5px, 6.6px); }
.ndl { transform-box: view-box; transform-origin: 21.4px 9.6px; }
.smk, .bill, .cash { transform-box: fill-box; transform-origin: center; }
.coin { transform-box: fill-box; }
.cf { transform-box: fill-box; transform-origin: 50% 100%; }
.background .arm { animation: crank calc(var(--run) * 4) linear infinite; }
.background .cr, svg.background:hover .cr { animation: cranked calc(var(--run) * 4) linear infinite; }
.background .cl { animation: up calc(var(--run) * 4) steps(1) infinite; }
.background .fol { transform: translateX(0.6px); }
.background .ndl { animation: needle calc(var(--run) * 4) ease-in-out infinite; }
.background .glow { animation: glow calc(var(--run) * 3) ease-in-out infinite; }
.background .smk { animation: smk var(--sm) ease-out infinite; }
.background .cash { animation: cash calc(var(--run) * 2) ease-in-out infinite; }
.background .bill { animation: bill var(--mn) ease-out infinite; }
.background .coin { animation: coin var(--mn) ease-out infinite; }
.background .cf { animation: flame 0.18s steps(1) infinite; }
svg.background:hover .cl { animation: wavel 0.4s ease-in-out infinite; }

/* Several things: it conducts them, a bar of four beats; the left claw keeps
   time, the eyes follow the baton, the badge bounces. */
@keyframes beat { 0% { transform: translate(0, -1px) rotate(0) } 25% { transform: translate(0, 1px) rotate(8deg) } 50% { transform: translate(-1.6px, 0) rotate(-12deg) } 75% { transform: translate(1px, 0) rotate(14deg) } 100% { transform: translate(0, -1px) rotate(0) } }
@keyframes follow { 0% { transform: translate(0.4px, -0.4px) } 25% { transform: translate(0.4px, 0.3px) } 50% { transform: translate(-0.4px, 0) } 75% { transform: translate(0.6px, 0) } 100% { transform: translate(0.4px, -0.4px) } }
.cond .crab { animation: bob var(--bar) ease-in-out infinite; }
.cond .cr, svg.cond:hover .cr { animation: beat var(--bar) ease-in-out infinite; }
.cond .cl { animation: up calc(var(--bar) / 4) steps(1) infinite; }
.cond .fol { animation: follow var(--bar) steps(4) infinite; }
.cond .badge { animation: bob calc(var(--bar) / 2) ease-in-out infinite; }
svg.cond:hover .cl { animation: wavel 0.4s ease-in-out infinite; }

/* Waiting for you: calm and busy, it looks itself in the eye through a
   magnifying glass, then a ? pops up; busy, the look is nervous. Hurrying, it
   waves, taps its foot, hops, jumps with both claws and sounds a siren. */
@keyframes mgl { 0%, 12%, 82%, 100% { transform: translate(19.5px, 4px) rotate(-15deg) } 28%, 66% { transform: translate(18.5px, 6px) rotate(-90deg) } }
@keyframes mgc { 0%, 12%, 82%, 100% { transform: translate(0, -2px) } 28%, 66% { transform: translate(-1px, 0) } }
@keyframes zoom { 0%, 27% { opacity: 0; transform: scale(0.45) } 36%, 63% { opacity: 1; transform: scale(1) } 68%, 100% { opacity: 0; transform: scale(0.45) } }
@keyframes bl { 0%, 47%, 53%, 100% { transform: scaleY(1) } 50% { transform: scaleY(0.1) } }
@keyframes pop { 0%, 82% { opacity: 0; transform: scale(0.3) } 87% { opacity: 1; transform: scale(1.2) } 90%, 96% { opacity: 1; transform: scale(1) } 100% { opacity: 0; transform: scale(1) } }
@keyframes mglx { 0%, 10%, 84%, 100% { transform: translate(19.5px, 4px) rotate(-15deg) } 22% { transform: translate(18px, 6.6px) rotate(-100deg) } 27%, 64% { transform: translate(18.5px, 6px) rotate(-90deg) } 32% { transform: translate(19px, 5.7px) rotate(-90deg) } 36% { transform: translate(18.1px, 6.3px) rotate(-90deg) } 40% { transform: translate(18.8px, 6.4px) rotate(-90deg) } 44% { transform: translate(18px, 5.8px) rotate(-90deg) } 48% { transform: translate(18.9px, 6.2px) rotate(-90deg) } 52% { transform: translate(18.2px, 5.6px) rotate(-90deg) } 56% { transform: translate(19px, 6.1px) rotate(-90deg) } 60% { transform: translate(18.3px, 6.3px) rotate(-90deg) } }
@keyframes mgcx { 0%, 10%, 84%, 100% { transform: translate(0, -2px) } 22% { transform: translate(-1.5px, 0.6px) } 27%, 64% { transform: translate(-1px, 0) } 32% { transform: translate(-0.5px, -0.3px) } 36% { transform: translate(-1.4px, 0.3px) } 40% { transform: translate(-0.7px, 0.4px) } 44% { transform: translate(-1.5px, -0.2px) } 48% { transform: translate(-0.6px, 0.2px) } 52% { transform: translate(-1.3px, -0.4px) } 56% { transform: translate(-0.5px, 0.1px) } 60% { transform: translate(-1.2px, 0.3px) } }
@keyframes zoomx { 0%, 24% { opacity: 0; transform: translate(0, 0) scale(0.45) } 29% { opacity: 1; transform: translate(0, 0) scale(1.3) } 32% { opacity: 1; transform: translate(0.5px, -0.3px) scale(1) } 36% { opacity: 1; transform: translate(-0.4px, 0.3px) scale(1) } 40% { opacity: 1; transform: translate(0.3px, 0.4px) scale(1) } 44% { opacity: 1; transform: translate(-0.5px, -0.2px) scale(1) } 48% { opacity: 1; transform: translate(0.4px, 0.2px) scale(1) } 52% { opacity: 1; transform: translate(-0.3px, -0.4px) scale(1) } 56% { opacity: 1; transform: translate(0.5px, 0.1px) scale(1) } 60% { opacity: 1; transform: translate(-0.2px, 0.3px) scale(1) } 64% { opacity: 1; transform: translate(0, 0) scale(1) } 68%, 100% { opacity: 0; transform: translate(0, 0) scale(0.45) } }
@keyframes blx { 0% { transform: scaleY(1) } 42% { transform: scaleY(0.1) } 45% { transform: scaleY(1) } 50% { transform: scaleY(0.1) } 53% { transform: scaleY(1) } }
@keyframes popx { 0%, 84% { opacity: 0; transform: scale(0.3) } 88% { opacity: 1; transform: scale(1.5) } 91%, 97% { opacity: 1; transform: scale(1) } 100% { opacity: 0; transform: scale(1) } }
.waiting .cr { transform: translateY(-2px); }
.waiting .ask { animation: bob var(--q) ease-in-out infinite; }
.lens { transform-box: view-box; transform-origin: 0 0; transform: translate(19.5px, 4px) rotate(-15deg); }
.zoom { opacity: 0; }
.mg .lens { animation: mgl var(--g) ease-in-out infinite; }
.mg .cr, svg.mg:hover .cr { animation: mgc var(--g) ease-in-out infinite; }
.mg .zoom { animation: zoom var(--g) ease-in-out infinite; }
.mg .beye { animation: bl var(--g) steps(1) infinite; }
.mg .pop { animation: pop var(--g) ease-out infinite; }
.mgx .lens { animation: mglx var(--g) ease-in-out infinite; }
.mgx .cr, svg.mgx:hover .cr { animation: mgcx var(--g) ease-in-out infinite; }
.mgx .zoom { animation: zoomx var(--g) linear infinite; }
.mgx .beye { animation: blx var(--g) steps(1) infinite; }
.mgx .pop { animation: popx var(--g) ease-out infinite; }
svg.mg:hover .cl, svg.mgx:hover .cl { animation: wavel 0.4s ease-in-out infinite; }
.wv .cr { animation: wavew var(--w) ease-in-out infinite; }
.both .cl { animation: wavel var(--w) ease-in-out infinite; }
.tf .legs-a { animation: lift var(--tf) steps(1) infinite; }
.tf .legs-b { animation: lift var(--tf) steps(1) infinite calc(var(--tf) / 2); }
.hp .crab { animation: hop var(--h) steps(1) infinite; }
.sir { animation: flick 0.3s steps(1) infinite; }
.sir2 { animation: flick 0.3s steps(1) infinite 0.15s; }

/* The pace, on every mood but sleep. */
@keyframes jit { 0% { transform: translate(0, 0) } 20% { transform: translate(-0.6px, 0.4px) } 40% { transform: translate(0.5px, -0.5px) } 60% { transform: translate(-0.4px, -0.3px) } 80% { transform: translate(0.6px, 0.3px) } 100% { transform: translate(0, 0) } }
@keyframes drip { 0% { transform: translateY(0); opacity: 0 } 20% { opacity: 1 } 100% { transform: translateY(3px); opacity: 0 } }
@keyframes rise { 0% { transform: translateY(0) scale(0.6); opacity: 0.9 } 100% { transform: translateY(-3.5px) scale(1.4); opacity: 0 } }
@keyframes flick { 0%, 100% { opacity: 0.1 } 50% { opacity: 1 } }
@keyframes flash { 0%, 60%, 100% { opacity: 0; transform: scale(0.4) } 30% { opacity: 1; transform: scale(1.4) } }
@keyframes hue { 0% { filter: hue-rotate(0deg) } 100% { filter: hue-rotate(360deg) } }
@keyframes ghl { 0%, 100% { transform: translateX(-2.6px) } 50% { transform: translateX(-1px) } }
@keyframes ghr { 0%, 100% { transform: translateX(2.6px) } 50% { transform: translateX(1px) } }
@keyframes spin { to { transform: rotate(360deg) } }
@keyframes spinr { to { transform: rotate(-360deg) } }
.eyes.spiral { animation: none; }
.sp { animation: spin 0.35s linear infinite; }
.shake.on { animation: jit 0.1s steps(1) infinite; }
.wrap.rb { animation: hue 1.4s linear infinite; }
.gl { animation: ghl 0.25s ease-in-out infinite; }
.gr { animation: ghr 0.25s ease-in-out infinite; }
.drip { animation: drip 1s ease-in infinite; }
.drip2 { animation: drip 1s ease-in infinite 0.5s; }
.puff { animation: rise 0.7s ease-out infinite; }
.puff2 { animation: rise 0.7s ease-out infinite 0.35s; }
.spk { animation: flash 0.6s steps(3) infinite; }
.bang { animation: bob 0.2s ease-in-out infinite; }
.gear { animation: spin 1.2s steps(8) infinite; }
.gear.rev { animation: spinr 1.2s steps(8) infinite; }
.bolt { animation: flick 0.25s steps(1) infinite; }
.bolt2 { animation: flick 0.25s steps(1) infinite 0.12s; }
.ray { animation: flick 0.16s steps(1) infinite; }
.ray2 { animation: flick 0.16s steps(1) infinite 0.08s; }

/* Cooling down: it stands, pants and fans itself. */
@keyframes pant { 0%, 100% { transform: scaleY(1) } 50% { transform: scaleY(1.07) } }
.cool .crab, .cool .cl, .cool .legs-a, .cool .legs-b { animation: none; }
.cool .body { animation: pant 0.8s ease-in-out infinite; }
.cool .cr { animation: wave 0.9s ease-in-out infinite; transform: none; }

svg:hover .cr, svg.tap:hover .cr { animation: wave 0.4s ease-in-out infinite; }

@media (prefers-reduced-motion: reduce) {
  * { animation: none !important; }
  .zz2, .zz3, .smk, .bill, .coin { display: none; }
}
`

// How fast the thought dots pulse.
const THOUGHT_BEAT = ['1.2s', '0.5s', '0.5s', '0.5s', '0.5s'] as const
// The thinking crab: one walk there and back.
const WALK = ['6s', '4s', '3s', '2s', '1.4s'] as const
// The working crab: one hammer strike.
const STRIKE = ['1s', '0.7s', '0.45s', '0.3s', '0.2s'] as const
// The background crab: a quarter turn of the crank, one puff of smoke, one
// bill's flight.
const CRANKING = ['0.75s', '0.5s', '0.35s', '0.2s', '0.12s'] as const
const SMOKE = ['3s', '2.2s', '1.6s', '1.2s', '0.9s'] as const
const MONEY_FLIGHT = ['3s', '3s', '2.4s', '1.6s', '1.1s'] as const
// The waiting crab: one look through the magnifying glass (calm and busy);
// hurrying, how fast the question mark bobs, the claws wave, the feet tap and
// the crab hops.
const LOOK = ['4s', '2.2s', '2.2s', '2.2s', '2.2s'] as const
const ASK = ['1s', '0.5s', '0.35s', '0.25s', '0.2s'] as const
const WAVE = ['1s', '0.8s', '0.4s', '0.25s', '0.2s'] as const
const FOOT = ['0.5s', '0.5s', '0.25s', '0.15s', '0.1s'] as const
const HOP = ['0.5s', '0.5s', '0.5s', '0.3s', '0.2s'] as const

// The ready crab, calm to meltdown: one bob, one look about, one beckon, one
// tap of the feet.
const READY_BOB = ['3s', '1.6s', '0.9s', '0.5s', '0.35s'] as const
const LOOK_ABOUT = ['5s', '3.5s', '2.5s', '1.6s', '1.2s'] as const
const BECKON = ['4s', '3s', '2s', '1.2s', '0.8s'] as const
const READY_TAP = ['1.2s', '0.8s', '0.5s', '0.3s', '0.2s'] as const

// The conductor's bar of four beats: how many things run sets it (2 s for two,
// down to 0.9 s from six), and the pace speeds it up.
const BAR = [2, 2, 2, 1.6, 1.3, 1.1, 0.9]
const SPEED = [1, 1.3, 1.7, 2.2, 3]

export const conductBar = (count: number, level: Level): number =>
  Number((BAR[Math.min(Math.max(count, 0), 6)]! / SPEED[level]!).toFixed(2))

// The SVG for a mood, how many things run, how hard the session works and
// whether the pace just fell back.
export const crabSvg = (mood: Mood, count: number, level: Level = 0, cooling = false): string => {
  const lv: Level = hasPace(mood) ? level : 0
  const cool = canCool(mood) && cooling
  const [coral, shade] = cool ? [CORAL, SHADE] : coats(lv)
  const look = { baton: mood === 'several', tucked: mood === 'idle' }
  // Thinking, the crab paces sideways, its thoughts going with it.
  const walking = mood === 'thinking' && !cool
  const parts = crab(coral, shade, eyesOf(mood, lv, cool), look)
  // The factory stands behind the crab.
  const behind = mood === 'background' ? MACHINE : ''
  const ghosts =
    lv === 4 && !cool
      ? [
          `<g class="gl" opacity="0.3"><g transform="translate(1 5)">${crab(coral, shade, '', look)}</g></g>`,
          `<g class="gr" opacity="0.3"><g transform="translate(1 5)">${crab(coral, shade, '', look)}</g></g>`,
        ].join('')
      : ''
  const act = !cool
  const classes = [
    cool ? 'cool' : mood,
    act && mood === 'working' ? 'hm' : '',
    act && mood === 'working' && lv === 2 ? 'hy' : '',
    act && mood === 'working' && lv >= 3 ? 'two' : '',
    act && mood === 'thinking' && lv >= 1 ? 'tap' : '',
    act && mood === 'several' ? 'cond' : '',
    act && mood === 'several' && lv >= 1 ? 'tf' : '',
    mood === 'waiting' && lv === 0 ? 'mg' : '',
    mood === 'waiting' && lv === 1 ? 'mgx' : '',
    mood === 'waiting' && lv >= 2 ? 'wv' : '',
    mood === 'waiting' && lv >= 1 ? 'tf' : '',
    mood === 'waiting' && lv >= 2 ? 'hp' : '',
    mood === 'waiting' && lv >= 3 ? 'both' : '',
    mood === 'ready' && lv >= 3 ? 'hp' : '',
  ]
    .filter(Boolean)
    .join(' ')
  const vars =
    `--d:${THOUGHT_BEAT[lv]};--wk:${WALK[lv]};--jb:${STRIKE[lv]};` +
    `--run:${CRANKING[lv]};--sm:${SMOKE[lv]};--mn:${MONEY_FLIGHT[lv]};--bar:${conductBar(count, lv)}s;` +
    `--g:${LOOK[lv]};--q:${ASK[lv]};--w:${WAVE[lv]};--tf:${FOOT[lv]};--h:${HOP[lv]};--rb:${READY_BOB[lv]};` +
    `--la:${LOOK_ABOUT[lv]};--bk:${BECKON[lv]};--rt:${READY_TAP[lv]}`

  return (
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${VIEW.x} ${VIEW.y} ${VIEW.w} ${VIEW.h}" ` +
    `shape-rendering="crispEdges" class="${classes}" style="${vars}"><style>${STYLE}</style>` +
    `<g class="shake${lv >= 3 && !cool ? ' on' : ''}">${walking ? '<g class="walk">' : ''}` +
    `<g class="wrap${lv === 4 && !cool ? ' rb' : ''}">` +
    behind +
    ghosts +
    `<g transform="translate(1 5)"><g class="crab">${parts}</g></g></g>` +
    extras(mood, count, lv, cool) +
    `${walking ? '</g>' : ''}</g></svg>`
  )
}

export const crabAlt = (mood: Mood, count: number, level: Level = 0, cooling = false): string => {
  const base = ((): string => {
    switch (mood) {
      case 'idle':
        return 'A crab asleep, tucked in: nothing is running'
      case 'ready':
        return 'A crab awake, tapping its feet and beckoning: your turn'
      case 'thinking':
        return 'A crab pacing, claw on its chin: the model is working'
      case 'working':
        return 'A crab hammering a nail: a tool is running'
      case 'background':
        return level >= 3
          ? 'A crab cranking its factory, burning money: background work is running'
          : 'A crab cranking its factory: background work is running'
      case 'several':
        return `A crab conducting under a badge of ${count}: several things are running`
      case 'waiting':
        return level <= 1
          ? 'A crab looking through a magnifying glass: waiting for your answer'
          : 'A crab with a question mark: waiting for your answer'
    }
  })()

  if (!hasPace(mood)) return base
  if (cooling && canCool(mood)) return `${base} (panting: the pace is falling back)`

  return level === 0 ? base : `${base} (pace: ${LEVEL_NAMES[level]})`
}
