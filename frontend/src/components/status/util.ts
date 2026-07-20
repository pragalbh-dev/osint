// Status visual-language helpers — map a status/freshness to the token-backed
// border/fill strings. THE ONE RULE: dashed = provisional · solid = settled.
// Status is border style + fill value, NEVER hue.

import type { Status } from '@/api/types'

export type StatusLike = Status | 'known-gap'
export type Freshness = 'fresh' | 'aging' | 'stale'

export function statusBorder(status: StatusLike): string {
  switch (status) {
    case 'confirmed':
      return 'var(--border-confirmed)'
    case 'probable':
      return 'var(--border-probable)'
    case 'possible':
      return 'var(--border-possible)'
    case 'contradicted':
      return 'var(--border-contradicted)'
    // stale = HISTORY (solid grey — we know this was overtaken)
    case 'stale':
      return 'var(--border-stale)'
    // insufficient = an EVIDENCE GAP (dashed grey — we do NOT know). It shares the
    // Known-Gap border deliberately, and must never fall through to the probable border,
    // which would draw an absence of evidence as a live teal assertion.
    case 'insufficient':
      return 'var(--gap-border-probable-max)'
    case 'known-gap':
      return 'var(--gap-border-probable-max)'
    default:
      return 'var(--border-probable)'
  }
}

export function fillVar(freshness: Freshness): string {
  return `var(--fill-${freshness})`
}

export function opacityFor(freshness: Freshness): number {
  return freshness === 'fresh' ? 1 : freshness === 'aging' ? 0.72 : 0.55
}
