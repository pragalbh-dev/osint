import { describe, expect, it } from 'vitest'
import type { AskAnswer, GraphView, ProvenanceDrawer } from './types'
import {
  alertToFiring,
  askToAnswerModel,
  claimElementIndex,
  clusterAreaPins,
  credibilityToDots,
  dateValueToString,
  displayNameOf,
  docRefsOf,
  edgeToKind,
  evidenceToDrawerModel,
  formatCoord,
  formatRadius,
  groupReviewQueue,
  hopLine,
  isAreaPin,
  mergeDiffersOn,
  mergeDifferences,
  orderReviewQueue,
  resolveHopElement,
  humanizeEdge,
  humanizeObservableId,
  isKnownElementId,
  nameResolver,
  statusToGraphKind,
  supersededSites,
  supersedeHoldReasons,
  viewToGraph,
  viewToGraphEdges,
  viewToGraphNodes,
  viewToPins,
  unplacedLocations,
  viewToReviewQueue,
  viewToTripwires,
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
    // an evidence GAP — must not render like the stale edge above, and must not fall
    // through to the probable (live teal) default
    { id: 'e5', type: 'based-at', source: 'gap_node', target: 'paad', status: 'insufficient' },
    { id: 'e6', type: 'based-at', source: 'gap_node', target: 'ht233', status: 'contradicted' },
    // status-LESS by design — nothing may assume every edge carries a status
    { id: 'sa1', type: 'same-as', source: 'karachi', target: 'paad', status: null },
    // The backend draws supersession site→site but the fact lives on the `based-at` edge, so the
    // drawn edge carries `attrs.subject` — WHO moved. Consumers must use it or they assert that
    // one site replaced another.
    {
      id: 'sup1',
      type: 'supersedes',
      source: 'rahwali_stale',
      target: 'karachi',
      status: null,
      confidence: null,
      attrs: {
        subject: 'paad',
        older_edge: 'e:paad:based-at:karachi',
        newer_edge: 'e:paad:based-at:rahwali_stale',
      },
    },
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

  it('maps contradicted → contradicted, NOT gap — disagreement is not absence', () => {
    const kind = statusToGraphKind({ id: 'x', type: 'unit', status: 'contradicted' })
    expect(kind).toBe('contradicted')
    expect(kind).not.toBe('gap')
  })

  it('falls back to probable when status is missing', () => {
    expect(statusToGraphKind({ id: 'x', type: 'unit' })).toBe('probable')
  })
})

describe('edgeToKind', () => {
  it('maps a plain confirmed edge → e-confirmed', () => {
    expect(edgeToKind(VIEW.edges[0])).toBe('e-confirmed')
  })

  it('superseded_by wins over an otherwise-confirmed status → e-stale', () => {
    expect(edgeToKind(VIEW.edges[1])).toBe('e-stale')
  })

  it('maps a non-confirmed, non-stale status → e-probable', () => {
    expect(edgeToKind(VIEW.edges[2])).toBe('e-probable')
  })

  it('maps a stale status with no superseded_by → e-stale (history)', () => {
    expect(edgeToKind(VIEW.edges[3])).toBe('e-stale')
  })

  it('maps insufficient → e-gap, NOT e-stale — a gap is not history', () => {
    expect(edgeToKind(VIEW.edges[4])).toBe('e-gap')
    expect(edgeToKind(VIEW.edges[4])).not.toBe(edgeToKind(VIEW.edges[3]))
  })

  it('maps contradicted → e-contradicted (sources disagree ≠ evidence missing)', () => {
    expect(edgeToKind(VIEW.edges[5])).toBe('e-contradicted')
  })

  it('gives a status-less same-as the neutral link kind, not a truth kind', () => {
    expect(edgeToKind(VIEW.edges[6])).toBe('e-link')
  })

  it('gives a status-less supersedes the "replaced by" kind, never a contradiction', () => {
    expect(edgeToKind(VIEW.edges[7])).toBe('e-supersede')
    expect(edgeToKind(VIEW.edges[7])).not.toBe('e-contradicted')
  })

  it('draws an UNADJUDICATED supersession dashed — candidate, not settled', () => {
    const candidate = {
      id: 'sup2',
      type: 'supersedes',
      source: 'a',
      target: 'b',
      status: null,
      attrs: { candidate_supersede: true },
    }
    expect(edgeToKind(candidate)).toBe('e-supersede-candidate')
    // a pending/held gate is the same fact by another name
    expect(edgeToKind({ id: 'sup3', type: 'supersedes', source: 'a', target: 'b', attrs: { supersede_gate: 'held' } })).toBe(
      'e-supersede-candidate',
    )
    // …and a promoted one is settled: solid.
    expect(edgeToKind({ id: 'sup4', type: 'supersedes', source: 'a', target: 'b', attrs: { supersede_gate: 'promoted' } })).toBe(
      'e-supersede',
    )
  })

  it('does not throw on an edge with no status at all', () => {
    expect(() => edgeToKind({ id: 'x', type: 'supersedes', source: 'a', target: 'b' })).not.toThrow()
    expect(edgeToKind({ id: 'x', type: 'based-at', source: 'a', target: 'b' })).toBe('e-probable')
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
    // VIEW's `sup1` supersedes this node, so read the plain as-of line off a view without it
    const plain = viewToPins({ ...VIEW, edges: VIEW.edges.filter((e) => e.type !== 'supersedes') })
    expect(plain[0].caption).toBe('as of 2022')
    expect(plain[0].superseded).toBe(false)
    expect(plain[0].supersededBy).toBeNull()
  })

  // Supersession lives on the EDGE — a node's own status never carries it — so the map has to
  // derive "this location is history now" from the graph, or it silently loses the relocation
  // story the Graph stage tells. VIEW's `sup1` is `rahwali_stale supersedes karachi`.
  it('marks the TARGET of a settled supersedes edge as history, naming its successor', () => {
    expect(pins[0]).toMatchObject({ id: 'karachi', superseded: true, supersededBy: 'rahwali_stale' })
  })

  // A bare "superseded" caption on a SITE reads as "this place was replaced", which is false —
  // the place is still there, its occupant left. The caption must be about the occupancy and it
  // must name the occupant, which the drawn edge carries in `attrs.subject`.
  it('captions a left-behind site by its former OCCUPANCY, naming the occupant', () => {
    expect(pins[0].caption).toBe('former PA Air Defence basing · 2022')
    expect(pins[0].supersedeSubject).toBe('PA Air Defence')
    expect(pins[0].supersedeEdgeId).toBe('sup1')
  })

  it('falls back to a subject-free caption rather than naming the site as replaced', () => {
    const anon = viewToPins({
      ...VIEW,
      edges: [{ id: 'sup1', type: 'supersedes', source: 'rahwali_stale', target: 'karachi' }],
    })
    expect(anon[0].caption).toBe('former basing on record · 2022')
    expect(anon[0].supersedeSubject).toBeNull()
  })

  it('does NOT mark a pin superseded on an unadjudicated (candidate/held) supersession', () => {
    const candidate = viewToPins({
      ...VIEW,
      edges: [
        {
          id: 'sup1',
          type: 'supersedes',
          source: 'rahwali_stale',
          target: 'karachi',
          status: null,
          attrs: { candidate_supersede: true },
        },
      ],
    })
    expect(candidate[0].superseded).toBe(false)
    expect(candidate[0].caption).toBe('as of 2022')
  })
})

describe('supersededSites', () => {
  it('maps superseded → successor for settled supersessions only', () => {
    expect([...supersededSites(VIEW).entries()]).toEqual([['karachi', 'rahwali_stale']])
  })

  it('ignores a held/pending/candidate supersession — that adjudication has not been made', () => {
    const held: GraphView = {
      ...VIEW,
      edges: [{ id: 's', type: 'supersedes', source: 'a', target: 'b', attrs: { supersede_gate: 'held' } }],
    }
    expect(supersededSites(held).size).toBe(0)
  })
})

// Raw internal ids are keys, not names. Analyst-facing copy renders the node's OWN name,
// with the id demoted to technical detail — and never invents one.
describe('displayNameOf / nameResolver', () => {
  it('renders a node id as its own name — never a paraphrase', () => {
    expect(displayNameOf(VIEW, 'karachi')).toBe('Karachi')
    expect(nameResolver(VIEW)('gap_node')).toBe('Unknown reserve unit')
  })

  it('falls back to the id when the graph has no name for it — shows the key, never a guess', () => {
    expect(displayNameOf(VIEW, 'site_nowhere')).toBe('site_nowhere')
    expect(nameResolver(null)('site_nowhere')).toBe('site_nowhere')
  })

  it('reads an edge id as its named endpoints', () => {
    expect(displayNameOf(VIEW, 'e1')).toBe('Karachi — based at → PA Air Defence')
  })

  it('knows which strings are element ids, so free-text slots pass through untouched', () => {
    expect(isKnownElementId(VIEW, 'karachi')).toBe(true)
    expect(isKnownElementId(VIEW, 'e1')).toBe(true)
    expect(isKnownElementId(VIEW, 'an unobscured pass')).toBe(false)
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
  it('maps id/source/target/kind/type for every edge', () => {
    expect(viewToGraphEdges(VIEW)).toEqual([
      { id: 'e1', source: 'karachi', target: 'paad', kind: 'e-confirmed', type: 'based-at' },
      { id: 'e2', source: 'paad', target: 'ht233', kind: 'e-stale', type: 'supplies-component' },
      { id: 'e3', source: 'ht233', target: 'gap_node', kind: 'e-probable', type: 'based-at' },
      { id: 'e4', source: 'rahwali_stale', target: 'gap_node', kind: 'e-stale', type: 'based-at' },
      { id: 'e5', source: 'gap_node', target: 'paad', kind: 'e-gap', type: 'based-at' },
      { id: 'e6', source: 'gap_node', target: 'ht233', kind: 'e-contradicted', type: 'based-at' },
      { id: 'sa1', source: 'karachi', target: 'paad', kind: 'e-link', type: 'same-as' },
      { id: 'sup1', source: 'rahwali_stale', target: 'karachi', kind: 'e-supersede', type: 'supersedes' },
    ])
  })

  // The graph stage separates DOMAIN relationships from resolution BOOKKEEPING, which is
  // only possible if the ontology type survives the collapse into a visual `kind`
  // (`e-link` is both `same-as` and `distinct-from`).
  it('keeps the ontology type alongside the collapsed visual kind', () => {
    const sameAs = viewToGraphEdges(VIEW).find((e) => e.id === 'sa1')
    expect(sameAs).toMatchObject({ kind: 'e-link', type: 'same-as' })
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
    // the verbatim text at each doc_ref — c2's SECOND ref is unreadable, c3 has none at all
    quotes: { c1: ['array present at Rahwali'], c2: ['a second look', ''] },
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

  // "observation · entity" names the claim's FILING CATEGORY, not its content — an analyst reads
  // it and still cannot tell what is being asserted. The detail line is the internal enum pair
  // translated; the CONTENT lives in `proposition` (below).
  it('translates kind + asserts into analyst English', () => {
    expect(model.clusters[0].rows[0].detail).toBe('Observed · about a connection')
    expect(model.clusters[0].rows[1].detail).toBe('Inferred · about a thing')
    expect(model.clusters[0].rows[0].kindLabel).toBe('Observed')
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

  // A file path + byte range is a POINTER, not a source — the analyst has to be able to read
  // the words. The quote array is positionally parallel to docRefs so index i always answers
  // "what does ref i say?", and an unreadable span is '' (the row shows the locator alone),
  // never a paraphrase.
  it('carries the verbatim quote per docRef, parallel to docRefs', () => {
    expect(model.clusters[0].rows[0].quotes).toEqual(['array present at Rahwali'])
    expect(model.clusters[0].rows[1].quotes).toEqual(['a second look', ''])
    expect(model.clusters[0].rows[1].quotes).toHaveLength(model.clusters[0].rows[1].docRefs.length)
  })

  it('emits an empty quote (never a paraphrase) when the backend returned none', () => {
    expect(model.clusters[1].rows[0].quotes).toEqual([''])
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

  // ── what the drawer is a verdict ABOUT ───────────────────────────────────────────────────
  // A status hung over a bare node name grades no proposition. The headline states the assertion
  // under assessment, built from the graph's own name + type — never invented.

  it('heads a node with the proposition that node exists, as its own type', () => {
    const m = evidenceToDrawerModel({ subject_ref: 'karachi' }, VIEW)
    expect(m.subject).toMatchObject({ kind: 'node', typeLabel: 'basing site', statusless: false })
    expect(m.subject?.headline).toBe('“Karachi” exists, as a basing site')
  })

  it('heads an edge with the relationship it asserts, both ends named', () => {
    const m = evidenceToDrawerModel({ subject_ref: 'e1' }, VIEW)
    expect(m.subject?.headline).toBe('Karachi — based at → PA Air Defence')
  })

  it('falls back to the bare ref when the view does not know the id — never a description', () => {
    const m = evidenceToDrawerModel({ subject_ref: 'nope' }, VIEW)
    expect(m.subject).toMatchObject({ kind: 'unknown', headline: 'nope' })
  })

  // The drawn `supersedes` edge runs site→site, but what was overtaken is the OCCUPANCY. Copy
  // that stops at "Karachi replaced by Rahwali (old)" asserts the site was replaced — false.
  it('narrates a supersedes edge as a relocation of its subject, not of the sites', () => {
    const m = evidenceToDrawerModel({ subject_ref: 'sup1' }, VIEW)
    expect(m.subject?.statusless).toBe(true)
    expect(m.subject?.headline).toContain('PA Air Defence moved from Karachi to Rahwali (old)')
    expect(m.supersession).toEqual({
      role: 'link',
      subjectName: 'PA Air Defence',
      fromName: 'Karachi',
      toName: 'Rahwali (old)',
      olderEdgeId: 'e:paad:based-at:karachi',
      newerEdgeId: 'e:paad:based-at:rahwali_stale',
    })
  })

  // "Stale" on the retired basing assertion, with no successor named, is the same failure as
  // "replaced by" with no subject named — so the relocation is reachable from either side of it.
  it('explains the relocation from the retired assertion as well as from the link', () => {
    const older = evidenceToDrawerModel({ subject_ref: 'e:paad:based-at:karachi' }, VIEW)
    expect(older.supersession).toMatchObject({ role: 'older', fromName: 'Karachi', toName: 'Rahwali (old)' })
    const newer = evidenceToDrawerModel({ subject_ref: 'e:paad:based-at:rahwali_stale' }, VIEW)
    expect(newer.supersession?.role).toBe('newer')
    expect(evidenceToDrawerModel({ subject_ref: 'e1' }, VIEW).supersession).toBeUndefined()
  })

  it('marks identity links status-less too, so a null status is never drawn as a gap', () => {
    expect(evidenceToDrawerModel({ subject_ref: 'sa1' }, VIEW).subject?.statusless).toBe(true)
    expect(evidenceToDrawerModel({ subject_ref: 'e1' }, VIEW).subject?.statusless).toBe(false)
  })

  // ── claim content ────────────────────────────────────────────────────────────────────────

  it('reads each claim proposition off its own payload, resolving ids to names', () => {
    const withPayloads = evidenceToDrawerModel(
      {
        subject_ref: 'karachi',
        claims: [
          {
            claim_id: 't1',
            source_id: 's1',
            doc_ref: { file: 'a.txt', line: 4 },
            kind: 'observation',
            asserts: 'relationship',
            payload: { form: 'triple', subject: 'paad', predicate: 'based-at', object: 'karachi' },
          },
          {
            claim_id: 't2',
            source_id: 's1',
            doc_ref: { file: 'a.txt', line: 22 },
            kind: 'observation',
            asserts: 'entity',
            payload: {
              form: 'entity',
              entity_type: 'basing_site',
              name: 'the old Rawalpindi-area site',
              attrs: { occupancy_state: 'negative TEL presence', coordinates: { wgs84_lat: 1 } },
            },
          },
        ],
      },
      VIEW,
    )
    const [t1, t2] = withPayloads.clusters[0].rows
    expect(t1.proposition).toBe('PA Air Defence is based at Karachi')
    expect(t2.proposition).toBe('“the old Rawalpindi-area site” is a basing site')
    // scalars only — a nested coordinate block is structure, not a line of prose
    expect(t2.attrLines).toEqual(['occupancy state — negative TEL presence'])
    // two claims from ONE document must be tellable apart on the chip itself
    expect([t1.locatorShort, t2.locatorShort]).toEqual(['L4', 'L22'])
  })

  // Two claims lifted from the SAME line of one document collide on "L22" — the defect being
  // fixed was three chips that read identically over three different claims.
  it('falls through to the character span when two claims share a line', () => {
    const m = evidenceToDrawerModel({
      subject_ref: 'x',
      claims: [
        { claim_id: 'a', source_id: 's', doc_ref: { file: 'd.txt', line: 22, span: [1359, 1486] }, kind: 'observation', asserts: 'entity' },
        { claim_id: 'b', source_id: 's', doc_ref: { file: 'd.txt', line: 22, span: [1487, 1630] }, kind: 'observation', asserts: 'entity' },
        { claim_id: 'c', source_id: 's', doc_ref: { file: 'd.txt', line: 9 }, kind: 'observation', asserts: 'entity' },
      ],
    })
    const labels = m.clusters[0].rows.map((r) => r.locatorShort)
    expect(labels).toEqual(['L22 · 1359–1486', 'L22 · 1487–1630', 'L9'])
    expect(new Set(labels).size).toBe(labels.length)
  })

  it('emits no proposition (rather than a guess) for a payload shape it cannot phrase', () => {
    const m = evidenceToDrawerModel({
      subject_ref: 'x',
      claims: [{ claim_id: 'c', source_id: 's', doc_ref: { file: 'a' }, kind: 'observation', asserts: 'entity' }],
    })
    expect(m.clusters[0].rows[0].proposition).toBe('')
  })

  // Claims outside every independence group used to be DROPPED — a status-less edge carries all
  // of its citations that way, so the drawer showed an element with three sources as having none.
  it('keeps cited claims that no cluster contains, in an explicitly-ungrouped bucket', () => {
    const m = evidenceToDrawerModel({
      subject_ref: 'sup1',
      claims: [
        { claim_id: 'a', source_id: 's1', doc_ref: { file: 'x' }, kind: 'observation', asserts: 'entity' },
        { claim_id: 'b', source_id: 's2', doc_ref: { file: 'y' }, kind: 'observation', asserts: 'entity' },
      ],
      clusters: [],
    })
    expect(m.looks).toBe(0) // an ungrouped bucket is NOT an independent look
    expect(m.clusters).toHaveLength(1)
    expect(m.clusters[0]).toMatchObject({ groupId: 'ungrouped', ungrouped: true })
    expect(m.claimCount).toBe(2)
  })

  // The header arithmetic has to survive comparison with the body: "2 sources" over four chips
  // was the bug. claimCount counts the rows actually rendered.
  it('counts claims as the rows actually rendered, so the header cannot contradict the body', () => {
    expect(model.claimCount).toBe(3) // c1, c2, c3 — c_missing has no record and is not rendered
    expect(model.sources).toBe(2)
    expect(model.looks).toBe(2)
  })

  // A source id is an internal key; "who says so?" needs the class + grade from the registry.
  it('describes each cluster source by CLASS and grade, never by an invented name', () => {
    const m = evidenceToDrawerModel({
      subject_ref: 'x',
      claims: [
        { claim_id: 'a', source_id: 'd17b', doc_ref: { file: 'x' }, kind: 'observation', asserts: 'entity' },
        { claim_id: 'b', source_id: 'mystery', doc_ref: { file: 'y' }, kind: 'observation', asserts: 'entity' },
      ],
      sources: {
        d17b: {
          source_id: 'd17b',
          source_type: 'satellite',
          reliability_grade: 'B',
          bias_vector: 'third-party',
          report_date: '2025-06-11',
          coordinated_inauthenticity_flag: false,
        },
      },
    })
    const [known, unknown] = m.clusters[0].sources
    expect(known).toMatchObject({
      label: 'Commercial satellite imagery',
      grade: 'B',
      bias: 'third party',
      reportDate: '2025-06-11',
      known: true,
    })
    // an id the registry does not carry is shown as the id, described as nothing
    expect(unknown).toEqual({ sourceId: 'mystery', label: 'mystery', flags: [], known: false })
  })

  it('surfaces registry gate flags on the source that carries them', () => {
    const m = evidenceToDrawerModel({
      subject_ref: 'x',
      claims: [{ claim_id: 'a', source_id: 'r', doc_ref: { file: 'x' }, kind: 'observation', asserts: 'entity' }],
      sources: {
        r: { source_id: 'r', source_type: 'named-social', coordinated_inauthenticity_flag: true },
      },
    })
    expect(m.clusters[0].sources[0].flags).toEqual(['coordinated inauthenticity'])
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
      // untagged → 'evidence', the pre-`kind` contract
      kind: 'evidence',
      reason: 'Needs an unobscured overhead pass.',
      missing: ['unobscured pass', 'SAR correlation'],
      nextCoverageDue: '2026-05-14',
      knownGap: null,
    })
  })

  // "we have no evidence" and "we could not look" are different claims to an analyst; the
  // renderer must be able to tell them apart, so the kind survives the adapter verbatim.
  it('carries a capability refusal through as capability, not as an evidence gap', () => {
    const m = askToAnswerModel({
      question: 'q',
      answer: null,
      refusal: { kind: 'capability', missing: ['a model key (ANTHROPIC_API_KEY)'], reason: 'could not run' },
    })
    expect(m.refusal!.kind).toBe('capability')
    expect(m.refusal!.kind).not.toBe('evidence')
  })

  it('carries a withheld refusal through as withheld', () => {
    const m = askToAnswerModel({ question: 'q', answer: null, refusal: { kind: 'withheld', missing: ['uncited'] } })
    expect(m.refusal!.kind).toBe('withheld')
  })

  it('treats a null answer with no refusal payload as a refusal too', () => {
    const m = askToAnswerModel({ question: 'q', answer: null })
    expect(m.kind).toBe('refusal')
    expect(m.refusal!.kind).toBe('evidence')
    expect(m.refusal).toEqual({ kind: 'evidence', reason: undefined, missing: [], nextCoverageDue: null, knownGap: null })
  })

  it('defaults hops/citations/subQuestions to empty on a bare answer', () => {
    const m = askToAnswerModel({ question: 'q', answer: 'a' })
    expect(m.hops).toEqual([])
    expect(m.citations).toEqual([])
    expect(m.subQuestions).toEqual([])
    expect(m.refusal).toBeUndefined()
  })
})

// ─────────── answer chips → provenance (resolveHopElement / claimElementIndex) ───────────

describe('resolveHopElement', () => {
  const HVIEW: GraphView = {
    nodes: [
      { id: 'unit', type: 'unit', claim_ids: ['n1'] },
      { id: 'variant', type: 'variant', claim_ids: ['n2'] },
    ],
    edges: [
      { id: 'e-equips', type: 'equips', source: 'unit', target: 'variant', claim_ids: ['d06'] },
      // a second edge of the SAME type between the SAME pair — only claim overlap tells them apart
      { id: 'e-equips-2', type: 'equips', source: 'unit', target: 'variant', claim_ids: ['d99'] },
    ],
    events: [],
    known_gaps: [],
    alerts: [],
  }

  it('resolves a hop to the edge it crossed', () => {
    expect(resolveHopElement(HVIEW, { src: 'unit', dst: 'variant', edge: 'equips' })).toBe('e-equips')
  })

  it('matches endpoints in either direction (the walk can cross an edge backwards)', () => {
    expect(resolveHopElement(HVIEW, { src: 'variant', dst: 'unit', edge: 'equips' })).toBe('e-equips')
  })

  it('disambiguates duplicate edges by the claim the hop actually cited', () => {
    const el = resolveHopElement(HVIEW, { src: 'unit', dst: 'variant', edge: 'equips', citations: ['d99'] })
    expect(el).toBe('e-equips-2')
  })

  it('falls back to the destination node when no edge matches', () => {
    expect(resolveHopElement(HVIEW, { src: 'unit', dst: 'variant', edge: 'inferred-link' })).toBe('variant')
  })

  it('returns null (chip stays inert) when neither an edge nor the dst node is known', () => {
    expect(resolveHopElement(HVIEW, { src: 'x', dst: 'ghost', edge: 'equips' })).toBeNull()
    expect(resolveHopElement(null, { src: 'unit', dst: 'variant', edge: 'equips' })).toBeNull()
  })
})

describe('claimElementIndex', () => {
  const CVIEW: GraphView = {
    nodes: [{ id: 'unit', type: 'unit', claim_ids: ['n1', 'shared'] }],
    edges: [{ id: 'e-equips', type: 'equips', source: 'unit', target: 'variant', claim_ids: ['d06', 'shared'] }],
    events: [],
    known_gaps: [],
    alerts: [],
  }

  it('maps a claim to the element that carries it', () => {
    const idx = claimElementIndex(CVIEW)
    expect(idx.get('n1')).toBe('unit')
    expect(idx.get('d06')).toBe('e-equips')
  })

  it('prefers the edge binding when a claim id sits on both a node and an edge', () => {
    expect(claimElementIndex(CVIEW).get('shared')).toBe('e-equips')
  })

  it('is empty for a null view', () => {
    expect(claimElementIndex(null).size).toBe(0)
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

// ─────────────────── live tripwires / alert provenance (derived) ───────────────────
// The fixture below is the REAL firing the backend produces on the frozen corpus
// (obs-basing-relocation on unit_hq9b, Rawalpindi → Rahwali), including the actual
// claim ids and the status/confidence copied off the after-edge.

describe('viewToTripwires / alertToFiring', () => {
  const BEFORE_EDGE = 'e:unit_hq9b:based-at:site_rawalpindi'
  const AFTER_EDGE = 'e:unit_hq9b:based-at:site_rahwali'

  const AVIEW: GraphView = {
    nodes: [
      { id: 'unit_hq9b', type: 'unit', name: 'HQ-9B fire unit', status: 'confirmed' },
      { id: 'site_rawalpindi', type: 'basing_site', name: 'Rawalpindi', status: 'stale' },
      { id: 'site_rahwali', type: 'basing_site', name: 'Rahwali', status: 'probable' },
    ],
    edges: [
      {
        id: BEFORE_EDGE,
        type: 'based-at',
        source: 'unit_hq9b',
        target: 'site_rawalpindi',
        status: 'stale', // history — the unit left, NOT an evidence gap
        confidence: { integrity_flags: ['superseded'] },
        attrs: {
          supersede_gate: 'held',
          candidate_supersede: true,
          supersede_hold_reason: ['newer-below-probable', 'newer-deception-gate:decoy-risk'],
        },
      },
      {
        id: AFTER_EDGE,
        type: 'based-at',
        source: 'unit_hq9b',
        target: 'site_rahwali',
        status: 'probable',
      },
      // the status-less version link the backend draws once a supersession is promoted
      {
        id: 'e:site_rahwali:supersedes:site_rawalpindi',
        type: 'supersedes',
        source: 'site_rahwali',
        target: 'site_rawalpindi',
        status: null,
        confidence: null,
        attrs: { derived_via: 'supersede' },
      },
    ],
    events: [],
    known_gaps: [],
    alerts: [
      {
        observable_id: 'obs-basing-relocation',
        subject: 'unit_hq9b',
        before: { 'based-at': 'site_rawalpindi' },
        after: { 'based-at': 'site_rahwali' },
        severity: 'notify',
        fired_ts: '2026-07-19',
        disposition: null,
        provenance: {
          before_ref: BEFORE_EDGE,
          after_ref: AFTER_EDGE,
          before_claim_ids: ['d17-rawalpindi-2021-unit-hq9b-site-rawalpindi-basing'],
          after_claim_ids: [
            'd18-rahwali-pass1-unit-hq9b-site-rahwali-basing',
            'd19-rahwali-confirm-unit-hq9b-site-rahwali-basing',
          ],
          claim_ids: [
            'd17-rawalpindi-2021-unit-hq9b-site-rawalpindi-basing',
            'd18-rahwali-pass1-unit-hq9b-site-rahwali-basing',
            'd19-rahwali-confirm-unit-hq9b-site-rahwali-basing',
          ],
          status: 'probable',
          assertion_confidence: 0.79,
        },
      },
    ],
  }

  const rows = viewToTripwires(AVIEW)

  it('derives one row per observable that actually fired', () => {
    expect(rows).toHaveLength(1)
    expect(rows[0].observableId).toBe('obs-basing-relocation')
    expect(rows[0].firings).toHaveLength(1)
  })

  it('humanises the observable id into the row name (no catalogue endpoint exists)', () => {
    expect(rows[0].name).toBe('Basing relocation')
    expect(humanizeObservableId('obs-followon-interceptor-order')).toBe('Followon interceptor order')
  })

  it('DERIVES the state badge — un-adjudicated reads "fired", never a hardcoded "armed"', () => {
    expect(rows[0].state).toBe('fired')
    expect(rows[0].stateLabel).toBe('fired')
    expect(rows[0].stateLabel).not.toBe('armed')
  })

  it('reads the analyst disposition back as the state once one is recorded', () => {
    const decided = viewToTripwires({
      ...AVIEW,
      alerts: [{ ...AVIEW.alerts[0], disposition: 'noise' }],
    })
    expect(decided[0].state).toBe('noise')
    expect(decided[0].stateLabel).toBe('dismissed as noise')
  })

  it('summarises before → after off the real snapshots', () => {
    expect(rows[0].firings[0].changed).toEqual({
      from: 'based-at: site_rawalpindi',
      to: 'based-at: site_rahwali',
    })
  })

  it('splits provenance into before/after sides, each with its element ref + claim ids', () => {
    const p = rows[0].firings[0].provenance!
    expect(p.sides).toEqual([
      {
        side: 'before',
        elementRef: BEFORE_EDGE,
        claimIds: ['d17-rawalpindi-2021-unit-hq9b-site-rawalpindi-basing'],
      },
      {
        side: 'after',
        elementRef: AFTER_EDGE,
        claimIds: [
          'd18-rahwali-pass1-unit-hq9b-site-rahwali-basing',
          'd19-rahwali-confirm-unit-hq9b-site-rahwali-basing',
        ],
      },
    ])
    expect(p.claimIds).toHaveLength(3)
    expect(p.status).toBe('probable')
    expect(p.assertionConfidence).toBeCloseTo(0.79)
  })

  it('falls back to the before+after union when claim_ids is absent', () => {
    const f = alertToFiring({
      observable_id: 'o',
      provenance: { before_claim_ids: ['c1'], after_claim_ids: ['c2', 'c1'] },
    })
    expect(f.provenance!.claimIds).toEqual(['c1', 'c2'])
  })

  it('reports a provenance-less alert as null rather than inventing a citation', () => {
    const f = alertToFiring({ observable_id: 'o', subject: 's' })
    expect(f.provenance).toBeNull()
    expect(f.holdReasons).toEqual([])
  })

  it('surfaces supersede_hold_reason VERBATIM off the referenced edges, de-duplicated', () => {
    expect(rows[0].firings[0].holdReasons).toEqual([
      'newer-below-probable',
      'newer-deception-gate:decoy-risk',
    ])
    expect(rows[0].firings[0].gate).toBe('held')
  })

  it('tolerates a bare-string hold reason and ignores junk', () => {
    expect(supersedeHoldReasons({ id: 'e', type: 'based-at', source: 'a', target: 'b', attrs: { supersede_hold_reason: 'newer-below-probable' } })).toEqual(['newer-below-probable'])
    expect(supersedeHoldReasons({ id: 'e', type: 'based-at', source: 'a', target: 'b', attrs: { supersede_hold_reason: 7 } })).toEqual([])
    expect(supersedeHoldReasons({ id: 'e', type: 'based-at', source: 'a', target: 'b' })).toEqual([])
    expect(supersedeHoldReasons(undefined)).toEqual([])
  })

  it('returns an empty feed (not demo content) for a live view with no alerts', () => {
    expect(viewToTripwires({ nodes: [], edges: [], events: [], known_gaps: [], alerts: [] })).toEqual([])
  })

  it('carries the same provenance + hold reasons onto the review-queue alert card', () => {
    const alert = viewToReviewQueue(AVIEW).find((i) => i.reviewType === 'alert-disposition')!
    expect(alert.subject).toBe('unit_hq9b')
    expect(alert.context.provenance!.sides).toHaveLength(2)
    expect(alert.context.holdReasons).toEqual([
      'newer-below-probable',
      'newer-deception-gate:decoy-risk',
    ])
  })
})

// ─────────────────────── location precision, honestly rendered (T5) ───────────────────────
// The map used to draw three pins because the backend resolved almost nothing to a
// coordinate. Now that it does, the risk flips: everything gets drawn, and a province
// centroid starts to look like a fix. These tests pin the distinction the map exists to
// make — a point you could put a reticle on vs. an area a source vaguely gestured at.

const PRECISION_VIEW: GraphView = {
  nodes: [
    {
      id: 'pad_site',
      type: 'basing_site',
      name: 'Malir emplacement',
      status: 'confirmed',
      location: { wgs84_lat: 24.9012, wgs84_lon: 67.2034, precision_class: 'pad', surface_format: 'DMS' },
      attrs: { location_uncertainty_radius_m: 500, location_source: 'stated-coordinate' },
    },
    {
      id: 'punjab_a',
      type: 'basing_site',
      name: 'air defence node',
      status: 'possible',
      location: { wgs84_lat: 31.1471, wgs84_lon: 72.7097, precision_class: 'province', raw: 'Punjab Province, Pakistan' },
      attrs: { location_uncertainty_radius_m: 150000, location_source: 'gazetteer-anchor' },
    },
    {
      id: 'punjab_b',
      type: 'basing_site',
      name: 'fenced compound',
      status: 'possible',
      location: { wgs84_lat: 31.1471, wgs84_lon: 72.7097, precision_class: 'province', raw: 'central Punjab' },
      attrs: { location_uncertainty_radius_m: 150000, location_source: 'gazetteer-anchor' },
    },
    {
      id: 'unplaced',
      type: 'basing_site',
      name: 'garrison in a western military district',
      status: 'insufficient',
      location: { raw: "China's western military district", surface_format: 'toponym' },
    },
  ],
  edges: [],
  events: [],
  known_gaps: [],
  alerts: [],
}

describe('location precision', () => {
  const pins = viewToPins(PRECISION_VIEW)

  it('carries precision, uncertainty radius and coordinate provenance onto every pin', () => {
    expect(pins).toHaveLength(3) // the unplaced node is not a pin
    expect(pins.find((p) => p.id === 'pad_site')).toMatchObject({
      precision: 'pad',
      uncertaintyRadiusM: 500,
      locationSource: 'stated-coordinate',
    })
  })

  it('states BOTH the point and how well it is known in the coord readout', () => {
    // showing the coordinate alone hides a 150 km envelope; showing the format alone hides the point
    expect(pins.find((p) => p.id === 'pad_site')!.coord).toBe('24.90°N  67.20°E  DMS  ±500 m')
    expect(pins.find((p) => p.id === 'punjab_a')!.coord).toContain('±150 km')
  })

  it('separates points from areas — a province is never a point', () => {
    expect(isAreaPin(pins.find((p) => p.id === 'pad_site')!)).toBe(false)
    expect(isAreaPin(pins.find((p) => p.id === 'punjab_a')!)).toBe(true)
  })

  it('treats an anchor-derived point of unknown precision as an area, not a point', () => {
    expect(isAreaPin({ ...pins[0], precision: null, locationSource: 'gazetteer-anchor' })).toBe(true)
    expect(isAreaPin({ ...pins[0], precision: null, locationSource: 'stated-coordinate' })).toBe(false)
  })

  it('formats a radius in the unit a reader thinks in', () => {
    expect(formatRadius(500)).toBe('500 m')
    expect(formatRadius(15000)).toBe('15 km')
  })
})

describe('clusterAreaPins', () => {
  const clustered = clusterAreaPins(viewToPins(PRECISION_VIEW))

  it('folds two entities that share one area anchor into a single counted marker', () => {
    expect(clustered).toHaveLength(2)
    const area = clustered.find((p) => p.id !== 'pad_site')!
    expect(area.label).toBe('2 entities')
    expect(area.caption).toBe('located to this area only')
    expect(area.members).toEqual(['punjab_a', 'punjab_b'])
  })

  it('never clusters point pins — those ARE distinguishable positions', () => {
    const point = clustered.find((p) => p.id === 'pad_site')!
    expect(point.label).toBe('Malir emplacement')
    expect(point.members).toBeUndefined()
  })

  it('is deterministic — members sort by id and the first is the survivor', () => {
    const reversed = clusterAreaPins([...viewToPins(PRECISION_VIEW)].reverse())
    const area = reversed.find((p) => p.members && p.members.length > 1)!
    expect(area.id).toBe('punjab_a')
    expect(area.members).toEqual(['punjab_a', 'punjab_b'])
  })

  it('leaves a lone area pin naming itself', () => {
    const single = clusterAreaPins(
      viewToPins({ ...PRECISION_VIEW, nodes: PRECISION_VIEW.nodes.filter((n) => n.id !== 'punjab_b') }),
    )
    expect(single.find((p) => p.id === 'punjab_a')!.label).toBe('air defence node')
  })
})

describe('unplacedLocations', () => {
  it('surfaces a node the graph knows is somewhere and the map will not draw', () => {
    expect(unplacedLocations(PRECISION_VIEW)).toEqual([
      {
        id: 'unplaced',
        label: 'garrison in a western military district',
        stated: "China's western military district",
        type: 'basing_site',
      },
    ])
  })

  it('ignores nodes with no location at all — those are not a placement failure', () => {
    expect(unplacedLocations(VIEW).map((u) => u.id)).not.toContain('paad')
  })
})

// ─────────────── review-queue legibility: row identity, evidence, triage ───────────────
// The failure this covers: 40+ rows all reading "Merge · Close call · Same system, or two?".
// A row must name its own subject, the card must be built from the clicked item, and a run of
// connected proposals must read as one cluster — WITHOUT anything being dropped or auto-decided.

describe('review queue — rows identify themselves', () => {
  const RVIEW: GraphView = {
    nodes: [
      {
        id: 'karachi_adc',
        type: 'basing_site',
        name: 'Army Air Defence Centre, Karachi',
        status: 'probable',
        claim_ids: ['c1'],
        location: { raw: 'Karachi' },
        attrs: { site_type: 'air defence centre' },
      },
      {
        id: 'sargodha',
        type: 'basing_site',
        name: 'Sargodha',
        status: 'probable',
        claim_ids: ['c2'],
        attrs: { site_type: 'deployment site' },
      },
      {
        id: 'ht233',
        type: 'component',
        name: 'HT-233',
        status: 'confirmed',
        claim_ids: ['c3', 'c4'],
        materiality: { chokepoint_status: 'candidate' },
      },
      { id: 'type305b', type: 'component', name: 'Type 305B', status: 'probable', claim_ids: ['c5'] },
    ],
    edges: [
      {
        id: 'sa:karachi',
        type: 'same-as',
        source: 'karachi_adc',
        target: 'sargodha',
        merge_confidence: 0.63,
        attrs: {
          merge_band: 'candidate',
          breakdown: { attribute: 0.46, relational: 1, temporal_consistency: 1, source_asserted: 0, total: 0.63 },
        },
      },
      {
        id: 'sa:radar',
        type: 'same-as',
        source: 'ht233',
        target: 'type305b',
        merge_confidence: 0.82,
        attrs: { breakdown: { attribute: 0.9, relational: 0, temporal_consistency: 1, source_asserted: 0, total: 0.82 } },
      },
      { id: 'e1', type: 'supplies-component', source: 'ht233', target: 'type305b', status: 'confirmed' },
    ],
    events: [],
    known_gaps: [],
    alerts: [],
  }

  const queue = viewToReviewQueue(RVIEW)
  const karachi = queue.find((i) => i.subject === 'sa:karachi')!
  const radar = queue.find((i) => i.subject === 'sa:radar')!

  it('titles a merge row with BOTH candidate records, not a generic question', () => {
    expect(karachi.title).toBe('Army Air Defence Centre, Karachi ↔ Sargodha')
    expect(radar.title).toBe('HT-233 ↔ Type 305B')
    // the question moves to the card headline; it is no longer what distinguishes a row
    expect(karachi.question).toBe('Same system, or two?')
    expect(karachi.title).not.toBe(radar.title)
  })

  it('bands the badge off the recorded identity confidence instead of a fixed "Close call"', () => {
    expect(karachi.badge).toBe('Close call') // credibilityToDots(0.63) === 3
    expect(radar.badge).toBe('Strong match') // credibilityToDots(0.82) === 4
    expect(karachi.note).toContain('0.63')
  })

  it('flags materiality so triage can lead with it', () => {
    expect(radar.material).toBe(true)
    expect(radar.badges).toContain('Touches a chokepoint')
    expect(karachi.material).toBe(false)
  })

  it('renders the resolver’s own per-signal breakdown as the case FOR', () => {
    const labels = karachi.context.merge!.matchedOn.map((r) => r.label)
    // zero-scored signals are NOT in matched-on — they are the case against
    expect(labels).not.toContain('A source calls them the same')
    expect(labels).toContain('Shared neighbours in the graph')
    expect(karachi.context.merge!.matchedOn[0].score).toBe(1)
  })

  it('derives the case AGAINST from the records themselves + the zero-scored signals', () => {
    const differs = karachi.context.merge!.differsOn
    expect(differs.some((d) => d.includes('Stated location'))).toBe(true)
    expect(differs.some((d) => d.includes('air defence centre') && d.includes('deployment site'))).toBe(true)
    expect(differs).toContain('No source states they are the same.')
  })

  it('counts the consequence off the graph and admits what it cannot predict', () => {
    const m = karachi.context.merge!
    expect(m.consequence[0]).toContain('Joins 2 sourced claims')
    expect(m.consequence[1]).toContain('0 graph edges') // neither basing site has an assertional edge
    // the radar pair DOES have one real edge on each endpoint
    expect(radar.context.merge!.consequence[1]).toContain('2 graph edges re-point')
    // never a predicted status — the one number this card must not invent
    expect(m.unknowns.join(' ')).toContain('recomputed at rebuild')
    expect(JSON.stringify(m.consequence)).not.toContain('node statuses')
  })

  it('names the chokepoint consequence when a candidate chokepoint is involved', () => {
    expect(radar.context.merge!.consequence.join(' ')).toContain('candidate chokepoint')
  })
})

describe('mergeDiffersOn', () => {
  it('states a coordinate distance when both sides are located', () => {
    const left = { id: 'a', type: 'basing_site', location: { wgs84_lat: 24.86, wgs84_lon: 67.01 } }
    const right = { id: 'b', type: 'basing_site', location: { wgs84_lat: 32.05, wgs84_lon: 72.67 } }
    const out = mergeDiffersOn(left, right, {})
    expect(out.some((d) => /Coordinates — [\d,]+ km apart\./.test(d))).toBe(true)
  })

  it('says a type mismatch out loud', () => {
    expect(mergeDiffersOn({ id: 'a', type: 'unit' }, { id: 'b', type: 'basing_site' }, {})).toContain(
      'Type — unit vs basing site.',
    )
  })

  it('returns nothing when the two records genuinely do not conflict', () => {
    const same = { id: 'a', type: 'variant', attrs: { family: 'HQ-16' } }
    expect(mergeDiffersOn(same, { ...same, id: 'b' }, { attribute: 0.9, relational: 0.5 })).toEqual([])
  })
})

describe('T10 — the merge card is traceable to its sources', () => {
  // Same shape as the review-queue view above, but the radar pair now has a source-asserted identity
  // (with the claims that assert it on the candidate edge, as view/pipeline._resolution_edges writes
  // them) and the basing pair has none. The contrast IS the test.
  const TVIEW: GraphView = {
    nodes: [
      { id: 'ht233', type: 'component', name: 'HT-233', status: 'confirmed', claim_ids: ['c3', 'c4'], attrs: { role: 'engagement radar' } },
      { id: 'type120', type: 'component', name: 'Type 120 / YLC series', status: 'probable', claim_ids: ['c5', 'c6'], attrs: { role: 'acquisition radar' } },
      { id: 'karachi_adc', type: 'basing_site', name: 'Army Air Defence Centre, Karachi', status: 'probable', claim_ids: ['c1'] },
      { id: 'sargodha', type: 'basing_site', name: 'Sargodha', status: 'probable', claim_ids: ['c2'] },
    ],
    edges: [
      {
        id: 'same-as:ht233|type120',
        type: 'same-as',
        source: 'ht233',
        target: 'type120',
        merge_confidence: 0.37,
        claim_ids: ['d15-globaltimes-aligned-l17-5'],
        attrs: { breakdown: { attribute: 0.47, relational: 0.07, temporal_consistency: 1, source_asserted: 0.7 } },
      },
      {
        id: 'same-as:karachi|sargodha',
        type: 'same-as',
        source: 'karachi_adc',
        target: 'sargodha',
        merge_confidence: 0.52,
        attrs: { breakdown: { attribute: 0.67, relational: 0.5, temporal_consistency: 1, source_asserted: 0 } },
      },
    ],
    events: [],
    known_gaps: [],
    alerts: [],
  }
  const queue = viewToReviewQueue(TVIEW)
  const cited = queue.find((i) => i.subject === 'same-as:ht233|type120')!
  const uncited = queue.find((i) => i.subject === 'same-as:karachi|sargodha')!

  it('gives the source-asserted signal — and ONLY it — an evidence handle', () => {
    const rows = cited.context.merge!.matchedOn
    const asserted = rows.find((r) => r.key === 'source_asserted')!
    // the candidate edge id is the handle: GET /evidence/{id} serves exactly its identity claims
    expect(asserted.evidenceId).toBe('same-as:ht233|type120')
    expect(asserted.evidenceCount).toBe(1)
    // every other signal is the resolver's own arithmetic over the two records — nothing to open
    expect(rows.filter((r) => r.key !== 'source_asserted').every((r) => r.evidenceId === undefined)).toBe(true)
  })

  it('offers NO handle when no source asserted the identity — never a link into an empty drawer', () => {
    expect(uncited.context.merge!.matchedOn.every((r) => r.evidenceId === undefined)).toBe(true)
    // and the absence is stated as the case AGAINST instead
    expect(uncited.context.merge!.differsOn).toContain('No source states they are the same.')
  })

  it('makes each record openable, with its claim count as the handle', () => {
    const m = cited.context.merge!
    expect(m.left.evidenceId).toBe('ht233')
    expect(m.left.claimCount).toBe(2)
    expect(m.right.evidenceId).toBe('type120')
  })

  it('attributes a differs-on line read off the records to those records', () => {
    const role = cited.context.merge!.differs.find((d) => d.text.includes('engagement radar'))!
    expect(role.text).toContain('engagement radar')
    expect(role.sides).toEqual(['left', 'right'])
    expect(role.computed).toBeUndefined() // a stated value is not a computation
  })

  it('marks a computed line as computed rather than dressing it as a citation', () => {
    const absent = uncited.context.merge!.differs.find((d) => d.text === 'No source states they are the same.')!
    expect(absent.sides).toEqual([])
    expect(absent.computed).toContain('resolver')
  })

  it('keeps differsOn as the plain-text projection of differs', () => {
    expect(cited.context.merge!.differsOn).toEqual(cited.context.merge!.differs.map((d) => d.text))
  })
})

describe('mergeDifferences — provenance per line', () => {
  it('says a coordinate distance is arithmetic over the two records, not a quote', () => {
    const left = { id: 'a', type: 'basing_site', location: { wgs84_lat: 24.86, wgs84_lon: 67.01 } }
    const right = { id: 'b', type: 'basing_site', location: { wgs84_lat: 32.05, wgs84_lon: 72.67 } }
    const km = mergeDifferences(left, right, {}).find((d) => d.text.startsWith('Coordinates'))!
    expect(km.computed).toContain('computed')
  })

  it('attributes a one-sided stated location to the side that states it', () => {
    const left = { id: 'a', type: 'basing_site', location: { raw: 'Karachi' } }
    const right = { id: 'b', type: 'basing_site' }
    const loc = mergeDifferences(left, right, {}).find((d) => d.text.startsWith('Stated location'))!
    expect(loc.sides).toEqual(['left'])
  })
})

describe('orderReviewQueue / groupReviewQueue', () => {
  // one 4-record blob (all 6 pairs proposed) + two unrelated pairs + one override
  const names = ['Punjab', 'Sindh', 'Sargodha', 'Karachi']
  const blobNodes = names.map((n, i) => ({ id: `b${i}`, type: 'basing_site', name: n, claim_ids: [`c${i}`] }))
  const blobEdges = []
  for (let i = 0; i < 4; i++) {
    for (let j = i + 1; j < 4; j++) {
      blobEdges.push({
        id: `sa:b${i}|b${j}`,
        type: 'same-as',
        source: `b${i}`,
        target: `b${j}`,
        merge_confidence: 0.6,
        attrs: { breakdown: { attribute: 0.5, relational: 1, temporal_consistency: 1, source_asserted: 0 } },
      })
    }
  }
  const GVIEW: GraphView = {
    nodes: [
      ...blobNodes,
      { id: 'cpmiec', type: 'manufacturer', name: 'CPMIEC', claim_ids: ['x1'] },
      { id: 'cnpmiec', type: 'manufacturer', name: 'China National Precision Machinery', claim_ids: ['x2'] },
      { id: 'ly80', type: 'variant', name: 'LY-80', claim_ids: ['y1'] },
      { id: 'hq16', type: 'variant', name: 'HQ-16', claim_ids: ['y2'] },
      { id: 'contra', type: 'unit', name: 'HQ-9B fire unit', status: 'contradicted' },
    ],
    edges: [
      ...blobEdges,
      { id: 'sa:org', type: 'same-as', source: 'cpmiec', target: 'cnpmiec', merge_confidence: 0.9 },
      { id: 'sa:var', type: 'same-as', source: 'ly80', target: 'hq16', merge_confidence: 0.7 },
    ],
    events: [],
    known_gaps: [],
    alerts: [],
  }

  const queue = viewToReviewQueue(GVIEW)
  const groups = groupReviewQueue(queue)

  it('never loses an item — the groups are a permutation of the queue', () => {
    const flat = groups.flatMap((g) => g.items.map((i) => i.itemId)).sort()
    expect(flat).toEqual(queue.map((i) => i.itemId).sort())
    expect(groups.flatMap((g) => g.items)).toHaveLength(9) // 8 merges + 1 override
  })

  it('collapses the connected run into ONE cluster and leaves the isolated pairs alone', () => {
    const clusters = groups.filter((g) => g.kind === 'cluster')
    expect(clusters).toHaveLength(1)
    expect(clusters[0].items).toHaveLength(6)
    expect(clusters[0].title).toBe('4 records, 6 merge proposals')
    // the density IS the finding: every possible pair proposed ⇒ not independent evidence
    expect(clusters[0].note).toContain('every one of the 6 possible pairs is proposed')
    expect(groups.filter((g) => g.kind === 'single')).toHaveLength(3) // 2 pairs + the override
  })

  it('carries the cluster onto each member so the card says what the header said', () => {
    const member = groups.find((g) => g.kind === 'cluster')!.items[0]
    expect(member.cluster).toMatchObject({ size: 6, records: 4, complete: true })
  })

  it('leads with the ★ pinned order (status-override, merge, alert), then materiality', () => {
    expect(groups[0].items[0].reviewType).toBe('status-override')
    const ordered = orderReviewQueue(queue)
    expect(ordered[0].reviewType).toBe('status-override')
    // among merges, the most confident identity claim comes first
    const merges = ordered.filter((i) => i.reviewType === 'merge')
    expect(merges[0].subject).toBe('sa:org')
  })

  it('puts a crisp two-record decision ahead of the systemic cluster', () => {
    const kinds = groups.map((g) => g.kind)
    expect(kinds.lastIndexOf('cluster')).toBe(kinds.length - 1)
  })
})
