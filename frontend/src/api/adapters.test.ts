import { describe, expect, it } from 'vitest'
import type { AskAnswer, GraphView, ProvenanceDrawer } from './types'
import {
  askToAnswerModel,
  credibilityToDots,
  dateValueToString,
  docRefsOf,
  edgeToKind,
  evidenceToDrawerModel,
  formatCoord,
  hopLine,
  humanizeEdge,
  statusToGraphKind,
  viewToGraph,
  viewToGraphEdges,
  viewToGraphNodes,
  viewToPins,
  viewToReviewQueue,
} from './adapters'

// Synthetic /view fixture covering: a located confirmed node (→ pin), an unlocated
// node (graph-only), a chokepoint candidate (kind precedence over status), a stale
// node and an insufficient node (status→kind mapping), plus one edge of each kind.
const VIEW: GraphView = {
  nodes: [
    {
      id: 'karachi',
      type: 'basing_site',
      name: 'Karachi',
      status: 'confirmed',
      location: { wgs84_lat: 24.86, wgs84_lon: 67.01 },
      freshness: { last_support_time: '2022-06-01' },
    },
    {
      id: 'paad',
      type: 'unit',
      name: 'PA Air Defence',
      status: 'probable',
      // no location — exists only in the graph, not on the map
    },
    {
      id: 'ht233',
      type: 'component',
      name: 'HT-233 radar',
      status: 'probable', // status alone would map to 'probable' — chokepoint must win
      materiality: { chokepoint_status: 'candidate' },
    },
    {
      id: 'rahwali_stale',
      type: 'basing_site',
      name: 'Rahwali (old)',
      status: 'stale',
    },
    {
      id: 'gap_node',
      type: 'unit',
      name: 'Unknown reserve unit',
      status: 'insufficient',
    },
  ],
  edges: [
    { id: 'e1', type: 'based-at', source: 'karachi', target: 'paad', status: 'confirmed' },
    {
      id: 'e2',
      type: 'supplies-component',
      source: 'paad',
      target: 'ht233',
      status: 'confirmed', // superseded_by must win over an otherwise-confirmed status
      superseded_by: 'e2b',
    },
    { id: 'e3', type: 'based-at', source: 'ht233', target: 'gap_node', status: 'possible' },
    { id: 'e4', type: 'based-at', source: 'rahwali_stale', target: 'gap_node', status: 'stale' },
  ],
  events: [],
  known_gaps: [],
  alerts: [],
}

describe('formatCoord', () => {
  it('formats a northern/eastern coordinate', () => {
    expect(formatCoord(24.86, 67.01)).toBe('24.86°N  67.01°E')
  })

  it('formats a southern/western coordinate with S/W hemispheres', () => {
    expect(formatCoord(-33.6, -70.5)).toBe('33.60°S  70.50°W')
  })
})

describe('statusToGraphKind', () => {
  it('maps confirmed → confirmed', () => {
    expect(statusToGraphKind(VIEW.nodes[0])).toBe('confirmed')
  })

  it('maps probable → probable', () => {
    expect(statusToGraphKind(VIEW.nodes[1])).toBe('probable')
  })

  it('chokepoint candidate wins regardless of status', () => {
    expect(statusToGraphKind(VIEW.nodes[2])).toBe('chokepoint')
  })

  it('maps stale → stale', () => {
    expect(statusToGraphKind(VIEW.nodes[3])).toBe('stale')
  })

  it('maps insufficient → gap', () => {
    expect(statusToGraphKind(VIEW.nodes[4])).toBe('gap')
  })

  it('falls back to probable when status is missing', () => {
    expect(statusToGraphKind({ id: 'x', type: 'unit' })).toBe('probable')
  })
})

describe('edgeToKind', () => {
  it('maps a plain confirmed edge → e-confirmed', () => {
    expect(edgeToKind(VIEW.edges[0])).toBe('e-confirmed')
  })

  it('superseded_by wins over an otherwise-confirmed status → e-history', () => {
    expect(edgeToKind(VIEW.edges[1])).toBe('e-history')
  })

  it('maps a non-confirmed, non-stale status → e-probable', () => {
    expect(edgeToKind(VIEW.edges[2])).toBe('e-probable')
  })

  it('maps a stale status with no superseded_by → e-history', () => {
    expect(edgeToKind(VIEW.edges[3])).toBe('e-history')
  })
})

describe('viewToPins', () => {
  const pins = viewToPins(VIEW)

  it('emits exactly one pin — only nodes with a full lat/lon location', () => {
    expect(pins).toHaveLength(1)
  })

  it('carries id, label, lat/lon, coord and status through', () => {
    expect(pins[0]).toMatchObject({
      id: 'karachi',
      label: 'Karachi',
      lat: 24.86,
      lon: 67.01,
      coord: '24.86°N  67.01°E',
      status: 'confirmed',
    })
  })

  it('derives the caption year from freshness.last_support_time', () => {
    expect(pins[0].caption).toBe('as of 2022')
  })
})

describe('viewToGraphNodes', () => {
  const nodes = viewToGraphNodes(VIEW)

  it('includes every node, located or not', () => {
    expect(nodes).toHaveLength(5)
    expect(nodes.map((n) => n.id)).toEqual(['karachi', 'paad', 'ht233', 'rahwali_stale', 'gap_node'])
  })

  it('builds a two-line "name\\ntype" label', () => {
    expect(nodes[0].label).toBe('Karachi\nbasing_site')
    expect(nodes[1].label).toBe('PA Air Defence\nunit')
  })

  it('leaves layout position at 0/0 for the component to place', () => {
    expect(nodes[0]).toMatchObject({ x: 0, y: 0 })
  })

  it('resolves kind the same way statusToGraphKind does', () => {
    expect(nodes.map((n) => n.kind)).toEqual(['confirmed', 'probable', 'chokepoint', 'stale', 'gap'])
  })
})

describe('viewToGraphEdges', () => {
  it('maps id/source/target/kind for every edge', () => {
    expect(viewToGraphEdges(VIEW)).toEqual([
      { id: 'e1', source: 'karachi', target: 'paad', kind: 'e-confirmed' },
      { id: 'e2', source: 'paad', target: 'ht233', kind: 'e-history' },
      { id: 'e3', source: 'ht233', target: 'gap_node', kind: 'e-probable' },
      { id: 'e4', source: 'rahwali_stale', target: 'gap_node', kind: 'e-history' },
    ])
  })
})

describe('viewToGraph', () => {
  it('wraps viewToGraphNodes + viewToGraphEdges', () => {
    const graph = viewToGraph(VIEW)
    expect(graph.nodes).toEqual(viewToGraphNodes(VIEW))
    expect(graph.edges).toEqual(viewToGraphEdges(VIEW))
  })
})

// ─────────────────────── live provenance drawer ───────────────────────

describe('dateValueToString', () => {
  it('undefined/null → undefined', () => {
    expect(dateValueToString(undefined)).toBeUndefined()
    expect(dateValueToString(null)).toBeUndefined()
  })

  it('a plain string passes through', () => {
    expect(dateValueToString('2020-01-01')).toBe('2020-01-01')
  })

  it('prefers .date when present', () => {
    expect(dateValueToString({ date: '2020-01-01', label: 'ignored' })).toBe('2020-01-01')
  })

  it('falls back to .label', () => {
    expect(dateValueToString({ label: 'Q1 2020' })).toBe('Q1 2020')
  })

  it('falls back to a start – end range', () => {
    expect(dateValueToString({ start: '2020-01-01', end: '2020-06-01' })).toBe('2020-01-01 – 2020-06-01')
  })

  it('falls back to whichever of start/end is present alone', () => {
    expect(dateValueToString({ start: '2020-01-01' })).toBe('2020-01-01')
    expect(dateValueToString({ end: '2020-06-01' })).toBe('2020-06-01')
  })

  it('an empty object → undefined', () => {
    expect(dateValueToString({})).toBeUndefined()
  })
})

describe('credibilityToDots', () => {
  it('undefined/null → 2 (unknown-mid)', () => {
    expect(credibilityToDots(undefined)).toBe(2)
    expect(credibilityToDots(null)).toBe(2)
  })

  it('buckets a 0..1 score into 1..4 dots', () => {
    expect(credibilityToDots(0)).toBe(1)
    expect(credibilityToDots(0.1)).toBe(1)
    expect(credibilityToDots(0.25)).toBe(2)
    expect(credibilityToDots(0.4)).toBe(2)
    expect(credibilityToDots(0.5)).toBe(3)
    expect(credibilityToDots(0.6)).toBe(3)
    expect(credibilityToDots(0.75)).toBe(4)
    expect(credibilityToDots(1)).toBe(4)
  })
})

describe('docRefsOf', () => {
  it('null/undefined → []', () => {
    expect(docRefsOf(undefined)).toEqual([])
    expect(docRefsOf(null)).toEqual([])
  })

  it('a single DocRef normalizes to a one-element array', () => {
    expect(docRefsOf({ file: 'a.pdf' })).toEqual([{ file: 'a.pdf' }])
  })

  it('an array passes through', () => {
    const refs = [{ file: 'a.pdf' }, { file: 'b.pdf' }]
    expect(docRefsOf(refs)).toEqual(refs)
  })
})

describe('evidenceToDrawerModel', () => {
  // c1/c2 sit in cluster g1; c3 + a missing claim id sit in g2 — the missing one
  // must be skipped rather than emitted as a row with no backing record.
  const DRAWER: ProvenanceDrawer = {
    subject_ref: 'unit:paad',
    status: 'probable',
    claims: [
      {
        claim_id: 'c1',
        source_id: 's1',
        doc_ref: { file: 'a.pdf', page: 2 },
        kind: 'observation',
        asserts: 'relationship',
        event_time: '2022-01-01',
        report_time: { date: '2022-01-02' },
        ingest_time: { label: 'Q1 2022' },
      },
      {
        claim_id: 'c2',
        source_id: 's2',
        doc_ref: [{ file: 'b.pdf' }, { file: 'c.pdf' }],
        kind: 'inference',
        asserts: 'entity',
        event_time: { start: '2021-01-01', end: '2021-06-01' },
        ingest_time: '2021-07-01',
      },
      {
        claim_id: 'c3',
        source_id: 's1',
        doc_ref: { file: 'd.pdf' },
        kind: 'observation',
        asserts: 'event',
      },
    ],
    clusters: [
      { group_id: 'g1', claim_ids: ['c1', 'c2'], axis_key: { origin: 'HUMINT', discipline: 'signals' } },
      { group_id: 'g2', claim_ids: ['c3', 'c_missing'] },
    ],
    confidence: {
      per_claim_credibility: { c1: 0.1, c2: 0.4, c3: 0.9 },
      integrity_flags: ['too-clean'],
    },
    opposing_claims: ['c_opp1'],
    sufficiency: {
      satisfied: false,
      missing_slots: ['corroboration'],
      next_coverage_due: '2026-08-01',
      ceiling: 'probable-max',
    },
  }

  const model = evidenceToDrawerModel(DRAWER)

  it('carries subjectRef and status through', () => {
    expect(model.subjectRef).toBe('unit:paad')
    expect(model.status).toBe('probable')
  })

  it('defaults status to insufficient when absent', () => {
    expect(evidenceToDrawerModel({ subject_ref: 'x' }).status).toBe('insufficient')
  })

  it('counts looks as the number of clusters', () => {
    expect(model.looks).toBe(2)
  })

  it('counts sources as distinct source_id across claims', () => {
    expect(model.sources).toBe(2) // s1, s2
  })

  it('builds one cluster per IndependenceGroup, carrying groupId and axis', () => {
    expect(model.clusters).toHaveLength(2)
    expect(model.clusters[0].groupId).toBe('g1')
    expect(model.clusters[0].axis).toEqual({ origin: 'HUMINT', discipline: 'signals' })
    expect(model.clusters[1].groupId).toBe('g2')
    expect(model.clusters[1].axis).toBeUndefined()
  })

  it('skips a claim_id referenced by a cluster but missing from claims[]', () => {
    expect(model.clusters[1].rows).toHaveLength(1)
    expect(model.clusters[1].rows[0].claimId).toBe('c3')
  })

  it('normalizes doc_ref to an array whether given as one object or a list', () => {
    expect(model.clusters[0].rows[0].docRefs).toEqual([{ file: 'a.pdf', page: 2 }])
    expect(model.clusters[0].rows[1].docRefs).toEqual([{ file: 'b.pdf' }, { file: 'c.pdf' }])
  })

  it('builds row detail from kind + asserts', () => {
    expect(model.clusters[0].rows[0].detail).toBe('observation · relationship')
    expect(model.clusters[0].rows[1].detail).toBe('inference · entity')
  })

  it('formats each date form through dateValueToString', () => {
    const [c1, c2] = model.clusters[0].rows
    expect(c1.dates).toEqual({ event: '2022-01-01', reported: '2022-01-02', ingested: 'Q1 2022' })
    expect(c2.dates.event).toBe('2021-01-01 – 2021-06-01')
    expect(c2.dates.reported).toBeUndefined()
    expect(c2.dates.ingested).toBe('2021-07-01')
  })

  it('buckets dots via credibilityToDots from per_claim_credibility', () => {
    expect(model.clusters[0].rows[0].dots).toBe(1) // 0.1
    expect(model.clusters[0].rows[1].dots).toBe(2) // 0.4
    expect(model.clusters[1].rows[0].dots).toBe(4) // 0.9
  })

  it('counts opposingCount from opposing_claims', () => {
    expect(model.opposingCount).toBe(1)
  })

  it('carries integrityFlags from confidence.integrity_flags', () => {
    expect(model.integrityFlags).toEqual(['too-clean'])
  })

  it('maps sufficiency, defaulting nextCoverageDue/missingSlots', () => {
    expect(model.sufficiency).toEqual({
      satisfied: false,
      missingSlots: ['corroboration'],
      nextCoverageDue: '2026-08-01',
      ceiling: 'probable-max',
    })
  })

  it('leaves sufficiency undefined when absent from the response', () => {
    expect(evidenceToDrawerModel({ subject_ref: 'x' }).sufficiency).toBeUndefined()
  })

  it('defaults sources/looks/opposingCount/integrityFlags to 0/[] on a bare response', () => {
    const bare = evidenceToDrawerModel({ subject_ref: 'x' })
    expect(bare.sources).toBe(0)
    expect(bare.looks).toBe(0)
    expect(bare.opposingCount).toBe(0)
    expect(bare.integrityFlags).toEqual([])
    expect(bare.clusters).toEqual([])
  })
})

// ─────────────────────────── live ask / answer ───────────────────────────

describe('humanizeEdge', () => {
  it('replaces hyphens and underscores with spaces', () => {
    expect(humanizeEdge('supplies-component')).toBe('supplies component')
    expect(humanizeEdge('based_at')).toBe('based at')
  })
})

describe('hopLine', () => {
  it('builds "src — edge → dst"', () => {
    expect(hopLine({ step: 1, edge: 'supplies-component', src: 'CASIC', dst: 'HT-233' })).toBe(
      'CASIC — supplies component → HT-233',
    )
  })
})

describe('askToAnswerModel', () => {
  const ANSWER: AskAnswer = {
    question: 'Trace this battery back to its component supplier',
    sub_questions: ['Where is it based?', 'Who supplied it?'],
    answer: 'The HT-233 radar is the candidate chokepoint.',
    citations: ['d05', 'd07'],
    hops: [
      { step: 1, edge: 'based-at', src: 'battery', dst: 'Karachi', observed_or_inferred: 'observed', claim_ids: ['c1'] },
      { step: 2, edge: 'supplies-component', src: 'CASIC', dst: 'HT-233', observed_or_inferred: 'inferred' },
    ],
  }

  it('classifies a populated answer as kind "answer"', () => {
    const m = askToAnswerModel(ANSWER)
    expect(m.kind).toBe('answer')
    expect(m.answer).toBe('The HT-233 radar is the candidate chokepoint.')
    expect(m.subQuestions).toEqual(['Where is it based?', 'Who supplied it?'])
    expect(m.citations).toEqual(['d05', 'd07'])
  })

  it('formats each hop into a readable line + observed/inferred flag + citations', () => {
    const m = askToAnswerModel(ANSWER)
    expect(m.hops).toHaveLength(2)
    expect(m.hops[0]).toMatchObject({ step: 1, line: 'battery — based at → Karachi', observed: true, citations: ['c1'] })
    expect(m.hops[1]).toMatchObject({ step: 2, line: 'CASIC — supplies component → HT-233', observed: false, citations: [] })
  })

  it('treats an explicit refusal payload as kind "refusal"', () => {
    const refusal: AskAnswer = {
      question: 'How many launchers?',
      answer: null,
      refusal: {
        reason: 'Needs an unobscured overhead pass.',
        missing: ['unobscured pass', 'SAR correlation'],
        next_coverage_due: '2026-05-14',
      },
    }
    const m = askToAnswerModel(refusal)
    expect(m.kind).toBe('refusal')
    expect(m.answer).toBe('')
    expect(m.refusal).toEqual({
      reason: 'Needs an unobscured overhead pass.',
      missing: ['unobscured pass', 'SAR correlation'],
      nextCoverageDue: '2026-05-14',
      knownGap: null,
    })
  })

  it('treats a null answer with no refusal payload as a refusal too', () => {
    const m = askToAnswerModel({ question: 'q', answer: null })
    expect(m.kind).toBe('refusal')
    expect(m.refusal).toEqual({ reason: undefined, missing: [], nextCoverageDue: null, knownGap: null })
  })

  it('defaults hops/citations/subQuestions to empty on a bare answer', () => {
    const m = askToAnswerModel({ question: 'q', answer: 'a' })
    expect(m.hops).toEqual([])
    expect(m.citations).toEqual([])
    expect(m.subQuestions).toEqual([])
    expect(m.refusal).toBeUndefined()
  })
})

// ─────────────────────── live review queue (derived) ───────────────────────

describe('viewToReviewQueue', () => {
  const QVIEW: GraphView = {
    nodes: [
      { id: 'hq9p', type: 'variant', name: 'HQ-9/P', status: 'probable' },
      { id: 'hq9be', type: 'variant', name: 'HQ-9BE', status: 'probable' },
      // a node with opposing evidence → status-override
      { id: 'karachi_east', type: 'basing_site', name: 'Karachi-East', status: 'probable', opposing_claims: ['c_d08', 'c_d09'] },
      // a contradicted node → status-override (contradiction badge)
      { id: 'sargodha', type: 'basing_site', name: 'Sargodha', status: 'contradicted' },
      // clean node → NOT in the queue
      { id: 'casic', type: 'manufacturer', name: 'CASIC', status: 'confirmed' },
    ],
    edges: [
      // a same-as edge → merge item
      { id: 'sa1', type: 'same-as', source: 'hq9p', target: 'hq9be', merge_confidence: 0.7 },
      // a normal edge → nothing
      { id: 'e1', type: 'based-at', source: 'karachi_east', target: 'hq9p', status: 'confirmed' },
    ],
    events: [],
    known_gaps: [],
    alerts: [
      // un-dispositioned → alert item
      {
        observable_id: 'relocation',
        subject: 'fire_unit_1',
        before: { site: 'Rawalpindi' },
        after: { site: 'Rahwali' },
        severity: 'watch',
        fired_ts: '2025-05-14',
        disposition: null,
      },
      // already dispositioned → NOT in the queue
      { observable_id: 'contradiction', subject: 'x', disposition: 'real', fired_ts: '2025-05-01' },
    ],
  }

  const queue = viewToReviewQueue(QVIEW)

  it('derives merge / status-override / alert items and skips clean + dispositioned ones', () => {
    const byType = queue.reduce<Record<string, number>>((acc, i) => {
      acc[i.reviewType] = (acc[i.reviewType] ?? 0) + 1
      return acc
    }, {})
    // 1 merge, 2 status-overrides (opposing + contradicted), 1 alert
    expect(byType).toEqual({ merge: 1, 'status-override': 2, 'alert-disposition': 1 })
  })

  it('builds a merge item from a same-as edge with the edge id as subject + endpoint labels', () => {
    const merge = queue.find((i) => i.reviewType === 'merge')!
    expect(merge.hitlVerb).toBe('merge')
    expect(merge.subject).toBe('sa1')
    expect(merge.context.left).toEqual({ id: 'hq9p', label: 'HQ-9/P' })
    expect(merge.context.right).toEqual({ id: 'hq9be', label: 'HQ-9BE' })
    expect(merge.context.dots).toBe(3) // credibilityToDots(0.7)
  })

  it('builds a status-override from opposing claims, keyed by the element id', () => {
    const ovr = queue.find((i) => i.subject === 'karachi_east')!
    expect(ovr.reviewType).toBe('status-override')
    expect(ovr.hitlVerb).toBe('status')
    expect(ovr.context.detail).toEqual(['c_d08', 'c_d09'])
    expect(ovr.badge).toBe('Close call')
  })

  it('flags a contradicted status with the Contradiction badge', () => {
    const contra = queue.find((i) => i.subject === 'sargodha')!
    expect(contra.reviewType).toBe('status-override')
    expect(contra.badge).toBe('Contradiction')
  })

  it('builds an alert-disposition from an un-dispositioned firing, with before→after', () => {
    const alert = queue.find((i) => i.reviewType === 'alert-disposition')!
    expect(alert.hitlVerb).toBe('alert')
    expect(alert.subject).toBe('fire_unit_1')
    expect(alert.context.changed).toEqual({ from: 'site: Rawalpindi', to: 'site: Rahwali' })
    expect(alert.context.severity).toBe('watch')
  })

  it('produces stable, unique itemIds', () => {
    const ids = queue.map((i) => i.itemId)
    expect(new Set(ids).size).toBe(ids.length)
  })

  it('returns an empty queue for a clean graph', () => {
    expect(viewToReviewQueue({ nodes: [], edges: [], events: [], known_gaps: [], alerts: [] })).toEqual([])
  })
})
