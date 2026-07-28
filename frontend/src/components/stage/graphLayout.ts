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
 *  NOT here: a "replaced by →" link is a real timeline fact about the world.
 *
 *  Split in two, because a wall and a proposal are opposite statements and an analyst adjudicating
 *  identity wants one or the other, not both at once:
 *
 *  · SEPARATIONS  `distinct-from` + `coref-distinct-from` — "these are NOT the same thing".
 *  · PROPOSALS    `same-as` — "these MIGHT be the same thing", still un-adjudicated.
 *
 *  `coref-distinct-from` used to sit in neither set, so its fourteen instances rode the knowledge
 *  layer as teal relationship lines — a separation drawn as a connection, on the picture where the
 *  order-of-battle trap (two co-located positions fused into one unit's before-and-after) lives. */
export const SEPARATION_EDGE_TYPES = new Set(['distinct-from', 'coref-distinct-from'])
export const PROPOSAL_EDGE_TYPES = new Set(['same-as'])
export const IDENTITY_EDGE_TYPES = new Set([...SEPARATION_EDGE_TYPES, ...PROPOSAL_EDGE_TYPES])

/** The evidence layer's node type. Reached from any node's provenance drawer. */
export const EVIDENCE_NODE_TYPES = new Set(['source'])

/** Supply-chain / order-of-battle role order, left → right. This IS the analytic story
 *  C is built to tell (manufacturer → component → import → variant → unit → basing), so
 *  the x-axis carries meaning rather than being wherever a force layout happened to stop.
 *
 *  EVERY ontology type is listed. A type left off this list is not merely un-positioned — the banding
 *  below re-keys it to `unknown` and it is drawn under the heading "unresolved type", asserting that the
 *  system could not type something it typed perfectly well. Adding a node type to the ontology means
 *  adding it here. Genuinely untyped nodes fall to the end, before the gap/evidence columns. */
export const ROLE_ORDER: string[] = [
  'manufacturer',
  'trading_org',
  'component',
  'contract_import_event',
  'variant',
  'unit',
  'operator',
  'presence',
  'basing_site',
  'area_of_operations',
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
  operator: 'operator',
  presence: 'presence',
  area_of_operations: 'area of ops',
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
  /** show the SEPARATIONS — "these two records are NOT the same thing". On by default: a wall is
   *  the thing standing between the graph and the archetypal harm, and a wall the analyst never
   *  sees is a judgement that reached nobody. Safe to show now that it is drawn AS a wall. */
  separations: boolean
  /** show the un-adjudicated merge PROPOSALS (`same-as`). Off by default: a proposal is a question
   *  the review queue already asks, and 47 of them at once buries the walls. */
  proposals: boolean
  /** show the `source` nodes of the evidence layer */
  evidence: boolean
  /** show nodes the ontology could not TYPE. Off by default, and the count is on the chip either way.
   *
   *  These are not mistyped entities — they are imagery laydowns the extractor emitted as things
   *  ("Six elongated canister-type objects, HT-233-type engagement radar, command/communications
   *  shelter…", "six-object fan", "light vehicles"). A bag of objects seen in one frame is an
   *  observation, and the ontology has no type for it because it is not an entity. Drawn among real
   *  entities they read as peers of the units and radars around them, which is the one thing they are
   *  not; hidden with no trace they would be a silent omission. So: off, counted, one click away — the
   *  system says how many things it declined to type rather than either asserting or concealing them. */
  unresolved: boolean
}

/** The ontology's own label for "no type could be established" — never a UI-side synonym. */
export const UNRESOLVED_NODE_TYPE = 'unknown'

export const DEFAULT_LAYERS: GraphLayers = {
  separations: true,
  proposals: false,
  evidence: false,
  unresolved: false,
}

/** How many nodes the ontology could not type. Stated on the chip whether the layer is on or off. */
export function countUnresolved(nodes: GraphNodeDef[]): number {
  return nodes.filter((n) => (n.type ?? '') === UNRESOLVED_NODE_TYPE).length
}

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
  /** identity edges the active layers would show but that the WHOLE-GRAPH view holds back, because
   *  at least one endpoint has no relationship about the world and so is not on the canvas. They are
   *  still in `canvasEdges` and in `adjacency`, so focusing either endpoint draws them; the count is
   *  stated rather than quietly dropped, because a wall the picture cannot show is still a finding. */
  undrawableIdentity: number
}

function nodeInLayers(node: GraphNodeDef, layers: GraphLayers): boolean {
  if (EVIDENCE_NODE_TYPES.has(node.type ?? '')) return layers.evidence
  if ((node.type ?? '') === UNRESOLVED_NODE_TYPE) return layers.unresolved
  return true
}

export function isIdentityEdge(edge: GraphEdgeDef): boolean {
  return IDENTITY_EDGE_TYPES.has(edge.type ?? '')
}

function edgeInLayers(edge: GraphEdgeDef, layers: GraphLayers): boolean {
  if (SEPARATION_EDGE_TYPES.has(edge.type ?? '')) return layers.separations
  if (PROPOSAL_EDGE_TYPES.has(edge.type ?? '')) return layers.proposals
  return true
}

const asc = (x: string, y: string): number => (x < y ? -1 : x > y ? 1 : 0)

/** The deterministic display tie-break: by NAME, with the id only as a last resort.
 *
 *  It used to be the id alone. An id is an opaque handle the backend mints and may re-key
 *  (RK-NAMECUT), so ordering on it makes a node's place in its column move for a reason
 *  that is invisible on screen and means nothing about the graph — while what the analyst
 *  is scanning is the label. The id stays as the final tiebreak because it is unique, which
 *  is what makes the order total (and therefore the picture reproducible run to run). */
function byLabel(a: GraphNodeDef, b: GraphNodeDef): number {
  return asc(a.name ?? '', b.name ?? '') || asc(a.id, b.id)
}

/**
 * Decide what the canvas shows and where each node sits.
 *
 * Layout: nodes are banded into columns by ontology role (left → right along the supply
 * chain), and within a column ordered by drawn-degree descending then name ascending — so
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

  const eligible = edges.filter(
    (e) =>
      edgeInLayers(e, layers) &&
      byId.has(e.source) &&
      byId.has(e.target) &&
      inLayer.get(e.source) === true &&
      inLayer.get(e.target) === true,
  )

  // The canvas is decided by KNOWLEDGE alone. An identity edge is bookkeeping about our records,
  // so turning the layer on may not promote an entity out of the "no asserted relationship" tray:
  // that tray is a collection FINDING, and letting a wall quietly empty it would trade one honest
  // surface for another. Identity edges therefore draw only between entities the world already
  // connects, and whatever that leaves undrawable is counted and stated (never silently dropped).
  const knowledgeEdges = eligible.filter((e) => !isIdentityEdge(e))

  const knowledgeAdj = new Map<string, Set<string>>()
  const adjacency = new Map<string, Set<string>>()
  const linkInto = (map: Map<string, Set<string>>, a: string, b: string) => {
    const set = map.get(a)
    if (set) set.add(b)
    else map.set(a, new Set([b]))
  }
  for (const e of knowledgeEdges) {
    linkInto(knowledgeAdj, e.source, e.target)
    linkInto(knowledgeAdj, e.target, e.source)
  }

  const canvasNodes = new Set<string>()
  const unconnected: GraphNodeDef[] = []
  for (const n of nodes) {
    if (inLayer.get(n.id) !== true) continue
    if ((knowledgeAdj.get(n.id)?.size ?? 0) > 0) canvasNodes.add(n.id)
    else unconnected.push(n)
  }

  // Identity edges join the drawable set and the focus adjacency, but the WHOLE-GRAPH view only
  // renders the ones whose endpoints the world already connects — the caller hides an edge whose
  // endpoint is off-canvas. Focusing an entity pulls its identity partners in through this
  // adjacency, so every wall and every proposal stays one click from the analyst even when the
  // whole-graph picture would be a tangle with it drawn.
  const identityEligible = eligible.filter(isIdentityEdge)
  const undrawableIdentity = identityEligible.filter(
    (e) => !canvasNodes.has(e.source) || !canvasNodes.has(e.target),
  ).length

  const drawnEdges = [...knowledgeEdges, ...identityEligible]
  for (const e of drawnEdges) {
    linkInto(adjacency, e.source, e.target)
    linkInto(adjacency, e.target, e.source)
  }

  const degree = (id: string) => adjacency.get(id)?.size ?? 0

  // ── positions: role columns, hubs first within a column ──────────────────────────
  const bands = new Map<string, GraphNodeDef[]>()
  for (const n of nodes) {
    // A type with no declared column used to be re-keyed to 'unknown' and drawn under the heading
    // "unresolved type" — so `presence`, `area_of_operations` and `operator` (28 of the 39 nodes in
    // that column on the booted corpus) were rendered as things the ontology could not type, which
    // they emphatically are not. Every type the ontology declares now owns a column; the fallback
    // remains for a type nobody has banded yet, and it is the ONLY thing that heading now covers.
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
      ...drawn.sort((a, b) => degree(b.id) - degree(a.id) || byLabel(a, b)),
      ...rest.sort(byLabel),
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
    undrawableIdentity,
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

/** …and split, because the two chips ask opposite questions. */
export function countSeparations(edges: GraphEdgeDef[]): number {
  return edges.filter((e) => SEPARATION_EDGE_TYPES.has(e.type ?? '')).length
}

export function countProposals(edges: GraphEdgeDef[]): number {
  return edges.filter((e) => PROPOSAL_EDGE_TYPES.has(e.type ?? '')).length
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
    .map(([type, ns]) => ({ type, nodes: ns.sort(byLabel) }))
    .sort((a, b) => b.nodes.length - a.nodes.length || roleRank(a.type) - roleRank(b.type))
}
