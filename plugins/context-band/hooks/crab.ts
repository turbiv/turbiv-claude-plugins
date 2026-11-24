import type { ActivityItem, Level, Mood } from '../types'

// The band's crab: a small pixel crab, drawn as one SVG per mood, that acts
// out what the session is doing. The desktop and mobile apps run its CSS
// animation; hovered, it waves.
//
// Awake, it also acts out how hard the session works (the pace, from 0 calm to
// 4 meltdown): faster, redder, sweating, then juggling, burning and leaving
// ghosts. The working, thinking and several-things crabs pant for a few seconds
// when the pace falls back from a burst.

// The drawing's box, in the cell's own units: the crab stands in the 22 x 16
// cell, and the margin around it holds what the higher levels add (speed
// lines, sparks, the flames and rays above). The crab keeps the size it had.
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

const LEVEL_NAMES = ['calm', 'busy', 'hyped', 'frenzy', 'meltdown'] as const

// What the crab acts out: someone waiting on you first, then how much runs.
export const moodOf = (items: ActivityItem[], isWorking: boolean): Mood => {
  if (items.some(item => item.label === 'Waiting for your answer')) return 'waiting'
  if (items.length === 0) return 'idle'
  if (items.length > 1) return 'several'

  const [only] = items

  if (only?.id === 'turn') return 'thinking'

  return only?.kind === 'tool' || isWorking ? 'working' : 'background'
}

// The pace shows on every mood but sleep: a crab that waits for your answer
// right after a burst of work is still wound up. Only the moods that spend
// tokens themselves pant when the pace falls back from a burst.
const hasPace = (mood: Mood): boolean => mood !== 'idle'

const canCool = (mood: Mood): boolean =>
  mood === 'working' || mood === 'thinking' || mood === 'several'

const rect = (x: number, y: number, w: number, h: number, fill: string, cls = ''): string =>
  `<rect${cls === '' ? '' : ` class="${cls}"`} x="${x}" y="${y}" width="${w}" height="${h}" fill="${fill}"/>`

const coats = (level: Level): [string, string] =>
  level >= 3 ? [RED, RED_SHADE] : level === 2 ? [HOT, HOT_SHADE] : [CORAL, SHADE]

const EYES_OPEN = [rect(7, 5, 1, 2, EYE), rect(12, 5, 1, 2, EYE)].join('')
const EYES_UP = [rect(7, 4, 1, 2, EYE), rect(12, 4, 1, 2, EYE)].join('')
const EYES_SHUT = [rect(6.5, 6, 2, 0.7, EYE), rect(11.5, 6, 2, 0.7, EYE)].join('')
// Worried brows over the eyes: busy and hyped.
const BROWS = [rect(6.4, 4.2, 2.2, 0.5, EYE), rect(11.4, 4.2, 2.2, 0.5, EYE)].join('')
const BROWS_UP = [rect(6.4, 3.3, 2.2, 0.5, EYE), rect(11.4, 3.3, 2.2, 0.5, EYE)].join('')

const spiral = (x: number): string =>
  `<g class="sp">${rect(x, 5, 2, 2, '#FAF9F5')}${rect(x, 5, 1, 1, EYE)}${rect(x + 1, 6, 1, 1, EYE)}</g>`

const eyesOf = (mood: Mood, level: Level, cooling: boolean): string => {
  if (cooling || mood === 'idle') return `<g class="eyes">${EYES_SHUT}</g>`
  if (hasPace(mood) && level >= 3) return `<g class="eyes spiral">${spiral(6.5)}${spiral(11.5)}</g>`

  const brows = hasPace(mood) && level >= 1
  const up = mood === 'thinking'

  return `<g class="eyes">${up ? EYES_UP : EYES_OPEN}${brows ? (up ? BROWS_UP : BROWS) : ''}</g>`
}

// One crab, its parts in groups the stylesheet moves.
const crab = (coral: string, shade: string, eyes: string): string => {
  const leftClaw = [
    rect(0, 0, 1, 2, coral),
    rect(2, 0, 1, 2, coral),
    rect(0, 2, 3, 1, coral),
    rect(1, 3, 1, 2, coral),
    rect(2, 4, 2, 1, coral),
  ].join('')
  const rightClaw = [
    rect(19, 0, 1, 2, coral),
    rect(17, 0, 1, 2, coral),
    rect(17, 2, 3, 1, coral),
    rect(18, 3, 1, 2, coral),
    rect(16, 4, 2, 1, coral),
  ].join('')
  const body = [rect(5, 3, 10, 1, coral), rect(4, 4, 12, 4, coral), rect(5, 8, 10, 1, coral)].join('')
  const legsA = [rect(5, 9, 1, 2, shade), rect(12, 9, 1, 2, shade)].join('')
  const legsB = [rect(7, 9, 1, 2, shade), rect(14, 9, 1, 2, shade)].join('')

  return [
    `<g class="legs-a">${legsA}</g>`,
    `<g class="legs-b">${legsB}</g>`,
    `<g class="body">${body}${eyes}</g>`,
    `<g class="cl">${leftClaw}</g>`,
    `<g class="cr">${rightClaw}</g>`,
  ].join('')
}

const sweat = (x: number, cls: string): string =>
  `<path class="${cls}" d="M${x} 8 q-1 1.6 0 2.2 q1 -0.6 0 -2.2z" fill="${SWEAT}"/>`

const STEAM = [
  `<circle class="puff" cx="3" cy="6" r="1" fill="#C9C2BB"/>`,
  `<circle class="puff2" cx="20" cy="6" r="1" fill="#C9C2BB"/>`,
].join('')

const SPEED_LINES = [
  rect(-2.5, 9, 2.4, 0.5, INK, 'spd'),
  rect(-2.5, 11, 2.4, 0.5, INK, 'spd2'),
  rect(-2.5, 13, 2.4, 0.5, INK, 'spd'),
].join('')

const spark = (x: number, y: number, delay: number): string =>
  `<rect class="spk" style="animation-delay:${delay}s" x="${x}" y="${y}" width="0.9" height="0.9" fill="${GOLD}"/>`

const bang = (x: number, y: number): string =>
  `<text class="bang" x="${x}" y="${y}" text-anchor="middle" font-size="4" font-weight="bold" font-family="-apple-system, system-ui, sans-serif" fill="${RED}">!!</text>`

const FLAMES = [
  `<path class="fl" d="M6 8 L7.4 3.6 L8.8 8z" fill="#F28C28"/>`,
  `<path class="fl2" d="M8.4 8 L10 2.4 L11.6 8z" fill="${GOLD}"/>`,
  `<path class="fl" d="M11.4 8 L13 3 L14.6 8z" fill="#F28C28"/>`,
  `<path class="fl2" d="M14 8 L15.2 4.4 L16.4 8z" fill="${GOLD}"/>`,
].join('')

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
    rect(2, 2, 1, 1, '#FAF9F5'),
  ].join('')

const GEARS = [
  `<g transform="translate(10 0.5)"><g class="gear">${gear(INK)}</g></g>`,
  `<g transform="translate(14.4 3)"><g class="gear rev">${gear(CORAL)}</g></g>`,
].join('')

const BALL_COLORS = [CORAL, SWEAT, GOLD, '#7BC47F', '#B38BE0', '#F28C8C']

// Balls that circle above the crab's back, so it looks to be juggling.
const balls = (n: number): string =>
  Array.from(
    { length: n },
    (_, i) =>
      `<circle class="ball" style="animation-delay:calc(var(--p) * -${(i / n).toFixed(3)})" ` +
      `cx="11" cy="4.4" r="0.95" fill="${BALL_COLORS[i % BALL_COLORS.length]}"/>`,
  ).join('')

const badge = (count: number): string => {
  const text = count > 9 ? '9+' : String(count)

  return [
    `<g class="badge" shape-rendering="geometricPrecision">`,
    `<circle cx="11" cy="4.4" r="3.4" fill="#FAF9F5" stroke="${CORAL}" stroke-width="0.7"/>`,
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

// A small hourglass, centred on the origin, for the juggling crab.
const hourglass = (): string =>
  [
    rect(-1.3, -1.7, 2.6, 0.5, INK),
    rect(-1.3, 1.2, 2.6, 0.5, INK),
    `<path d="M-1.1 -1.2 L1.1 -1.2 L0 0 Z" fill="${CORAL}"/>`,
    `<path d="M0 0 L1.1 1.2 L-1.1 1.2 Z" fill="${INK}" opacity="0.6"/>`,
  ].join('')

// Hourglasses that circle above the crab's back, each turning over as it goes.
const hourglasses = (n: number): string =>
  `<g transform="translate(11 4.4)">` +
  Array.from(
    { length: n },
    (_, i) =>
      `<g class="ob" style="animation-delay:calc(var(--p) * -${(i / n).toFixed(3)})">` +
      `<g class="flp">${hourglass()}</g></g>`,
  ).join('') +
  `</g>`

// What a calm crab shows over its head or beside it, per mood.
const thinkingDots = [
  `<circle class="dot d1" cx="12.5" cy="6.6" r="0.8" fill="${INK}"/>`,
  `<circle class="dot d2" cx="14.6" cy="4.8" r="0.9" fill="${INK}"/>`,
  `<circle class="dot d3" cx="17" cy="2.6" r="1.1" fill="${INK}"/>`,
].join('')

const workingExtras = (level: Level): string => {
  switch (level) {
    case 0:
      return ''
    case 1:
      return sweat(18.4, 'drip')
    case 2:
      return STEAM + SPEED_LINES + sweat(18.4, 'drip')
    case 3:
      return spark(2, 7, 0) + spark(19.5, 8, 0.2) + spark(11, 3.5, 0.4) + spark(16, 5, 0.1) +
        sweat(18.4, 'drip') + sweat(3.4, 'drip2')
    case 4:
      return FLAMES + bang(11, 2.6) + spark(2, 7, 0) + spark(20, 9, 0.3)
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

// The hourglass the crab watches: one at calm and busy (turned faster, by the
// stylesheet), then juggled.
const backgroundExtras = (level: Level): string => {
  const glass = [
    `<g class="glass">`,
    rect(12.5, 1.5, 3.5, 0.7, INK),
    rect(12.5, 6, 3.5, 0.7, INK),
    `<path d="M12.9 2.2 L15.6 2.2 L14.25 4.1 Z" fill="${CORAL}"/>`,
    `<path d="M14.25 4.1 L15.6 6 L12.9 6 Z" fill="${INK}" opacity="0.6"/>`,
    `</g>`,
  ].join('')

  switch (level) {
    case 0:
      return glass
    case 1:
      return glass + sweat(18.4, 'drip')
    case 2:
      return hourglasses(2) + STEAM
    case 3:
      return hourglasses(3) + spark(2, 7, 0) + spark(19.5, 8, 0.3) +
        sweat(18.4, 'drip') + sweat(3.4, 'drip2')
    case 4:
      return hourglasses(5) + spark(2, 7, 0) + spark(20, 9, 0.3)
  }
}

const QUESTION = askMark('?', 12.6, 7.2, 6, CORAL, 'ask')

// The question mark grows into more of them as the crab hurries.
const waitingExtras = (level: Level): string => {
  switch (level) {
    case 0:
      return QUESTION
    case 1:
      return QUESTION + sweat(18.4, 'drip')
    case 2:
      return QUESTION + askMark('?', 16.8, 4.4, 4.5, CORAL, 'ask') + STEAM + sweat(18.4, 'drip')
    case 3:
      return askMark('?!', 12, 7.2, 6, RED, 'ask') + spark(2, 7, 0) + spark(19.5, 8, 0.3) +
        sweat(18.4, 'drip') + sweat(3.4, 'drip2')
    case 4:
      return SIREN + askMark('?!', 12, 7.2, 6, RED, 'ask') + spark(2, 7, 0) + spark(20, 9, 0.3)
  }
}

const severalExtras = (count: number, level: Level): string => {
  switch (level) {
    case 0:
      return badge(count)
    case 1:
      return badge(count) + sweat(18.4, 'drip')
    case 2:
      return balls(2) + badge(count) + STEAM + SPEED_LINES
    case 3:
      return balls(4) + badge(count) + spark(2, 7, 0) + spark(19.5, 8, 0.3) +
        sweat(18.4, 'drip') + sweat(3.4, 'drip2')
    case 4:
      return balls(6) + badge(count) + spark(2, 7, 0) + spark(20, 9, 0.3)
  }
}

// What floats above the crab, in the cell's own units (the crab stands at y 5).
const extras = (mood: Mood, count: number, level: Level, cooling: boolean): string => {
  if (cooling) return sweat(18.4, 'drip') + sweat(3.4, 'drip2')

  switch (mood) {
    case 'idle':
      return [
        `<text class="z z1" x="12" y="6.5" font-size="4" font-family="monospace" fill="${INK}">z</text>`,
        `<text class="z z2" x="14.5" y="4" font-size="3" font-family="monospace" fill="${INK}">z</text>`,
      ].join('')
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
@keyframes side { 0%, 100% { transform: translateX(-1px) } 50% { transform: translateX(1px) } }
@keyframes up { 0%, 100% { transform: translateY(0) } 50% { transform: translateY(-1.5px) } }
@keyframes lift { 0%, 100% { transform: translateY(0) } 50% { transform: translateY(-0.6px) } }
@keyframes tap { 0%, 70%, 100% { transform: translateY(0) } 80% { transform: translateY(1px) } }
@keyframes breathe { 0%, 100% { transform: translateY(0) } 50% { transform: translateY(0.5px) } }
@keyframes blink { 0%, 94%, 100% { transform: scaleY(1) } 97% { transform: scaleY(0.1) } }
@keyframes float { 0% { transform: translate(0, 1px); opacity: 0 } 30% { opacity: 1 } 100% { transform: translate(1px, -2px); opacity: 0 } }
@keyframes pulse { 0%, 100% { opacity: 0.25 } 50% { opacity: 1 } }
@keyframes flip { 0%, 40% { transform: rotate(0) } 50%, 90% { transform: rotate(180deg) } 100% { transform: rotate(360deg) } }
@keyframes bob { 0%, 100% { transform: translateY(0) } 50% { transform: translateY(-0.7px) } }
@keyframes wave { 0%, 100% { transform: rotate(-18deg) translateY(-1px) } 50% { transform: rotate(18deg) translateY(-1px) } }
@keyframes jit { 0% { transform: translate(0, 0) } 20% { transform: translate(-0.6px, 0.4px) } 40% { transform: translate(0.5px, -0.5px) } 60% { transform: translate(-0.4px, -0.3px) } 80% { transform: translate(0.6px, 0.3px) } 100% { transform: translate(0, 0) } }
@keyframes drip { 0% { transform: translateY(0); opacity: 0 } 20% { opacity: 1 } 100% { transform: translateY(3px); opacity: 0 } }
@keyframes rise { 0% { transform: translateY(0) scale(0.6); opacity: 0.9 } 100% { transform: translateY(-3.5px) scale(1.4); opacity: 0 } }
@keyframes flick { 0%, 100% { opacity: 0.1 } 50% { opacity: 1 } }
@keyframes flash { 0%, 60%, 100% { opacity: 0; transform: scale(0.4) } 30% { opacity: 1; transform: scale(1.4) } }
@keyframes flame { 0%, 100% { transform: scaleY(0.75) } 50% { transform: scaleY(1.25) } }
@keyframes hue { 0% { filter: hue-rotate(0deg) } 100% { filter: hue-rotate(360deg) } }
@keyframes ghl { 0%, 100% { transform: translateX(-2.6px) } 50% { transform: translateX(-1px) } }
@keyframes ghr { 0%, 100% { transform: translateX(2.6px) } 50% { transform: translateX(1px) } }
@keyframes spin { to { transform: rotate(360deg) } }
@keyframes spinr { to { transform: rotate(-360deg) } }
@keyframes hop { 0%, 50%, 100% { transform: translateY(0) } 25%, 75% { transform: translateY(-1.6px) } }
@keyframes wavew { 0%, 100% { transform: rotate(-18deg) translateY(-2px) } 50% { transform: rotate(18deg) translateY(-2px) } }
@keyframes wavel { 0%, 100% { transform: rotate(18deg) translateY(-2px) } 50% { transform: rotate(-18deg) translateY(-2px) } }
@keyframes tapc { 0%, 100% { transform: translate(-2px, 2px) } 50% { transform: translate(-2px, 0.8px) } }
@keyframes pulsebadge { 0%, 100% { transform: scale(1) } 50% { transform: scale(1.18) } }
@keyframes pant { 0%, 100% { transform: scaleY(1) } 50% { transform: scaleY(1.07) } }
@keyframes orbit { 0% { transform: translate(7.5px, 0) } 12.5% { transform: translate(5.3px, 2.1px) } 25% { transform: translate(0, 3px) } 37.5% { transform: translate(-5.3px, 2.1px) } 50% { transform: translate(-7.5px, 0) } 62.5% { transform: translate(-5.3px, -2.1px) } 75% { transform: translate(0, -3px) } 87.5% { transform: translate(5.3px, -2.1px) } 100% { transform: translate(7.5px, 0) } }

.idle .body { animation: breathe 3s ease-in-out infinite; }
.idle .z { animation: float 3s ease-out infinite; }
.idle .z2 { animation-delay: 1.5s; }

.thinking .eyes, .working .eyes, .background .eyes, .waiting .eyes, .several .eyes {
  animation: blink 4s infinite;
}
.thinking .cr { transform: translate(-2px, 2px); }
.thinking .dot { animation: pulse var(--d) ease-in-out infinite; }
.thinking .d2 { animation-delay: calc(var(--d) / 6); }
.thinking .d3 { animation-delay: calc(var(--d) / 3); }

.working .crab, .several .crab {
  animation: side 0.6s steps(1) 5, bob 2.4s ease-in-out 3s infinite;
}
.working .cl, .several .cl { animation: up 0.3s steps(1) 10; }
.working .cr, .several .cr { animation: up 0.3s steps(1) 10 0.15s; }
.working .legs-a, .several .legs-a { animation: lift 0.3s steps(1) 10; }
.working .legs-b, .several .legs-b { animation: lift 0.3s steps(1) 10 0.15s; }

.background .cl { animation: tap var(--tp) infinite; }
.background .glass { animation: flip var(--fl) ease-in-out infinite; }

.waiting .cr { transform: translateY(-2px); }
.waiting .ask { animation: bob var(--q) ease-in-out infinite; }

.fast .crab { animation: side calc(var(--t) * 2) steps(1) infinite; }
.fast .cl { animation: up var(--t) steps(1) infinite; }
.fast .cr { animation: up var(--t) steps(1) infinite calc(var(--t) / 2); }
.fast .legs-a { animation: lift var(--t) steps(1) infinite; }
.fast .legs-b { animation: lift var(--t) steps(1) infinite calc(var(--t) / 2); }
.j .cl { animation: up var(--t) steps(1) infinite; }
.j .cr { animation: up var(--t) steps(1) infinite calc(var(--t) / 2); }
.flp { animation: flip var(--fl) ease-in-out infinite; }
.ob { animation: orbit var(--p) linear infinite; }
.wv .cr { animation: wavew var(--w) ease-in-out infinite; }
.both .cl { animation: wavel var(--w) ease-in-out infinite; }
.tf .legs-a { animation: lift var(--tf) steps(1) infinite; }
.tf .legs-b { animation: lift var(--tf) steps(1) infinite calc(var(--tf) / 2); }
.hp .crab { animation: hop var(--h) steps(1) infinite; }
.sir { animation: flick 0.3s steps(1) infinite; }
.sir2 { animation: flick 0.3s steps(1) infinite 0.15s; }
.thinking.tap .cr { animation: tapc 0.4s steps(1) infinite; }
.fast .badge { animation: pulsebadge 0.5s steps(2) infinite; }

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
.spd { animation: flick 0.18s steps(1) infinite; }
.spd2 { animation: flick 0.18s steps(1) infinite 0.09s; }
.spk { animation: flash 0.6s steps(3) infinite; }
.fl { animation: flame 0.18s steps(1) infinite; transform-origin: 50% 100%; }
.fl2 { animation: flame 0.18s steps(1) infinite 0.09s; transform-origin: 50% 100%; }
.bang { animation: bob 0.2s ease-in-out infinite; }
.gear { animation: spin 1.2s steps(8) infinite; }
.gear.rev { animation: spinr 1.2s steps(8) infinite; }
.bolt { animation: flick 0.25s steps(1) infinite; }
.bolt2 { animation: flick 0.25s steps(1) infinite 0.12s; }
.ray { animation: flick 0.16s steps(1) infinite; }
.ray2 { animation: flick 0.16s steps(1) infinite 0.08s; }
.ball { animation: orbit var(--p) linear infinite; }

.cool .crab, .cool .cl, .cool .legs-a, .cool .legs-b { animation: none; }
.cool .body { animation: pant 0.8s ease-in-out infinite; }
.cool .cr { animation: wave 0.9s ease-in-out infinite; transform: none; }

svg:hover .cr, svg.tap:hover .cr { animation: wave 0.4s ease-in-out infinite; }

@media (prefers-reduced-motion: reduce) {
  * { animation: none !important; }
}
`

// How fast the claws go, how fast the thought dots pulse, how fast the balls
// circle, at each level.
const BEAT = ['0.3s', '0.2s', '0.12s', '0.07s', '0.05s'] as const
const THOUGHT_BEAT = ['1.2s', '0.5s', '0.5s', '0.5s', '0.5s'] as const
const ORBIT = ['3s', '3s', '1.6s', '1s', '0.7s'] as const
// The background crab: how fast it taps and turns its hourglass, how fast the
// juggled ones circle and turn.
const TAP = ['1.2s', '0.5s', '0.3s', '0.3s', '0.3s'] as const
const TURN = ['4s', '1.6s', '1.2s', '0.5s', '0.3s'] as const
const JUGGLE = ['3s', '3s', '2s', '1.2s', '0.8s'] as const
// The waiting crab: how fast the question mark bobs, the claws wave, the feet
// tap and the crab hops.
const ASK = ['1s', '0.5s', '0.35s', '0.25s', '0.2s'] as const
const WAVE = ['1s', '0.8s', '0.4s', '0.25s', '0.2s'] as const
const FOOT = ['0.5s', '0.5s', '0.25s', '0.15s', '0.1s'] as const
const HOP = ['0.5s', '0.5s', '0.5s', '0.3s', '0.2s'] as const

// The SVG for a mood, how hard the session works and whether the pace just
// fell back. Working, the calm crab dances for three seconds and then bobs
// slowly: the dance plays again only when the SVG changes, that is when the
// mood, the count or the level does, so a new state is noticed and a long one
// is not distracting. From level 1 the dance does not stop.
export const crabSvg = (mood: Mood, count: number, level: Level = 0, cooling = false): string => {
  const lv: Level = hasPace(mood) ? level : 0
  const cool = canCool(mood) && cooling
  const [coral, shade] = cool ? [CORAL, SHADE] : coats(lv)
  const parts = crab(coral, shade, eyesOf(mood, lv, cool))
  const ghosts =
    lv === 4 && !cool
      ? [
          `<g class="gl" opacity="0.3"><g transform="translate(1 5)">${crab(coral, shade, '')}</g></g>`,
          `<g class="gr" opacity="0.3"><g transform="translate(1 5)">${crab(coral, shade, '')}</g></g>`,
        ].join('')
      : ''
  const classes = [
    cool ? 'cool' : mood,
    lv >= 1 && !cool && (mood === 'working' || mood === 'several') ? 'fast' : '',
    lv >= 1 && !cool && mood === 'thinking' ? 'tap' : '',
    lv >= 2 && mood === 'background' ? 'j' : '',
    lv >= 1 && mood === 'waiting' ? 'wv tf' : '',
    lv >= 2 && mood === 'waiting' ? 'hp' : '',
    lv >= 3 && mood === 'waiting' ? 'both' : '',
  ]
    .filter(Boolean)
    .join(' ')
  const orbit = mood === 'background' ? JUGGLE[lv] : ORBIT[lv]
  const vars =
    `--t:${BEAT[lv]};--d:${THOUGHT_BEAT[lv]};--p:${orbit};--tp:${TAP[lv]};--fl:${TURN[lv]};` +
    `--q:${ASK[lv]};--w:${WAVE[lv]};--tf:${FOOT[lv]};--h:${HOP[lv]}`

  return (
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${VIEW.x} ${VIEW.y} ${VIEW.w} ${VIEW.h}" ` +
    `shape-rendering="crispEdges" class="${classes}" style="${vars}"><style>${STYLE}</style>` +
    `<g class="shake${lv >= 3 && !cool ? ' on' : ''}"><g class="wrap${lv === 4 && !cool ? ' rb' : ''}">` +
    ghosts +
    `<g transform="translate(1 5)"><g class="crab">${parts}</g></g></g>` +
    extras(mood, count, lv, cool) +
    `</g></svg>`
  )
}

export const crabAlt = (mood: Mood, count: number, level: Level = 0, cooling = false): string => {
  const base = ((): string => {
    switch (mood) {
      case 'idle':
        return 'A crab asleep: nothing is running'
      case 'thinking':
        return 'A crab thinking: the model is working'
      case 'working':
        return 'A crab dancing: a tool is running'
      case 'background':
        return 'A crab watching an hourglass: background work is running'
      case 'several':
        return `A crab with a badge of ${count}: several things are running`
      case 'waiting':
        return 'A crab with a question mark: waiting for your answer'
    }
  })()

  if (!hasPace(mood)) return base
  if (cooling && canCool(mood)) return `${base} (panting: the pace is falling back)`

  return level === 0 ? base : `${base} (pace: ${LEVEL_NAMES[level]})`
}
