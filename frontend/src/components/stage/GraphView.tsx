// Graph view — Cytoscape.
//
// DEMO mode is UNCHANGED: a deterministic PRESET whose positions are frozen in the
// scenario and re-used verbatim; the layout NEVER moves — only edges/statuses/labels
// change. The graded hero thread renders byte-identically to before.
//
// LIVE mode is where the legibility work lives. A cold-boot live graph is ~171 nodes /
// ~105 edges, and dumping all of it on one canvas produced a hairball plus marching rows
// of orphans. The fix is to draw the repo's own bi-level architecture (spine/01) as three
// layers instead of flattening them:
//
//   · KNOWLEDGE (default)  domain entities joined by domain relationships.
//   · IDENTITY  (chip)     `same-as`/`distinct-from` — bookkeeping about our RECORDS, not
//                          about the world. On when adjudicating identity, off otherwise.
//   · EVIDENCE  (chip)     `source` nodes. One-click-to-source is the provenance drawer's
//                          job; a source node on the canvas is that fact drawn twice.
//
// Nothing is silently dropped — every entity not on the canvas is counted, named and
// clickable in the tray, because "known entity, no asserted relationship" is a FINDING.
//
// Layout is a pure function of the node/edge sets (see ./graphLayout): role columns along
// the supply chain, hubs first. No physics, no seeded randomness — same graph in, same
// pixels out, which is the determinism CLAUDE.md requires of the demo.
//
// Node status is carried by BORDER + FILL, never hue; the chokepoint halo stays a DASHED
// ring (candidate only). Zoom/pan stay disabled in DEMO (mockup framing) and are enabled in
// LIVE, where ~50 entities need navigating; we re-fit after every visibility change. Rewire
// is positions/visibility/statuses/labels only, and never runs a layout algorithm.

import { useEffect, useMemo, useRef, useState, type CSSProperties } from 'react'
import cytoscape from 'cytoscape'
import type { GraphKind, GraphNodeDef, GraphEdgeDef } from '@/demo/scenario'
import { useStageGraph } from '@/api/viewmodel'
import { useWorkbench, selMoved, selRahwaliConfirmed } from '@/store/workbench'
import { COLORS, HALO, fillFor } from '@/design/tokens'
import {
  DEFAULT_LAYERS,
  EVIDENCE_NODE_TYPES,
  NODE_H,
  NODE_W,
  ROLE_LABEL,
  ROW_H,
  countIdentityEdges,
  egoNodes,
  groupByType,
  planGraph,
  type GraphLayers,
  type GraphPlan,
} from './graphLayout'

// stale/gap label text — the mockup's lighter grey (#8a949c), between history and text-dim
const GREY_TEXT = '#8a949c'

const COL_HEAD_PREFIX = 'colhead::'

function buildElements(
  nodes: GraphNodeDef[],
  edges: GraphEdgeDef[],
  plan: GraphPlan | null,
): cytoscape.ElementDefinition[] {
  const at = (n: GraphNodeDef) => plan?.positions.get(n.id) ?? { x: n.x, y: n.y }

  const nodeEls: cytoscape.ElementDefinition[] = nodes.map((n) => ({
    // carry `kind`/`type`/`name` in node data so syncGraph reads it off the element (works
    // for demo presets AND live-adapted nodes, with no dependency on the scenario module).
    data: { id: n.id, label: n.label, kind: n.kind, etype: n.type ?? '', name: n.name ?? n.label },
    position: at(n),
    // in a role-column layout the type is already said by the column heading, so a live
    // node drops the "\ntype" second line and spends the box on the name instead.
    classes: plan ? 'named' : undefined,
  }))
  // non-interactive dashed halo behind EACH candidate-chokepoint node (demo: just ht233).
  const halos: cytoscape.ElementDefinition[] = nodes
    .filter((n) => n.kind === 'chokepoint')
    .map((n) => ({
      data: { id: `${n.id}_halo`, label: '' },
      position: at(n),
      classes: 'halo',
      selectable: false,
      grabbable: false,
    }))
  // one non-interactive heading per role column — the x-axis means something (supply-chain
  // role), so it gets said out loud rather than left for the analyst to infer.
  const heads: cytoscape.ElementDefinition[] = (plan?.columns ?? []).map((c) => ({
    data: { id: `${COL_HEAD_PREFIX}${c.type}`, label: (ROLE_LABEL[c.type] ?? c.type).toUpperCase() },
    position: { x: c.x, y: 0 },
    classes: 'colhead',
    selectable: false,
    grabbable: false,
  }))
  const edgeEls: cytoscape.ElementDefinition[] = edges.map((e) => ({
    data: { id: e.id, source: e.source, target: e.target, kind: e.kind, etype: e.type ?? '' },
  }))
  return [...nodeEls, ...halos, ...heads, ...edgeEls]
}

function cyStyle(): cytoscape.CytoscapeOptions['style'] {
  const fresh = fillFor('fresh')
  const staleFill = fillFor('stale', 'history')
  const problemFill = fillFor('fresh', 'problem') // === --fill-problem
  const style = [
    {
      selector: 'node',
      style: {
        width: 152,
        height: 46,
        shape: 'rectangle',
        'background-color': fresh,
        'background-opacity': 1,
        'border-width': 2,
        'border-color': COLORS.live,
        'border-style': 'solid',
        label: 'data(label)',
        'text-wrap': 'wrap',
        'text-max-width': 136,
        'text-valign': 'center',
        'text-halign': 'center',
        color: COLORS.text,
        'font-size': 10,
        'font-family': 'ui-monospace, Menlo, monospace, sans-serif',
        'line-height': 1.5,
        'z-index': 10,
      },
    },
    { selector: '.confirmed', style: { 'border-width': 2, 'border-style': 'solid', 'border-color': COLORS.live, 'background-color': fresh } },
    { selector: '.probable', style: { 'border-width': 1.5, 'border-style': 'dashed', 'border-color': COLORS.live, 'background-color': fresh } },
    { selector: '.chokepoint', style: { 'border-width': 1.5, 'border-style': 'dashed', 'border-color': COLORS.live, 'background-color': fresh } },
    { selector: '.stale', style: { 'border-width': 2, 'border-style': 'solid', 'border-color': COLORS.history, 'background-color': staleFill, color: GREY_TEXT } },
    { selector: '.gap', style: { 'border-width': 1.5, 'border-style': 'dashed', 'border-color': COLORS.history, 'background-opacity': 0, color: GREY_TEXT } },
    // CONTRADICTED — sources disagree. Loud and settled: solid 2px coral with a coral
    // fill (--border-contradicted / --fill-problem). It must NOT rhyme with `.gap`
    // (dashed grey, unfilled): a problem is not an absence. Text stays full-strength.
    { selector: '.contradicted', style: { 'border-width': 2, 'border-style': 'solid', 'border-color': COLORS.problem, 'background-color': problemFill, 'background-opacity': 1, color: COLORS.text } },
    // LIVE node — the role column above it already names the type, so the box carries the
    // entity's own name only. Shorter label, shallower box, more of them legible at once.
    { selector: '.named', style: { label: 'data(name)', width: NODE_W, height: NODE_H, 'font-size': 12, 'text-max-width': 138 } },
    { selector: '.halo', style: { width: 176, height: 70, shape: 'rectangle', 'background-opacity': 0, 'border-width': HALO.width, 'border-style': 'dashed', 'border-color': HALO.color, label: '', 'z-index': 0, events: 'no' } },
    // role-column heading — chrome, not an entity: no box, just dim mono text above the band.
    {
      selector: '.colhead',
      style: {
        width: 1,
        height: 1,
        'background-opacity': 0,
        'border-width': 0,
        label: 'data(label)',
        'text-valign': 'center',
        'text-halign': 'center',
        color: COLORS.textDim,
        'font-size': 12,
        'font-family': 'ui-monospace, Menlo, monospace',
        'text-max-width': 220,
        'z-index': 1,
        events: 'no',
      },
    },
    { selector: 'edge', style: { width: 1, 'curve-style': 'straight', 'line-color': COLORS.live, opacity: 0.7, 'target-arrow-shape': 'none' } },
    { selector: '.e-confirmed', style: { 'line-style': 'solid', 'line-color': COLORS.live } },
    { selector: '.e-probable', style: { 'line-style': 'dashed', 'line-color': COLORS.live } },
    // STALE vs GAP are different facts and must not look alike: stale is SOLID grey
    // (settled history — the assertion was overtaken, matching --border-stale on nodes);
    // a gap is DASHED grey (provisional/absent — we do not know), matching the Known-Gap
    // border. THE ONE RULE holds: dashed = provisional, solid = settled.
    { selector: '.e-stale', style: { 'line-style': 'solid', 'line-color': COLORS.history, opacity: 0.6 } },
    { selector: '.e-gap', style: { 'line-style': 'dashed', 'line-color': COLORS.history, opacity: 0.42 } },
    { selector: '.e-contradicted', style: { 'line-style': 'solid', 'line-color': COLORS.problem, opacity: 0.9 } },
    // `supersedes` — a status-LESS version link ("replaced by →"), given the arrow rather
    // than the contradiction treatment: it is a timeline relationship, not an alarm.
    {
      selector: '.e-supersede',
      style: {
        'line-style': 'solid',
        'line-color': COLORS.history,
        opacity: 0.75,
        'target-arrow-shape': 'triangle',
        'target-arrow-color': COLORS.history,
        'arrow-scale': 0.7,
      },
    },
    // CANDIDATE supersession — the analyst has not adjudicated it yet, so we are not sure
    // the two things are the same unit. Same arrow (still a version link, still not an
    // alarm), DASHED (provisional). THE ONE RULE makes "not sure" undrawable as certain.
    {
      selector: '.e-supersede-candidate',
      style: {
        'line-style': 'dashed',
        'line-color': COLORS.history,
        opacity: 0.75,
        'target-arrow-shape': 'triangle',
        'target-arrow-color': COLORS.history,
        'arrow-scale': 0.7,
      },
    },
    // other status-less edges (same-as / distinct-from) — identity, never truth
    { selector: '.e-link', style: { 'line-style': 'dotted', 'line-color': COLORS.history, opacity: 0.6 } },
    // in focus mode the edge type is spelled out: a two-hop trace is only auditable if the
    // analyst can read WHICH relationship each hop is, not just that a line exists.
    {
      selector: 'edge.labelled',
      style: {
        label: 'data(etype)',
        'font-size': 8.5,
        'font-family': 'ui-monospace, Menlo, monospace',
        color: COLORS.textDim,
        'text-background-color': COLORS.bg,
        'text-background-opacity': 0.85,
        'text-background-padding': '2px',
        'text-rotation': 'autorotate',
      },
    },
    { selector: '.sel', style: { 'overlay-color': COLORS.accent, 'overlay-opacity': 0.16, 'overlay-padding': 7 } },
    { selector: '.faded', style: { opacity: 0.16 } },
    { selector: '.hidden', style: { display: 'none' } },
  ]
  return style as unknown as cytoscape.CytoscapeOptions['style']
}

interface SyncState {
  selected: string | null
  moved: boolean
  confirmed: boolean
  mode: 'demo' | 'live'
  plan: GraphPlan | null
  hops: number
}

function syncGraph(cy: cytoscape.Core, state: SyncState) {
  const { selected: sel, moved, confirmed, mode, plan, hops } = state

  // DEMO-only status/label choreography, keyed to the hero-thread nodes. LIVE nodes carry
  // their status via data(kind) from the adapter and never get relabeled/re-kinded here.
  const kindOverride: Record<string, GraphKind> = {}
  const label: Record<string, string> = {}
  if (mode === 'demo') {
    kindOverride.rawalpindi = moved ? 'stale' : 'confirmed'
    kindOverride.rahwali = confirmed ? 'confirmed' : 'probable'
    label.rawalpindi = 'Rawalpindi\n' + (moved ? 'superseded · 2021' : 'HQ-9B fire-unit')
    label.rahwali = 'Rahwali\n' + (confirmed ? 'confirmed · 2025' : 'single pass · 2025')
  }

  // LIVE: focus is an EGO-GRAPH at a chosen hop depth over the drawn edges. Everything
  // outside it is hidden rather than dimmed — at ~50 nodes, dimming still leaves a tangle
  // to read past, and the point of focusing is to be able to read one chain.
  const focus =
    plan && sel && (plan.canvasNodes.has(sel) || plan.positions.has(sel))
      ? egoNodes(plan.adjacency, sel, hops)
      : null

  // DEMO keeps its original closed-neighbourhood fade (the hero choreography).
  const selNode = !plan && sel ? cy.$id(sel) : null
  const neigh = selNode && selNode.nonempty() ? selNode.closedNeighborhood() : null

  const onCanvas = (id: string): boolean => {
    if (!plan) return true
    if (!plan.canvasNodes.has(id)) return focus != null && focus.has(id) // a focused orphan
    return focus == null || focus.has(id)
  }

  cy.batch(() => {
    cy.nodes().forEach((n) => {
      const id = n.id()
      if (id.startsWith(COL_HEAD_PREFIX)) {
        const type = id.slice(COL_HEAD_PREFIX.length)
        const col = plan?.columns.find((c) => c.type === type)
        // a heading with nothing under it (layer off, or focus excluded the band) goes away
        const live =
          plan != null &&
          col != null &&
          col.count > 0 &&
          (focus == null ||
            [...focus].some((f) => plan.positions.get(f)?.x === col.x && plan.canvasNodes.has(f)))
        n.classes(live ? 'colhead' : 'colhead hidden')
        return
      }
      if (id.endsWith('_halo')) {
        const baseId = id.replace(/_halo$/, '')
        const cls = ['halo']
        if (!onCanvas(baseId)) cls.push('hidden')
        else if (neigh && !neigh.contains(cy.$id(baseId))) cls.push('faded')
        n.classes(cls.join(' '))
        return
      }
      if (label[id]) n.data('label', label[id])
      const baseKind = kindOverride[id] || (n.data('kind') as GraphKind) || 'confirmed'
      const cls: string[] = [baseKind]
      if (plan) cls.push('named') // live: the column heading already says the type
      if (!onCanvas(id)) cls.push('hidden')
      if (neigh) {
        if (!neigh.contains(n)) cls.push('faded')
        else if (id === sel) cls.push('sel')
      } else if (plan && id === sel) cls.push('sel')
      n.classes(cls.join(' '))
    })
    cy.edges().forEach((e) => {
      const cls = [String(e.data('kind'))]
      if (mode === 'demo' && e.id() === 'e_moved' && !moved) cls.push('hidden')
      if (plan) {
        const drawn =
          plan.canvasEdges.has(e.id()) && onCanvas(e.source().id()) && onCanvas(e.target().id())
        if (!drawn) cls.push('hidden')
        else if (focus) cls.push('labelled')
      }
      if (!plan && sel && e.source().id() !== sel && e.target().id() !== sel) cls.push('faded')
      e.classes(cls.join(' '))
    })
  })
}

export function GraphView() {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const cyRef = useRef<cytoscape.Core | null>(null)

  const mode = useWorkbench((s) => s.mode)
  const graph = useStageGraph()
  const selected = useWorkbench((s) => s.selected)
  const moved = useWorkbench(selMoved)
  const confirmed = useWorkbench(selRahwaliConfirmed)
  const select = useWorkbench((s) => s.select)
  const drawerOpen = useWorkbench((s) => s.drawerOpen)

  // The layering/focus machinery is for the LIVE graph. In demo — and in the live-before-
  // first-/view fallback, which serves the demo fixtures verbatim — the frozen preset is
  // already legible and its hand-placed positions must not be re-derived.
  const liveView = useWorkbench((s) => s.liveView)
  const isLive = mode === 'live' && liveView != null
  const [layers, setLayers] = useState<GraphLayers>(DEFAULT_LAYERS)
  const [hops, setHops] = useState(2)
  const [trayOpen, setTrayOpen] = useState(false)

  const plan = useMemo(
    () => (isLive ? planGraph(graph.nodes, graph.edges, layers) : null),
    [isLive, graph, layers],
  )
  // the element set is built ONCE per graph/mode; layer toggles only move + hide things,
  // so the initial plan is read through a ref and never re-triggers a rebuild.
  const planRef = useRef(plan)
  planRef.current = plan

  const identityCount = useMemo(() => countIdentityEdges(graph.edges), [graph])
  const evidenceCount = useMemo(
    () => graph.nodes.filter((n) => EVIDENCE_NODE_TYPES.has(n.type ?? '')).length,
    [graph],
  )
  const focused = isLive && selected != null && plan != null && plan.positions.has(selected)
  // …and it may be an entity with NO relationships (picked out of the tray). That is a
  // finding, so the readout says it rather than reporting "1 of 48".
  const focusIsolated = focused && selected != null && plan != null && !plan.canvasNodes.has(selected)
  const visibleCount = useMemo(() => {
    if (!plan) return 0
    if (!focused || selected == null) return plan.canvasNodes.size
    return egoNodes(plan.adjacency, selected, hops).size
  }, [plan, focused, selected, hops])

  // mount — build the graph. In demo the element set is a stable reference so this runs
  // once (preset never moves). In live it rebuilds when the adapted /view data changes.
  useEffect(() => {
    if (!containerRef.current || cyRef.current) return
    const cy = cytoscape({
      container: containerRef.current,
      elements: buildElements(graph.nodes, graph.edges, planRef.current),
      style: cyStyle(),
      layout: { name: 'preset' },
      // DEMO stays locked to the mockup's framing (9 nodes, no navigation to do). LIVE is a
      // real explorer over ~50 connected entities: a fixed fit that far out is unreadable
      // by construction, so the analyst gets zoom + pan. Nodes stay ungrabbable either way,
      // so the LAYOUT is still deterministic — only the viewport moves.
      userZoomingEnabled: isLive,
      userPanningEnabled: isLive,
      minZoom: 0.25,
      maxZoom: 2.5,
      boxSelectionEnabled: false,
      autoungrabify: true,
      autounselectify: true,
    })
    cyRef.current = cy
    // Dev-only handle. The graph is drawn to a <canvas>, so headless QA has no DOM to
    // assert against; this is the only way to check what is actually on screen. Stripped
    // from the production build, which is what the graded call runs.
    if (import.meta.env.DEV) (window as unknown as { __cy?: cytoscape.Core }).__cy = cy

    cy.on('tap', 'node', (evt) => {
      const id = evt.target.id()
      if (id.endsWith('_halo') || id.startsWith(COL_HEAD_PREFIX)) return
      select(id) // store routes rahwali → drawer
    })
    cy.on('tap', (evt) => {
      if (evt.target === cy) select(null)
    })

    syncGraph(cy, {
      selected: useWorkbench.getState().selected,
      moved: selMoved(useWorkbench.getState()),
      confirmed: selRahwaliConfirmed(useWorkbench.getState()),
      mode,
      plan: planRef.current,
      hops: 2,
    })
    setTimeout(() => fitVisible(cy), 0)

    return () => {
      cy.destroy()
      cyRef.current = null
    }
  }, [graph, mode, select, isLive])

  // rewire (positions/visibility/statuses/labels) — the layout is a pure function of the
  // node/edge sets, so a layer toggle repositions rather than re-runs anything physical.
  useEffect(() => {
    const cy = cyRef.current
    if (!cy) return
    if (plan) applyPositions(cy, plan)
    syncGraph(cy, { selected, moved, confirmed, mode, plan, hops })
    if (!plan) return
    // Re-frame on the NEXT frame, not inline: `display: none` is applied through the style
    // sheet, and fitting in the same tick measures the pre-change visible set — which
    // silently left focus mode framed for the whole graph.
    //
    // Frame into the uncovered half of the stage while the provenance drawer is open —
    // clicking a node opens it, so otherwise the ego-graph you just asked for lands
    // underneath the panel explaining it.
    const frame = requestAnimationFrame(() => fitVisible(cy, drawerOpen ? DRAWER_W : 0))
    return () => cancelAnimationFrame(frame)
  }, [graph, selected, moved, confirmed, mode, plan, hops, drawerOpen])

  const tray = plan ? groupByType(plan.unconnected) : []

  return (
    <div style={{ position: 'absolute', inset: 0, paddingTop: 52 }}>
      <div ref={containerRef} style={{ width: '100%', height: '100%' }} />

      {isLive && plan && (
        <>
          <LayerBar
            layers={layers}
            toggleIdentity={() => setLayers((l) => ({ ...l, identity: !l.identity }))}
            // sources carry claims, not relationships, so turning the evidence layer on
            // lands them in the tray rather than on the canvas — open it, or the chip
            // looks like it did nothing.
            toggleEvidence={() =>
              setLayers((l) => {
                const on = !l.evidence
                if (on) setTrayOpen(true)
                return { ...l, evidence: on }
              })
            }
            identityCount={identityCount}
            evidenceCount={evidenceCount}
            shown={visibleCount}
            total={plan.canvasNodes.size}
            focused={focused}
            focusLabel={focused && selected ? nameOf(graph.nodes, selected) : null}
            focusIsolated={focusIsolated}
            hops={hops}
            setHops={setHops}
            clearFocus={() => select(null)}
            refit={() => cyRef.current && fitVisible(cyRef.current, drawerOpen ? DRAWER_W : 0)}
          />
          <UnconnectedTray
            groups={tray}
            open={trayOpen}
            toggle={() => setTrayOpen((o) => !o)}
            // picking one closes the tray: the analyst has chosen an entity, and the panel
            // sits over exactly the canvas that entity is about to be drawn on.
            onPick={(id) => {
              setTrayOpen(false)
              select(id)
            }}
            evidenceOn={layers.evidence}
          />
        </>
      )}

      <Legend mode={mode} live={isLive} identityOn={layers.identity} />
    </div>
  )
}

/** Width of the provenance drawer, which OVERLAYS the stage rather than pushing it (App.tsx).
 *  Selecting a node opens it, so a plain fit would centre the ego-graph underneath it. */
const DRAWER_W = 560

/** Nudge the view to whatever is currently drawn. Never throws on an unsized container.
 *  With no inset this is the mockup's `fit(…, 44)` verbatim, so DEMO framing is unchanged;
 *  with an inset it frames the content in the part of the stage the drawer is not covering. */
function fitVisible(cy: cytoscape.Core, rightInset = 0) {
  try {
    const vis = cy.nodes().filter((n) => n.visible())
    const eles = vis.nonempty() ? vis : cy.nodes()
    if (rightInset <= 0) {
      cy.fit(eles, 44)
      return
    }
    // Only honour the inset while it still leaves a workable canvas. The drawer is a fixed
    // 560px, so on a laptop-width stage insetting it would squeeze the graph into ~45% of
    // the width — being partly covered and readable beats being fully visible and tiny.
    const usable = cy.width() - rightInset
    if (usable < 620 || usable < cy.width() * 0.55) {
      cy.fit(eles, 44)
      return
    }
    const pad = 44
    const bb = eles.boundingBox()
    if (bb.w <= 0 || bb.h <= 0) return
    const w = usable
    const h = cy.height()
    const z = Math.max(
      cy.minZoom(),
      Math.min(cy.maxZoom(), Math.min((w - 2 * pad) / bb.w, (h - 2 * pad) / bb.h)),
    )
    cy.zoom(z)
    cy.pan({ x: w / 2 - z * (bb.x1 + bb.w / 2), y: h / 2 - z * (bb.y1 + bb.h / 2) })
  } catch {
    /* container not sized yet — harmless */
  }
}

function applyPositions(cy: cytoscape.Core, plan: GraphPlan) {
  cy.batch(() => {
    cy.nodes().forEach((n) => {
      const id = n.id()
      if (id.startsWith(COL_HEAD_PREFIX)) {
        const type = id.slice(COL_HEAD_PREFIX.length)
        const col = plan.columns.find((c) => c.type === type)
        // sit the heading one row above the tallest drawn node in its band
        if (col) n.position({ x: col.x, y: -((Math.max(col.count, 1) - 1) / 2) * ROW_H - NODE_H / 2 - 18 })
        return
      }
      const base = id.endsWith('_halo') ? id.replace(/_halo$/, '') : id
      const p = plan.positions.get(base)
      if (p) n.position(p)
    })
  })
}

function nameOf(nodes: GraphNodeDef[], id: string): string {
  const n = nodes.find((x) => x.id === id)
  return n?.name ?? n?.label.split('\n')[0] ?? id
}

// ─────────────────────────────── chrome ───────────────────────────────

const CHIP: CSSProperties = {
  padding: '4px 9px',
  font: '10.5px/1.3 ui-monospace, Menlo, monospace',
  // long-hand, not the `border` shorthand: several call sites override borderColor /
  // borderStyle alone, and React warns (rightly) when the two forms are mixed.
  borderWidth: 1,
  borderStyle: 'solid',
  borderColor: 'var(--hairline-strong)',
  borderRadius: 3,
  background: 'var(--surface)',
  color: 'var(--text-dim)',
  cursor: 'pointer',
  whiteSpace: 'nowrap',
}

function chipStyle(on: boolean): CSSProperties {
  return on
    ? { ...CHIP, color: 'var(--text)', borderColor: 'var(--live)', background: 'var(--surface-raised)' }
    : CHIP
}

interface LayerBarProps {
  layers: GraphLayers
  toggleIdentity: () => void
  toggleEvidence: () => void
  identityCount: number
  evidenceCount: number
  shown: number
  total: number
  focused: boolean
  focusLabel: string | null
  focusIsolated: boolean
  hops: number
  setHops: (h: number) => void
  clearFocus: () => void
  refit: () => void
}

function LayerBar(p: LayerBarProps) {
  return (
    <div
      style={{
        position: 'absolute',
        top: 60,
        left: 16,
        zIndex: 5,
        display: 'flex',
        flexDirection: 'column',
        gap: 7,
        alignItems: 'flex-start',
      }}
    >
      <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
        <span style={{ font: '10px/1 ui-monospace,Menlo,monospace', color: 'var(--text-faint)', letterSpacing: '0.08em' }}>
          LAYERS
        </span>
        <span style={{ ...CHIP, cursor: 'default', color: 'var(--text)', borderColor: 'var(--live)' }}>
          knowledge · {p.total}
        </span>
        <button
          type="button"
          style={chipStyle(p.layers.identity)}
          title="same-as / distinct-from — bookkeeping about our records, not about the world"
          onClick={p.toggleIdentity}
        >
          identity links · {p.identityCount}
        </button>
        <button
          type="button"
          style={chipStyle(p.layers.evidence)}
          title="the append-only evidence layer — normally reached through a node's provenance drawer"
          onClick={p.toggleEvidence}
        >
          sources · {p.evidenceCount}
        </button>
        <button type="button" style={CHIP} title="scroll to zoom · drag to pan" onClick={p.refit}>
          fit
        </button>
      </div>

      {p.focused && (
        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          <span style={{ font: '10px/1 ui-monospace,Menlo,monospace', color: 'var(--text-faint)', letterSpacing: '0.08em' }}>
            FOCUS
          </span>
          <span style={{ ...CHIP, cursor: 'default', color: 'var(--text)', borderColor: 'var(--accent-primary)' }}>
            {p.focusLabel}
          </span>
          {[1, 2, 3].map((h) => (
            <button key={h} type="button" style={chipStyle(p.hops === h)} onClick={() => p.setHops(h)}>
              {h} hop{h === 1 ? '' : 's'}
            </button>
          ))}
          <button type="button" style={CHIP} onClick={p.clearFocus}>
            show all ×
          </button>
        </div>
      )}

      <div style={{ font: '10px/1.4 ui-monospace,Menlo,monospace', color: 'var(--text-faint)' }}>
        {!p.focused
          ? `${p.total} connected entities`
          : p.focusIsolated
            ? 'no relationship has been asserted about this entity — its provenance is still one click away'
            : `${p.shown} of ${p.total} connected entities shown`}
      </div>
    </div>
  )
}

interface TrayProps {
  groups: Array<{ type: string; nodes: GraphNodeDef[] }>
  open: boolean
  toggle: () => void
  onPick: (id: string) => void
  evidenceOn: boolean
}

/** The honest affordance for entities with no asserted relationship. They are NOT quietly
 *  filtered: they are counted, named, grouped by type and one click from their provenance.
 *  An entity we know exists but have learned nothing relational about is a collection gap
 *  — a finding the analyst should be able to see and act on, not a rendering artifact. */
function UnconnectedTray(p: TrayProps) {
  const total = p.groups.reduce((n, g) => n + g.nodes.length, 0)
  if (total === 0) return null
  return (
    <div
      style={{
        position: 'absolute',
        bottom: 44, // clear of the dev-only DEMO/LIVE chip parked in the stage's bottom gutter
        left: 16,
        zIndex: 5,
        maxWidth: 620,
        background: 'var(--surface)',
        border: '1px solid var(--hairline-strong)',
        borderRadius: 4,
      }}
    >
      <button
        type="button"
        onClick={p.toggle}
        style={{
          all: 'unset',
          display: 'block',
          cursor: 'pointer',
          padding: '7px 11px',
          font: '10.5px/1.4 ui-monospace, Menlo, monospace',
          color: 'var(--text-dim)',
        }}
      >
        {p.open ? '▾' : '▸'} {total} {total === 1 ? 'entity has' : 'entities have'} no asserted
        relationship — {p.open ? 'hide' : 'show'}
      </button>
      {p.open && (
        <div style={{ padding: '0 11px 10px', maxHeight: 300, overflowY: 'auto' }}>
          <div style={{ font: '10px/1.5 ui-monospace,Menlo,monospace', color: 'var(--text-faint)', marginBottom: 8 }}>
            Known to the graph, but no relationship has been asserted about them yet — a collection
            gap, not a rendering one. Click any to open its provenance.
            {p.evidenceOn && ' Source records carry claims, not relationships, so they are all listed here.'}
          </div>
          {p.groups.map((g) => (
            <div key={g.type} style={{ marginBottom: 8 }}>
              <div
                style={{
                  font: '9px/1 ui-monospace,Menlo,monospace',
                  color: 'var(--text-faint)',
                  letterSpacing: '0.08em',
                  marginBottom: 5,
                }}
              >
                {(ROLE_LABEL[g.type] ?? g.type).toUpperCase()} · {g.nodes.length}
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>
                {g.nodes.map((n) => (
                  <button
                    key={n.id}
                    type="button"
                    onClick={() => p.onPick(n.id)}
                    style={{
                      ...CHIP,
                      padding: '3px 7px',
                      fontSize: 10,
                      maxWidth: 200,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      borderStyle: g.type === 'known_gap' ? 'dashed' : 'solid',
                      borderColor: g.type === 'known_gap' ? 'var(--history)' : 'var(--hairline-strong)',
                    }}
                    title={n.id}
                  >
                    {n.name ?? n.label.split('\n')[0]}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function Legend({ mode, live, identityOn }: { mode: 'demo' | 'live'; live: boolean; identityOn: boolean }) {
  // DEMO keeps the mockup's legend verbatim (its stale node really does carry a stale
  // fill). LIVE drops "fill = freshness": the live adapter has no freshness band, so every
  // live fill is the fresh one — claiming otherwise would teach a distinction the screen
  // isn't drawing.
  const lines = live
    ? [
        'columns = supply-chain role',
        'border: solid = confirmed · dashed = probable',
        'dashed ring = candidate chokepoint',
        'grey arrow = replaced by',
        ...(identityOn ? ['dotted grey = identity link (same-as / distinct-from)'] : []),
        'click a node = focus its ego-graph + open provenance',
      ]
    : ['border = status · fill = freshness · dashed ring = candidate chokepoint']
  return (
    <div
      style={{
        position: 'absolute',
        bottom: 14,
        right: 18,
        font: '10.5px/1.4 ui-monospace,Menlo,monospace',
        color: 'var(--text-faint)',
        textAlign: 'right',
        zIndex: 4,
        pointerEvents: 'none',
      }}
      data-mode={mode}
    >
      {lines.map((l) => (
        <div key={l}>{l}</div>
      ))}
    </div>
  )
}
