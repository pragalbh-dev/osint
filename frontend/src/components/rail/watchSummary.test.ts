import { describe, expect, it } from 'vitest'
import { watchSummary, type WatchTripwire } from './watchSummary'

const OBS = [{ observable_id: 'a' }, { observable_id: 'b' }, { observable_id: 'c' }]
const fired = (state: string): WatchTripwire => ({ state })

describe('watchSummary — the rail Watching row', () => {
  it('demo mode (no live feed) is unchanged: the frozen count, captioned "armed"', () => {
    expect(watchSummary(null, null, 3)).toEqual({ count: '3', note: 'armed' })
    // the armed catalogue is irrelevant in demo mode — the frozen scenario wins
    expect(watchSummary(OBS, null, 3)).toEqual({ count: '3', note: 'armed' })
  })

  it('cold boot: armed catalogue read, nothing fired → the armed count, NOT 0', () => {
    expect(watchSummary(OBS, [], 3)).toEqual({ count: '3', note: '3 armed · none fired' })
  })

  it('never reports the fired count as the watching count', () => {
    // one of three armed tripwires has fired — the badge stays 3, the caption carries the 1
    const s = watchSummary(OBS, [fired('fired')], 3)
    expect(s.count).toBe('3')
    expect(s.note).toBe('3 armed · 1 fired')
  })

  it('keeps fired-and-decided distinguishable from still-open', () => {
    expect(watchSummary(OBS, [fired('real')], 3).note).toBe('3 armed · fired · all decided')
    expect(watchSummary(OBS, [fired('fired'), fired('real')], 3).note).toBe('3 armed · 1 fired')
  })

  it('degrades honestly when the catalogue cannot be read — no confident 0', () => {
    const s = watchSummary(null, [], 3)
    expect(s.count).toBe('—')
    expect(s.note).toBe('none fired · armed count unavailable')
    expect(s.count).not.toBe('0')
  })

  it('unreadable catalogue still reports the firings it CAN see, labelled', () => {
    const s = watchSummary(null, [fired('fired')], 3)
    expect(s.count).toBe('1')
    expect(s.note).toBe('1 fired · armed count unavailable')
  })

  it('an empty armed catalogue is a real 0, not the unknown case', () => {
    expect(watchSummary([], [], 3)).toEqual({ count: '0', note: '0 armed · none fired' })
  })

  // ── AH-1: armed is not the same as watching ─────────────────────────────────────────────
  // A tripwire whose anchors resolve to no node watches an EMPTY SET — it can never fire. Counting
  // it as coverage is the same class of lie the fired-count bug above was: "3 armed · none fired"
  // reads as three quiet sentries when one of them is blind.

  it('omitting the anchor check leaves the caption exactly as it was', () => {
    expect(watchSummary(OBS, [], 3).note).toBe('3 armed · none fired')
    expect(watchSummary(OBS, [], 3, null).note).toBe('3 armed · none fired')
  })

  it('a clean anchor check adds nothing — no cry wolf', () => {
    expect(watchSummary(OBS, [], 3, { checked: true, unresolved: [] }).note).toBe(
      '3 armed · none fired',
    )
  })

  it('names the tripwires that are watching nothing, between the count and the firings', () => {
    const s = watchSummary(OBS, [], 3, {
      checked: true,
      unresolved: [{ watching_nothing: true }],
    })
    expect(s.count).toBe('3')
    expect(s.note).toBe('3 armed · 1 watching nothing · none fired')
  })

  it('separates a blind tripwire from a merely degraded one', () => {
    const s = watchSummary(OBS, [], 3, {
      checked: true,
      unresolved: [{ watching_nothing: true }, { watching_nothing: false }],
    })
    expect(s.note).toBe('3 armed · 1 watching nothing · 1 anchor unresolved · none fired')
  })

  it('an unrunnable anchor check is stated, never rendered as a clean bill of health', () => {
    const s = watchSummary(OBS, [], 3, { checked: false, unresolved: [] })
    expect(s.note).toBe('3 armed · anchor check unavailable · none fired')
  })

  it('a fired-but-now-blind tripwire still reports blind — the past firing is not a warrant', () => {
    const s = watchSummary(OBS, [fired('fired')], 3, {
      checked: true,
      unresolved: [{ watching_nothing: true }],
    })
    expect(s.note).toBe('3 armed · 1 watching nothing · 1 fired')
  })
})

// ── AH-2: the rail is an ALARM surface, so only faults belong on it ──────────────────────────
// The shipped app withholds two documents from the seed on purpose, so one declared lens anchor is
// legitimately uncovered at first paint. Counting that as "anchor unresolved" made the rail shout on
// a healthy system and fall silent once the demo alert fired — precisely backwards.

describe('watchSummary — anchor severity (AH-2)', () => {
  it('an anchor awaiting coverage is NOT counted on the rail', () => {
    const s = watchSummary(OBS, [], 3, {
      checked: true,
      unresolved: [{ watching_nothing: false, watched_node_count: 2, severity: 'pending_coverage' }],
    })
    expect(s.note).toBe('3 armed · none fired')
  })

  it('the shipped boot shape — two pending, nothing broken — leaves the caption untouched', () => {
    const s = watchSummary(OBS, [], 3, {
      checked: true,
      unresolved: [
        { watching_nothing: false, watched_node_count: 2, severity: 'pending_coverage' },
        { watching_nothing: false, watched_node_count: 32, severity: 'pending_coverage' },
      ],
    })
    expect(s.note).toBe('3 armed · none fired')
  })

  it('a genuinely broken anchor is still counted beside a pending one', () => {
    const s = watchSummary(OBS, [], 3, {
      checked: true,
      unresolved: [
        { watching_nothing: false, watched_node_count: 2, severity: 'pending_coverage' },
        { watching_nothing: false, watched_node_count: 5, severity: 'dangling' },
      ],
    })
    expect(s.note).toBe('3 armed · 1 anchor unresolved · none fired')
  })

  it('scope lost is not collapsed into the milder partial case — it watches the WHOLE graph', () => {
    const s = watchSummary(OBS, [], 3, {
      checked: true,
      unresolved: [{ watching_nothing: false, watched_node_count: null, severity: 'unscoped' }],
    })
    expect(s.note).toBe('3 armed · 1 scope lost · none fired')
  })

  it('a problem with no stated severity is treated as a fault, never quietly downgraded', () => {
    const s = watchSummary(OBS, [], 3, {
      checked: true,
      unresolved: [{ watching_nothing: false }],
    })
    expect(s.note).toBe('3 armed · 1 anchor unresolved · none fired')
  })
})
