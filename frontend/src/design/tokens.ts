// Status visual-language tokens for canvas consumers (Cytoscape, Leaflet) that
// cannot read CSS custom properties. Keep in lockstep with src/styles/tokens.css.
// Spec: design docs 05/06. THE ONE RULE: dashed = provisional · solid = settled.

export const COLORS = {
  bg: '#0a0c0d',
  surface: '#101315',
  surfaceRaised: '#171b1e',
  hairline: '#22282c',
  hairlineStrong: '#333c42',
  text: '#e6e9ec',
  textDim: '#828c94',
  textFaint: '#525c64',
  live: '#2fb89b',
  history: '#6b757c',
  problem: '#e0704a',
  accent: '#4a9eff',
} as const

// Axis A — status → stroke width + dash pattern + hue-family. Never hue alone.
export const STATUS = {
  confirmed: { width: 2, dash: [] as number[], color: COLORS.live },
  probable: { width: 1.5, dash: [6, 3], color: COLORS.live },
  possible: { width: 1.5, dash: [2, 4], color: COLORS.live },
  contradicted: { width: 2, dash: [], color: COLORS.problem },
  stale: { width: 2, dash: [], color: COLORS.history },
  // insufficient is an answer-level state, not a node status; rendered as a Known Gap.
  insufficient: { width: 1.5, dash: [6, 3], color: COLORS.history },
} as const

// Axis B — freshness → fill alpha (VSUP "confidence fog").
export const FRESHNESS = { fresh: 0.18, aging: 0.07, stale: 0.1 } as const

// Axis D — the lid (cap). dashed = liftable, solid = welded.
export const LID = {
  liftable: { width: 2, dash: [5, 3], color: 'rgba(107,117,124,0.85)' },
  welded: { width: 2.5, dash: [] as number[], color: COLORS.textDim },
} as const

// Axis H — chokepoint halo. MUST stay dashed (candidate only).
export const HALO = { dash: [4, 4], width: 1.5, color: 'rgba(47,184,155,0.55)' } as const

export type StatusKey = keyof typeof STATUS
export type FreshnessKey = keyof typeof FRESHNESS

// family 'problem' at 'fresh' reproduces --fill-problem (rgba(224,112,74,0.18)) — the
// contradicted fill. Kept here so canvas consumers never hardcode a hex.
const FAMILY_RGB = { live: '47,184,155', history: '107,117,124', problem: '224,112,74' } as const

export function fillFor(freshness: FreshnessKey, family: keyof typeof FAMILY_RGB = 'live'): string {
  return `rgba(${FAMILY_RGB[family]},${FRESHNESS[freshness]})`
}
