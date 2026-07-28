import { describe, expect, it } from 'vitest'
import {
  cannotFireCount,
  reachabilityBadge,
  reachabilityIndex,
  reachabilityMeta,
  reachabilityNotice,
} from './reachability'
import { isReachabilityFault, type TriggerReachability } from '@/api/types'

const base: TriggerReachability = {
  observable_id: 'obs-x',
  status: 'reachable',
  can_fire: true,
  gap_kind: null,
  missing: [],
  candidate_count: 0,
  checked: true,
  warning: null,
}
const r = (o: Partial<TriggerReachability>): TriggerReachability => ({ ...base, ...o })

// ── The three verdicts the SHIPPED config actually produces ──────────────────────────────────────
// Captured verbatim from GET /config/observables on a keyless boot. Pinning the real payload (not a
// hand-written approximation of it) is what makes this file a regression test rather than a test of
// my own assumptions about the backend.
const LIVE_REACHABLE = r({
  observable_id: 'obs-basing-relocation',
  status: 'reachable',
  can_fire: true,
  gap_kind: null,
  missing: [],
  candidate_count: 10,
  warning: null,
})
const LIVE_DATA_GAP = r({
  observable_id: 'obs-followon-interceptor-order',
  status: 'no_coverage',
  can_fire: false,
  gap_kind: 'data',
  missing: [
    { kind: 'edge_type', name: 'replenishes' },
    { kind: 'node_type', name: 'interceptor_stockpile' },
  ],
  candidate_count: 0,
  warning:
    "this tripwire filters on the edge type 'replenishes', and the current view contains no edge of that type at all — so it has nothing to watch and cannot fire on this graph.",
})
const LIVE_ENGINE_FAULT = r({
  observable_id: 'obs-spares-tender-probable-induction',
  status: 'never_fires',
  can_fire: false,
  gap_kind: 'engine',
  missing: [{ kind: 'trigger_form', name: 'new_claim' }],
  candidate_count: null,
  warning:
    "this tripwire cannot fire from any change to the graph: trigger.on='new_claim' is not a view-delta condition",
})
const LIVE = [LIVE_REACHABLE, LIVE_DATA_GAP, LIVE_ENGINE_FAULT]

describe('reachabilityNotice — the two registers', () => {
  it('a wire that CAN fire gets no block — the positive verdict rides on the meta line', () => {
    expect(reachabilityNotice(LIVE_REACHABLE)).toBeNull()
    expect(reachabilityBadge(LIVE_REACHABLE)).toBeNull() // caller keeps its own "armed"
    expect(reachabilityMeta(LIVE_REACHABLE)).toBe('can fire · 10 candidates')
  })

  it('a DATA gap is neutral — it self-heals on the next document, nobody edits anything', () => {
    const n = reachabilityNotice(LIVE_DATA_GAP)!
    expect(n.register).toBe('gap')
    expect(n.label).toBe('UNCOVERED')
    expect(reachabilityBadge(LIVE_DATA_GAP)).toBe('uncovered')
    // never the loud register, and never the word reserved for a real fault
    expect(n.label).not.toBe('CANNOT FIRE')
  })

  it('an ENGINE/MODELLING gap is a fault — no volume of documents fixes it', () => {
    for (const kind of ['engine', 'modelling'] as const) {
      const n = reachabilityNotice(r({ can_fire: false, gap_kind: kind, status: 'never_fires' }))!
      expect(n.register).toBe('fault')
      expect(n.label).toBe('CANNOT FIRE')
    }
    expect(reachabilityBadge(LIVE_ENGINE_FAULT)).toBe('cannot fire')
  })

  it('a SCOPE gap renders nothing — the anchor block on the same card already owns that remedy', () => {
    const scoped = r({ can_fire: false, gap_kind: 'scope', status: 'out_of_watch_scope' })
    expect(reachabilityNotice(scoped)).toBeNull()
    expect(reachabilityBadge(scoped)).toBeNull()
    expect(isReachabilityFault(scoped)).toBe(false)
  })

  it('no verdict for an observable asserts nothing either way', () => {
    expect(reachabilityNotice(undefined)).toBeNull()
    expect(reachabilityBadge(undefined)).toBeNull()
    expect(reachabilityMeta(undefined)).toBeNull()
  })
})

describe('reachabilityNotice — the unknown state is never a pass', () => {
  // The whole defect class: an unrun check reading as a passed one.
  it('checked:false renders as UNVERIFIED, never as silence and never as reachable', () => {
    const unchecked = r({ checked: false, can_fire: false, warning: 'no view supplied' })
    const n = reachabilityNotice(unchecked)!
    expect(n).not.toBeNull()
    expect(n.register).toBe('unknown')
    expect(n.label).toBe('REACHABILITY UNVERIFIED')
    expect(reachabilityBadge(unchecked)).toBe('unverified')
    // not downgraded to a fault either — unknown is its own thing
    expect(isReachabilityFault(unchecked)).toBe(false)
  })

  it('checked:false never claims the positive verdict, even if can_fire says true', () => {
    // A payload that did not run the check cannot be reporting a real can_fire, so the UI must not
    // launder it into "can fire" on the meta line.
    expect(reachabilityMeta(r({ checked: false, can_fire: true }))).toBeNull()
  })

  it('an unexplained failure defaults to FAULT, never quietly to fine', () => {
    const mystery = r({ can_fire: false, gap_kind: null, status: 'never_fires' })
    expect(reachabilityNotice(mystery)!.register).toBe('fault')
    expect(isReachabilityFault(mystery)).toBe(true)
  })
})

describe("reachability — the backend's words, verbatim", () => {
  // The rule that keeps the surface and the engine from drifting: the sentence naming the missing
  // thing and the remedy is computed once, by the side that actually knows, and passed through.
  it('passes the warning through untouched — no paraphrase, no truncation', () => {
    expect(reachabilityNotice(LIVE_DATA_GAP)!.warning).toBe(LIVE_DATA_GAP.warning)
    expect(reachabilityNotice(LIVE_ENGINE_FAULT)!.warning).toBe(LIVE_ENGINE_FAULT.warning)
  })

  it('a missing warning yields an empty string, not an invented sentence', () => {
    const n = reachabilityNotice(
      r({ can_fire: false, gap_kind: 'engine', status: 'never_fires', warning: null }),
    )!
    expect(n.warning).toBe('')
    expect(n.detail).toContain('never_fires') // the machine detail still identifies it
  })

  it('the detail line names the specific missing types', () => {
    expect(reachabilityNotice(LIVE_DATA_GAP)!.detail).toBe(
      "no_coverage  ·  edge type 'replenishes'  ·  node type 'interceptor_stockpile'",
    )
    expect(reachabilityNotice(LIVE_ENGINE_FAULT)!.detail).toBe(
      "never_fires  ·  trigger form 'new_claim'",
    )
  })
})

describe('cannotFireCount — what the rail counts', () => {
  it('counts BOTH gap kinds: dead is dead, whatever revives it later', () => {
    expect(cannotFireCount({ observables: LIVE })).toBe(2)
  })

  it('excludes scope gaps (the anchor half of the caption already counts those)', () => {
    expect(cannotFireCount({ observables: [r({ can_fire: false, gap_kind: 'scope' })] })).toBe(0)
  })

  it('excludes unchecked entries — unknown is not a count of dead wires', () => {
    expect(cannotFireCount({ observables: [r({ checked: false, can_fire: false })] })).toBe(0)
  })

  it('is 0 on a clean catalogue and on an unknown one', () => {
    expect(cannotFireCount({ observables: [LIVE_REACHABLE] })).toBe(0)
    expect(cannotFireCount(null)).toBe(0)
    expect(cannotFireCount({})).toBe(0)
  })
})

describe('reachabilityIndex', () => {
  it('keys verdicts by observable id so a card can find its own', () => {
    const ix = reachabilityIndex({ observables: LIVE })
    expect(ix.get('obs-spares-tender-probable-induction')?.status).toBe('never_fires')
    expect(ix.get('nope')).toBeUndefined()
    expect(reachabilityIndex(null).size).toBe(0)
  })
})

// ── NON-VACUITY CONTROL ──────────────────────────────────────────────────────────────────────────
// How this check would silently die: someone stubs the surface to always report healthy (return null
// / "armed" / 0), or to always report broken, and every "does it show the warning" test above still
// passes for the wrong reason. These pair a healthy payload against a broken one through the SAME
// call, so neither constant answer can satisfy both halves.
describe('NON-VACUITY: the surface must discriminate on the payload', () => {
  it('fails if every tripwire is reported healthy regardless of payload', () => {
    const allHealthy = [r({ observable_id: 'a' }), r({ observable_id: 'b' }), r({ observable_id: 'c' })]

    // Healthy payload → nothing raised.
    expect(allHealthy.map(reachabilityNotice)).toEqual([null, null, null])
    expect(cannotFireCount({ observables: allHealthy })).toBe(0)

    // Same calls, broken payload → something raised. A hardcoded "healthy" breaks here.
    expect(LIVE.map((x) => reachabilityNotice(x)?.register ?? null)).toEqual([null, 'gap', 'fault'])
    expect(cannotFireCount({ observables: LIVE })).toBe(2)
  })

  it('fails if every tripwire is reported broken regardless of payload', () => {
    // The opposite failure — crying wolf on everything — is just as useless, and would train an
    // analyst to ignore the one card that matters.
    expect(reachabilityNotice(LIVE_REACHABLE)).toBeNull()
    expect(reachabilityBadge(LIVE_REACHABLE)).toBeNull()
    expect(reachabilityNotice(LIVE_ENGINE_FAULT)).not.toBeNull()
  })

  it('fails if the two registers are collapsed into one', () => {
    // The data/fault split is the whole analyst-facing point: one waits, the other edits config.
    const registers = LIVE.map((x) => reachabilityNotice(x)?.register ?? 'none')
    expect(new Set(registers).size).toBe(3) // none, gap, fault — all distinct
  })
})
