import { describe, expect, it } from 'vitest'
import type { GraphEdgeDef, GraphNodeDef } from '@/demo/scenario'
import {
  COL_W,
  DEFAULT_LAYERS,
  countIdentityEdges,
  egoNodes,
  groupByType,
  planGraph,
  roleRank,
} from './graphLayout'

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
const E = (id: string, source: string, target: string, type: string): GraphEdgeDef => ({
  id,
  source,
  target,
  kind: type === 'same-as' || type === 'distinct-from' ? 'e-link' : 'e-confirmed',
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
]

describe('planGraph — default (knowledge layer only)', () => {
  const plan = planGraph(NODES, EDGES, DEFAULT_LAYERS)

  it('draws only domain relationships — resolution bookkeeping is off by default', () => {
    expect(plan.canvasEdges.has('sa1')).toBe(false)
    expect(plan.canvasEdges.has('df1')).toBe(false)
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

describe('planGraph — identity overlay', () => {
  const plan = planGraph(NODES, EDGES, { identity: true, evidence: false })

  it('draws the bookkeeping edges when the analyst asks for them', () => {
    expect(plan.canvasEdges.has('sa1')).toBe(true)
    expect(plan.canvasEdges.has('df1')).toBe(true)
  })

  it('pulls in entities that only an identity link connects', () => {
    expect(plan.canvasNodes.has('alias_ft2000')).toBe(true)
    expect(plan.canvasNodes.has('orphan_a')).toBe(true)
    expect(plan.unconnected.map((n) => n.id).sort()).toEqual(['gap_tel', 'orphan_b'])
  })
})

describe('planGraph — evidence layer', () => {
  it('admits source records, which then show up as unconnected (they carry claims, not edges)', () => {
    const plan = planGraph(NODES, EDGES, { identity: false, evidence: true })
    expect(plan.unconnected.map((n) => n.id)).toContain('src_d05')
    expect(plan.canvasNodes.has('src_d05')).toBe(false)
  })
})

describe('planGraph — layout', () => {
  const plan = planGraph(NODES, EDGES, DEFAULT_LAYERS)

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
    const a = planGraph(NODES, EDGES, DEFAULT_LAYERS)
    const b = planGraph([...NODES].reverse(), [...EDGES].reverse(), DEFAULT_LAYERS)
    for (const id of a.canvasNodes) expect(b.positions.get(id)).toEqual(a.positions.get(id))
  })

  it('draws no heading for a band with nothing on the canvas', () => {
    expect(plan.columns.find((c) => c.type === 'source')?.count).toBe(0)
    expect(plan.columns.find((c) => c.type === 'unit')?.count).toBe(1)
  })
})

describe('egoNodes', () => {
  const plan = planGraph(NODES, EDGES, DEFAULT_LAYERS)

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
  it('counts the identity links the chip offers', () => {
    expect(countIdentityEdges(EDGES)).toBe(2)
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
