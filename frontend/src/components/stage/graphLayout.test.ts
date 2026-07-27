import { describe, expect, it } from 'vitest'
import type { GraphEdgeDef, GraphNodeDef } from '@/demo/scenario'
import {
  COL_W,
  DEFAULT_LAYERS,
  countIdentityEdges,
  countProposals,
  countSeparations,
  egoNodes,
  groupByType,
  planGraph,
  roleRank,
} from './graphLayout'

/** Knowledge only — both identity layers off. */
const NO_IDENTITY = { separations: false, proposals: false, evidence: false }

// A miniature of the real cold-boot shape: a domain chain, an entity reachable ONLY via a
// same-as link, a pair of orphans, a Known Gap, and two evidence-layer source records.
const N = (id: string, type: string, kind: GraphNodeDef['kind'] = 'probable'): GraphNodeDef => ({
  id,
  label: `${id}\n${type}`,
  name: id,
  x: 0,
  y: 0,
  kind,
  type,
})
const IDENTITY_KIND: Record<string, GraphEdgeDef['kind']> = {
  'same-as': 'e-merge-candidate',
  'distinct-from': 'e-wall',
  'coref-distinct-from': 'e-wall',
}
const E = (id: string, source: string, target: string, type: string): GraphEdgeDef => ({
  id,
  source,
  target,
  kind: IDENTITY_KIND[type] ?? 'e-confirmed',
  type,
})

const NODES: GraphNodeDef[] = [
  N('casic', 'manufacturer'),
  N('ht233', 'component', 'chokepoint'),
  N('imp21', 'contract_import_event'),
  N('hq9p', 'variant'),
  N('paad', 'unit'),
  N('karachi', 'basing_site'),
  N('alias_ft2000', 'variant'), // reachable only through an identity edge
  N('orphan_a', 'component'),
  N('orphan_b', 'basing_site'),
  N('gap_tel', 'known_gap', 'gap'),
  N('src_d05', 'source'),
  N('src_d07', 'source'),
]

const EDGES: GraphEdgeDef[] = [
  E('e1', 'casic', 'ht233', 'manufactures'),
  E('e2', 'ht233', 'hq9p', 'component-of'),
  E('e3', 'imp21', 'hq9p', 'imported-by'),
  E('e4', 'hq9p', 'paad', 'inducted-into'),
  E('e5', 'paad', 'karachi', 'based-at'),
  E('sa1', 'hq9p', 'alias_ft2000', 'same-as'),
  E('df1', 'alias_ft2000', 'orphan_a', 'distinct-from'),
  // A separation between two entities the world already connects — the shape of the Pano Aqil
  // trap (two co-located positions asserted by a source to be different things).
  E('cdf1', 'karachi', 'ht233', 'coref-distinct-from'),
  // …and a proposed merge between two entities the world already connects
  E('sa2', 'ht233', 'imp21', 'same-as'),
]

describe('planGraph — knowledge layer only', () => {
  const plan = planGraph(NODES, EDGES, NO_IDENTITY)

  it('draws only domain relationships when both identity layers are off', () => {
    expect(plan.canvasEdges.has('sa1')).toBe(false)
    expect(plan.canvasEdges.has('df1')).toBe(false)
    expect(plan.canvasEdges.has('cdf1')).toBe(false)
    expect(plan.canvasEdges.size).toBe(5)
  })

  it('keeps evidence-layer source records off the canvas', () => {
    expect(plan.canvasNodes.has('src_d05')).toBe(false)
    expect(plan.canvasNodes.has('src_d07')).toBe(false)
  })

  it('draws exactly the entities that hold a drawn relationship', () => {
    expect([...plan.canvasNodes].sort()).toEqual(['casic', 'hq9p', 'ht233', 'imp21', 'karachi', 'paad'])
  })

  // The non-negotiable: nothing is quietly filtered. Everything off-canvas is enumerable.
  it('surfaces every unconnected in-layer entity rather than dropping it', () => {
    const ids = plan.unconnected.map((n) => n.id).sort()
    expect(ids).toEqual(['alias_ft2000', 'gap_tel', 'orphan_a', 'orphan_b'])
  })

  it('accounts for every in-layer node exactly once — canvas + unconnected', () => {
    const inLayer = NODES.filter((n) => n.type !== 'source')
    expect(plan.canvasNodes.size + plan.unconnected.length).toBe(inLayer.length)
  })
})

describe('planGraph — separations (on by default)', () => {
  const plan = planGraph(NODES, EDGES, DEFAULT_LAYERS)

  it('draws a separation between two entities the world already connects', () => {
    expect(plan.canvasEdges.has('cdf1')).toBe(true)
  })

  it('treats a source-asserted `coref-distinct-from` as a separation, not a relationship', () => {
    // It carries a status and would otherwise ride the knowledge layer as an ordinary line —
    // a "these are NOT the same thing" edge drawn as a connection.
    expect(planGraph(NODES, EDGES, NO_IDENTITY).canvasEdges.has('cdf1')).toBe(false)
  })

  it('leaves un-adjudicated merge proposals off until asked', () => {
    expect(plan.canvasEdges.has('sa2')).toBe(false)
    expect(planGraph(NODES, EDGES, { ...DEFAULT_LAYERS, proposals: true }).canvasEdges.has('sa2')).toBe(
      true,
    )
  })

  // An identity edge is bookkeeping about our records. Letting one promote an entity onto the
  // canvas would empty the "no asserted relationship" tray — a collection FINDING — with something
  // that is not knowledge about the world at all.
  it('never promotes an entity onto the canvas on the strength of an identity edge alone', () => {
    const both = planGraph(NODES, EDGES, { separations: true, proposals: true, evidence: false })
    expect(both.canvasNodes.has('alias_ft2000')).toBe(false)
    expect(both.canvasNodes.has('orphan_a')).toBe(false)
    expect(both.unconnected.map((n) => n.id).sort()).toEqual([
      'alias_ft2000',
      'gap_tel',
      'orphan_a',
      'orphan_b',
    ])
  })

  // Counted AND still reachable: the whole-graph view holds them back (the caller hides an edge
  // whose endpoint is off-canvas), but they stay in the focus adjacency, so focusing either
  // endpoint draws them. A wall the analyst can never reach is a judgement that reached nobody.
  it('counts — never silently drops — the identity decisions the whole-graph view holds back', () => {
    const both = planGraph(NODES, EDGES, { separations: true, proposals: true, evidence: false })
    expect(both.undrawableIdentity).toBe(2)
    expect(both.adjacency.get('alias_ft2000')).toContain('hq9p')
    expect(both.adjacency.get('orphan_a')).toContain('alias_ft2000')
  })

  it('reports nothing undrawable when the identity layers are off', () => {
    expect(planGraph(NODES, EDGES, NO_IDENTITY).undrawableIdentity).toBe(0)
  })
})

describe('planGraph — evidence layer', () => {
  it('admits source records, which then show up as unconnected (they carry claims, not edges)', () => {
    const plan = planGraph(NODES, EDGES, { ...NO_IDENTITY, evidence: true })
    expect(plan.unconnected.map((n) => n.id)).toContain('src_d05')
    expect(plan.canvasNodes.has('src_d05')).toBe(false)
  })
})

describe('planGraph — layout', () => {
  const plan = planGraph(NODES, EDGES, NO_IDENTITY)

  it('bands nodes into supply-chain role columns, left → right', () => {
    const x = (id: string) => plan.positions.get(id)!.x
    expect(x('casic')).toBeLessThan(x('ht233'))
    expect(x('ht233')).toBeLessThan(x('imp21'))
    expect(x('imp21')).toBeLessThan(x('hq9p'))
    expect(x('hq9p')).toBeLessThan(x('paad'))
    expect(x('paad')).toBeLessThan(x('karachi'))
  })

  it('opens no gap for a role band with nothing on the canvas', () => {
    const drawnXs = [...plan.canvasNodes].map((id) => plan.positions.get(id)!.x)
    const slots = [...new Set(drawnXs)].sort((a, b) => a - b)
    expect(slots).toEqual(slots.map((_, i) => i * COL_W))
  })

  it('gives every node a position, on canvas or not', () => {
    for (const n of NODES) expect(plan.positions.has(n.id)).toBe(true)
  })

  // CLAUDE.md: the demo must render the same every run. No physics, no seeded randomness.
  it('is deterministic — same input, byte-identical positions', () => {
    const a = planGraph(NODES, EDGES, NO_IDENTITY)
    const b = planGraph([...NODES].reverse(), [...EDGES].reverse(), NO_IDENTITY)
    for (const id of a.canvasNodes) expect(b.positions.get(id)).toEqual(a.positions.get(id))
  })

  it('draws no heading for a band with nothing on the canvas', () => {
    expect(plan.columns.find((c) => c.type === 'source')?.count).toBe(0)
    expect(plan.columns.find((c) => c.type === 'unit')?.count).toBe(1)
  })
})

describe('egoNodes', () => {
  const plan = planGraph(NODES, EDGES, NO_IDENTITY)

  it('1 hop is the node and its immediate relationships', () => {
    expect([...egoNodes(plan.adjacency, 'hq9p', 1)].sort()).toEqual(['ht233', 'hq9p', 'imp21', 'paad'].sort())
  })

  it('2 hops reaches the supplier and the basing site', () => {
    const ego = egoNodes(plan.adjacency, 'hq9p', 2)
    expect(ego.has('casic')).toBe(true)
    expect(ego.has('karachi')).toBe(true)
  })

  it('3 hops spans the whole traced chain', () => {
    expect(egoNodes(plan.adjacency, 'karachi', 3).size).toBe(5)
  })

  // An entity with no asserted relationship focuses to itself — which IS the finding.
  it('returns just the node when nothing connects to it', () => {
    expect([...egoNodes(plan.adjacency, 'orphan_b', 3)]).toEqual(['orphan_b'])
  })
})

describe('helpers', () => {
  it('counts the identity links the chips offer, split by what they assert', () => {
    expect(countIdentityEdges(EDGES)).toBe(4)
    // a source-asserted separation counts as a separation, not as a domain relationship
    expect(countSeparations(EDGES)).toBe(2)
    expect(countProposals(EDGES)).toBe(2)
  })

  it('groups the unconnected tray by type, biggest group first', () => {
    const groups = groupByType([N('a', 'component'), N('b', 'component'), N('c', 'basing_site')])
    expect(groups.map((g) => g.type)).toEqual(['component', 'basing_site'])
  })

  it('sorts an unmodelled type after the modelled supply chain but before the gap band', () => {
    expect(roleRank('manufacturer')).toBeLessThan(roleRank('mystery_type'))
    expect(roleRank('mystery_type')).toBeLessThan(roleRank('known_gap'))
  })
})
