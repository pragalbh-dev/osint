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
})
