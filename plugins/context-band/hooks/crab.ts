import type { ActivityItem, Mood } from '../types'

// The band's crab: a small pixel crab, drawn as one SVG per mood, that acts
// out what the session is doing. The desktop and mobile apps run its CSS
// animation; hovered, it waves.

export const CRAB_HEIGHT = 22

const CELL_W = 22
const CELL_H = 16

const CORAL = '#D97757'
const SHADE = '#B65D40'
const EYE = '#2B1D17'
const INK = '#9A8F86'

// What the crab acts out: someone waiting on you first, then how much runs.
export const moodOf = (items: ActivityItem[], isWorking: boolean): Mood => {
  if (items.some(item => item.label === 'Waiting for your answer')) return 'waiting'
  if (items.length === 0) return 'idle'
  if (items.length > 1) return 'several'

  const [only] = items

  if (only?.id === 'turn') return 'thinking'

  return only?.kind === 'tool' || isWorking ? 'working' : 'background'
}

const rect = (x: number, y: number, w: number, h: number, fill: string): string =>
  `<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="${fill}"/>`

const LEFT_CLAW = [
  rect(0, 0, 1, 2, CORAL),
  rect(2, 0, 1, 2, CORAL),
  rect(0, 2, 3, 1, CORAL),
  rect(1, 3, 1, 2, CORAL),
  rect(2, 4, 2, 1, CORAL),
].join('')

const RIGHT_CLAW = [
  rect(19, 0, 1, 2, CORAL),
  rect(17, 0, 1, 2, CORAL),
  rect(17, 2, 3, 1, CORAL),
  rect(18, 3, 1, 2, CORAL),
  rect(16, 4, 2, 1, CORAL),
].join('')

const BODY = [rect(5, 3, 10, 1, CORAL), rect(4, 4, 12, 4, CORAL), rect(5, 8, 10, 1, CORAL)].join('')

const LEGS_A = [rect(5, 9, 1, 2, SHADE), rect(12, 9, 1, 2, SHADE)].join('')
const LEGS_B = [rect(7, 9, 1, 2, SHADE), rect(14, 9, 1, 2, SHADE)].join('')

const EYES_OPEN = [rect(7, 5, 1, 2, EYE), rect(12, 5, 1, 2, EYE)].join('')
const EYES_UP = [rect(7, 4, 1, 2, EYE), rect(12, 4, 1, 2, EYE)].join('')
const EYES_SHUT = [rect(6.5, 6, 2, 0.7, EYE), rect(11.5, 6, 2, 0.7, EYE)].join('')

// One crab, its parts in groups the stylesheet moves.
const crab = (mood: Mood): string => {
  const eyes = mood === 'idle' ? EYES_SHUT : mood === 'thinking' ? EYES_UP : EYES_OPEN

  return [
    `<g class="legs-a">${LEGS_A}</g>`,
    `<g class="legs-b">${LEGS_B}</g>`,
    `<g class="body">${BODY}<g class="eyes">${eyes}</g></g>`,
    `<g class="cl">${LEFT_CLAW}</g>`,
    `<g class="cr">${RIGHT_CLAW}</g>`,
  ].join('')
}

// What floats above the crab, in the cell's own units (the crab stands at y 5).
const extras = (mood: Mood, count: number): string => {
  switch (mood) {
    case 'idle':
      return [
        `<text class="z z1" x="12" y="6.5" font-size="4" font-family="monospace" fill="${INK}">z</text>`,
        `<text class="z z2" x="14.5" y="4" font-size="3" font-family="monospace" fill="${INK}">z</text>`,
      ].join('')
    case 'thinking':
      return [
        `<circle class="dot d1" cx="12.5" cy="6.6" r="0.8" fill="${INK}"/>`,
        `<circle class="dot d2" cx="14.6" cy="4.8" r="0.9" fill="${INK}"/>`,
        `<circle class="dot d3" cx="17" cy="2.6" r="1.1" fill="${INK}"/>`,
      ].join('')
    case 'background':
      // An hourglass above the crab's back that turns over.
      return [
        `<g class="glass">`,
        rect(12.5, 1.5, 3.5, 0.7, INK),
        rect(12.5, 6, 3.5, 0.7, INK),
        `<path d="M12.9 2.2 L15.6 2.2 L14.25 4.1 Z" fill="${CORAL}"/>`,
        `<path d="M14.25 4.1 L15.6 6 L12.9 6 Z" fill="${INK}" opacity="0.6"/>`,
        `</g>`,
      ].join('')
    case 'waiting':
      return `<text class="ask" x="12.6" y="7.2" font-size="6" font-weight="bold" font-family="monospace" fill="${CORAL}">?</text>`
    case 'several': {
      // A badge over the crab's back, between its claws, with how many things run, as an app
      // icon's: the crab itself stays one.
      const text = count > 9 ? '9+' : String(count)

      return [
        `<g class="badge" shape-rendering="geometricPrecision">`,
        `<circle cx="11" cy="4.4" r="3.4" fill="#FAF9F5" stroke="${CORAL}" stroke-width="0.7"/>`,
        `<text x="11" y="5.85" text-anchor="middle" font-size="${text.length > 1 ? 3.2 : 4.2}" `,
        `font-weight="bold" font-family="-apple-system, system-ui, sans-serif" fill="${SHADE}">${text}</text>`,
        `</g>`,
      ].join('')
    }
    default:
      return ''
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

.idle .body { animation: breathe 3s ease-in-out infinite; }
.idle .z { animation: float 3s ease-out infinite; }
.idle .z2 { animation-delay: 1.5s; }

.thinking .eyes, .working .eyes, .background .eyes, .waiting .eyes, .several .eyes {
  animation: blink 4s infinite;
}
.thinking .cr { transform: translate(-2px, 2px); }
.thinking .dot { animation: pulse 1.2s ease-in-out infinite; }
.thinking .d2 { animation-delay: 0.2s; }
.thinking .d3 { animation-delay: 0.4s; }

.working .crab, .several .crab {
  animation: side 0.6s steps(1) 5, bob 2.4s ease-in-out 3s infinite;
}
.working .cl, .several .cl { animation: up 0.3s steps(1) 10; }
.working .cr, .several .cr { animation: up 0.3s steps(1) 10 0.15s; }
.working .legs-a, .several .legs-a { animation: lift 0.3s steps(1) 10; }
.working .legs-b, .several .legs-b { animation: lift 0.3s steps(1) 10 0.15s; }

.background .cl { animation: tap 1.2s infinite; }
.background .glass { animation: flip 4s ease-in-out infinite; }

.waiting .cr { transform: translateY(-2px); }
.waiting .ask { animation: bob 1s ease-in-out infinite; }

svg:hover .cr { animation: wave 0.4s ease-in-out infinite; }

@media (prefers-reduced-motion: reduce) {
  * { animation: none !important; }
}
`

// The SVG for a mood. Working, the crab dances for three seconds and then
// bobs slowly: the dance plays again only when the SVG changes, that is when
// the mood or the count does, so a new state is noticed and a long one is
// not distracting.
export const crabSvg = (mood: Mood, count: number): string =>
  `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${CELL_W} ${CELL_H}" ` +
  `shape-rendering="crispEdges" class="${mood}"><style>${STYLE}</style>` +
  `<g transform="translate(1 5)"><g class="crab">${crab(mood)}</g></g>` +
  extras(mood, count) +
  `</svg>`

export const CRAB_WIDTH = Math.round((CELL_W * CRAB_HEIGHT) / CELL_H)

export const crabAlt = (mood: Mood, count: number): string => {
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
}
