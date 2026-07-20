// Graph legibility — the pure half of the Graph stage (Cytoscape does the drawing;
// everything about WHAT to draw and WHERE is decided here, so it is testable and
// deterministic).
//
// The problem this solves: a cold-boot live graph is 171 nodes / 105 edges, of which
// 113 nodes have no relationship at all and ~47% of the edges are entity-resolution
// bookkeeping. Dropped on one canvas that is an unreadable tangle plus rows of orphans.
//
// The fix is the repo's own headline architecture, made visible (spine/01 — the bi-level
// graph). Three layers, drawn as three layers instead of flattened into one:
//
//   KNOWLEDGE  the derived picture — domain entities joined by domain relationships.
//              This is the default canvas and the only layer on by default.
//   IDENTITY   resolution bookkeeping — `same-as` / `distinct-from`. Not knowledge about
//              the world, knowledge about our own records. An overlay the analyst turns on
//              when adjudicating identity, because then it is the most interesting thing
//              on screen and the rest of the time it is noise.
//   EVIDENCE   the append-only source layer. One-click-to-source already lives in the
//              provenance drawer; a `source` node on the canvas is the same fact drawn
//              twice, so it is off by default — but never deleted, only put behind a chip.
//
// Nothing is silently dropped. Whatever is not on the canvas is counted, named and
// reachable: an entity with no asserted relationship is a FINDING (a known entity we
// have learned nothing relational about), not a rendering artifact, so it gets an honest
// affordance rather than a quiet filter.
//
// Determinism (CLAUDE.md: the demo must render identically every run): positions are a
// pure function of the node/edge sets — no physics, no seeded randomness, no `cose`.
// Same graph in, same pixels out.

import type { GraphEdgeDef, GraphNodeDef } from '@/demo/scenario'

/** Resolution bookkeeping — identity, not domain knowledge. `supersedes` is deliberately
 *  NOT here: a "replaced by →" link is a real timeline fact about the world. */
export const IDENTITY_EDGE_TYPES = new Set(['same-as', 'distinct-from'])

/** The evidence layer's node type. Reached from any node's provenance drawer. */
export const EVIDENCE_NODE_TYPES = new Set(['source'])

/** Supply-chain / order-of-battle role order, left → right. This IS the analytic story
 *  C is built to tell (manufacturer → component → import → variant → unit → basing), so
 *  the x-axis carries meaning rather than being wherever a force layout happened to stop.
 *  Unknown types fall to the end, before the gap/evidence columns. */
export const ROLE_ORDER: string[] = [
  'manufacturer',
  'trading_org',
  'component',
  'contract_import_event',
  'variant',
  'unit',
  'basing_site',
  'known_gap',
  'source',
]

/** Column heading shown above each role band. */
export const ROLE_LABEL: Record<string, string> = {
  manufacturer: 'manufacturer',
  trading_org: 'trading org',
  component: 'component',
  contract_import_event: 'import event',
  variant: 'variant',
  unit: 'unit',
  basing_site: 'basing site',
  known_gap: 'known gap',
  source: 'source',
  unknown: 'unresolved type',
}

const OTHER_RANK = ROLE_ORDER.indexOf('known_gap') - 0.5 // unknown types sit just before gaps

export function roleRank(type: string | undefined): number {
  const i = ROLE_ORDER.indexOf(type ?? '')
  return i === -1 ? OTHER_RANK : i
}

// Geometry. A live node box is 152×`NODE_H`; the column pitch leaves ~46px of gutter for
// edges to run through and the row pitch ~16px between boxes.
//
// The x-axis is deliberately tight and the y-axis deliberately generous: seven role
// columns is what decides how far out a whole-graph fit has to zoom (and therefore how
// small the labels get), whereas column height is free — the stage is taller than the
// layout either way. So vertical room goes to letting long entity names wrap inside their
// box instead of spilling out of it.
export const COL_W = 198
export const ROW_H = 82
export const NODE_W = 152
export const NODE_H = 66

export interface GraphLayers {
  /** show `same-as` / `distinct-from` edges (and any node they alone connect) */
  identity: boolean
  /** show the `source` nodes of the evidence layer */
  evidence: boolean
}

export const DEFAULT_LAYERS: GraphLayers = { identity: false, evidence: false }

export interface GraphPlan {
  /** id → position for EVERY node, canvas or not (stable across layer toggles) */
  positions: Map<string, { x: number; y: number }>
  /** nodes drawn on the canvas: in the active layers AND holding at least one drawn edge */
  canvasNodes: Set<string>
  /** edges drawn on the canvas */
  canvasEdges: Set<string>
  /** in the active layers but holding no drawn edge — the honest-affordance list */
  unconnected: GraphNodeDef[]
  /** every role band: its x, and how many of its nodes are actually on the canvas. Bands
   *  with `count` 0 are parked off to the right and draw no heading. */
  columns: Array<{ type: string; x: number; count: number }>
  /** adjacency over the DRAWN edges — the substrate for ego-graph focus */
  adjacency: Map<string, Set<string>>
}

function nodeInLayers(node: GraphNodeDef, layers: GraphLayers): boolean {
  if (EVIDENCE_NODE_TYPES.has(node.type ?? '')) return layers.evidence
  return true
}

function edgeInLayers(edge: GraphEdgeDef, layers: GraphLayers): boolean {
  if (IDENTITY_EDGE_TYPES.has(edge.type ?? '')) return layers.identity
  return true
}

/**
 * Decide what the canvas shows and where each node sits.
 *
 * Layout: nodes are banded into columns by ontology role (left → right along the supply
 * chain), and within a column ordered by drawn-degree descending then id ascending — so
 * hubs sit at the top of their band and the order never depends on object iteration luck.
 * Positions are computed for every node, including ones currently off-canvas, so toggling
 * a layer on slides nodes in at a fixed place instead of re-shuffling the whole picture.
 */
export function planGraph(
  nodes: GraphNodeDef[],
  edges: GraphEdgeDef[],
  layers: GraphLayers = DEFAULT_LAYERS,
): GraphPlan {
  const byId = new Map(nodes.map((n) => [n.id, n]))
  const inLayer = new Map(nodes.map((n) => [n.id, nodeInLayers(n, layers)]))

  const drawnEdges = edges.filter(
    (e) =>
      edgeInLayers(e, layers) &&
      byId.has(e.source) &&
      byId.has(e.target) &&
      inLayer.get(e.source) === true &&
      inLayer.get(e.target) === true,
  )

  const adjacency = new Map<string, Set<string>>()
  const link = (a: string, b: string) => {
    const set = adjacency.get(a)
    if (set) set.add(b)
    else adjacency.set(a, new Set([b]))
  }
  for (const e of drawnEdges) {
    link(e.source, e.target)
    link(e.target, e.source)
  }

  const degree = (id: string) => adjacency.get(id)?.size ?? 0

  const canvasNodes = new Set<string>()
  const unconnected: GraphNodeDef[] = []
  for (const n of nodes) {
    if (inLayer.get(n.id) !== true) continue
    if (degree(n.id) > 0) canvasNodes.add(n.id)
    else unconnected.push(n)
  }

  // ── positions: role columns, hubs first within a column ──────────────────────────
  const bands = new Map<string, GraphNodeDef[]>()
  for (const n of nodes) {
    const key = ROLE_ORDER.includes(n.type ?? '') ? (n.type as string) : 'unknown'
    const band = bands.get(key)
    if (band) band.push(n)
    else bands.set(key, [n])
  }
  const orderedBands = [...bands.entries()].sort((a, b) => roleRank(a[0]) - roleRank(b[0]))

  // Only bands that actually put something on the canvas take a column slot — an empty
  // band must not open a gap in the middle of the supply chain. Empty bands are parked
  // to the right of the last real column; their nodes are hidden anyway, and a later
  // layer toggle re-plans from scratch and gives them a real slot then.
  const positions = new Map<string, { x: number; y: number }>()
  const columns: Array<{ type: string; x: number; count: number }> = []
  const drawnBands = orderedBands.filter(([, band]) => band.some((n) => canvasNodes.has(n.id)))
  let parked = drawnBands.length

  orderedBands.forEach(([type, band]) => {
    const drawn = band.filter((n) => canvasNodes.has(n.id))
    const rest = band.filter((n) => !canvasNodes.has(n.id))
    // canvas nodes first (hub-first), then the rest — so the drawn column is contiguous
    // and centred, and off-canvas nodes park below it without opening gaps.
    const ordered = [
      ...drawn.sort((a, b) => degree(b.id) - degree(a.id) || (a.id < b.id ? -1 : 1)),
      ...rest.sort((a, b) => (a.id < b.id ? -1 : 1)),
    ]
    const slot = drawn.length > 0 ? drawnBands.findIndex(([t]) => t === type) : parked++
    const x = slot * COL_W
    columns.push({ type, x, count: drawn.length })
    const span = Math.max(drawn.length, 1)
    ordered.forEach((n, i) => {
      positions.set(n.id, { x, y: (i - (span - 1) / 2) * ROW_H })
    })
  })

  return {
    positions,
    canvasNodes,
    canvasEdges: new Set(drawnEdges.map((e) => e.id)),
    unconnected,
    columns,
    adjacency,
  }
}

/** Every node within `hops` of `root` over the drawn edges, `root` included. `hops` 0 is
 *  the node alone — which is the honest answer for an entity with no relationships. */
export function egoNodes(adjacency: Map<string, Set<string>>, root: string, hops: number): Set<string> {
  const seen = new Set<string>([root])
  let frontier = [root]
  for (let h = 0; h < hops; h++) {
    const next: string[] = []
    for (const id of frontier) {
      for (const nb of adjacency.get(id) ?? []) {
        if (seen.has(nb)) continue
        seen.add(nb)
        next.push(nb)
      }
    }
    if (next.length === 0) break
    frontier = next
  }
  return seen
}

/** How many identity links there are to offer, so the chip can carry a real count. */
export function countIdentityEdges(edges: GraphEdgeDef[]): number {
  return edges.filter((e) => IDENTITY_EDGE_TYPES.has(e.type ?? '')).length
}

/** Group the unconnected list by ontology type for the tray, biggest group first. */
export function groupByType(nodes: GraphNodeDef[]): Array<{ type: string; nodes: GraphNodeDef[] }> {
  const groups = new Map<string, GraphNodeDef[]>()
  for (const n of nodes) {
    const t = n.type ?? 'unknown'
    const g = groups.get(t)
    if (g) g.push(n)
    else groups.set(t, [n])
  }
  return [...groups.entries()]
    .map(([type, ns]) => ({ type, nodes: ns.sort((a, b) => (a.id < b.id ? -1 : 1)) }))
    .sort((a, b) => b.nodes.length - a.nodes.length || roleRank(a.type) - roleRank(b.type))
}
