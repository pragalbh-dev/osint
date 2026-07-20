// Graph view — Cytoscape. In DEMO mode the layout is a deterministic PRESET (positions
// frozen in the scenario, re-used verbatim; the layout NEVER moves — only edges/statuses/
// labels change) exactly as the mockup (ensureGraph/syncGraph, lines 901-1031). In LIVE
// mode the adapter gives no positions, so we run a force layout ('cose') once and align
// each candidate-chokepoint halo behind its node afterwards. Node status is carried by
// BORDER + FILL, never hue; the chokepoint halo stays a DASHED ring (candidate only).
// userZooming/userPanning are disabled to match the mockup; we fit once after layout.
// Rewire (syncGraph) is edges/statuses/labels only, ~200ms, and never re-lays-out.

import { useEffect, useRef } from 'react'
import cytoscape from 'cytoscape'
import type { GraphKind, GraphNodeDef, GraphEdgeDef } from '@/demo/scenario'
import { useStageGraph } from '@/api/viewmodel'
import { useWorkbench, selMoved, selRahwaliConfirmed } from '@/store/workbench'
import { COLORS, HALO, fillFor } from '@/design/tokens'

// stale/gap label text — the mockup's lighter grey (#8a949c), between history and text-dim
const GREY_TEXT = '#8a949c'

function buildElements(nodes: GraphNodeDef[], edges: GraphEdgeDef[]): cytoscape.ElementDefinition[] {
  const nodeEls: cytoscape.ElementDefinition[] = nodes.map((n) => ({
    // carry `kind` in node data so syncGraph reads it off the element (works for demo
    // presets AND live-adapted nodes, with no dependency on the scenario module).
    data: { id: n.id, label: n.label, kind: n.kind },
    position: { x: n.x, y: n.y },
  }))
  // non-interactive dashed halo behind EACH candidate-chokepoint node (demo: just ht233).
  const halos: cytoscape.ElementDefinition[] = nodes
    .filter((n) => n.kind === 'chokepoint')
    .map((n) => ({
      data: { id: `${n.id}_halo`, label: '' },
      position: { x: n.x, y: n.y },
      classes: 'halo',
      selectable: false,
      grabbable: false,
    }))
  const edgeEls: cytoscape.ElementDefinition[] = edges.map((e) => ({
    data: { id: e.id, source: e.source, target: e.target, kind: e.kind },
  }))
  return [...nodeEls, ...halos, ...edgeEls]
}

function cyStyle(): cytoscape.CytoscapeOptions['style'] {
  const fresh = fillFor('fresh')
  const staleFill = fillFor('stale', 'history')
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
    { selector: '.halo', style: { width: 176, height: 70, shape: 'rectangle', 'background-opacity': 0, 'border-width': HALO.width, 'border-style': 'dashed', 'border-color': HALO.color, label: '', 'z-index': 0, events: 'no' } },
    { selector: 'edge', style: { width: 1, 'curve-style': 'straight', 'line-color': COLORS.live, opacity: 0.7, 'target-arrow-shape': 'none' } },
    { selector: '.e-confirmed', style: { 'line-style': 'solid', 'line-color': COLORS.live } },
    { selector: '.e-probable', style: { 'line-style': 'dashed', 'line-color': COLORS.live } },
    // demo-only legacy kind (the frozen fixtures' history edges) — live never emits it
    { selector: '.e-history', style: { 'line-style': 'dashed', 'line-color': COLORS.history, opacity: 0.55 } },
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
    // other status-less edges (same-as / distinct-from) — identity, never truth
    { selector: '.e-link', style: { 'line-style': 'dotted', 'line-color': COLORS.history, opacity: 0.6 } },
    { selector: '.sel', style: { 'overlay-color': COLORS.accent, 'overlay-opacity': 0.16, 'overlay-padding': 7 } },
    { selector: '.faded', style: { opacity: 0.16 } },
    { selector: '.hidden', style: { display: 'none' } },
  ]
  return style as unknown as cytoscape.CytoscapeOptions['style']
}

function syncGraph(
  cy: cytoscape.Core,
  state: { selected: string | null; moved: boolean; confirmed: boolean; mode: 'demo' | 'live' },
) {
  const { selected: sel, moved, confirmed, mode } = state

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

  const selNode = sel ? cy.$id(sel) : null
  const neigh = selNode && selNode.nonempty() ? selNode.closedNeighborhood() : null

  cy.batch(() => {
    cy.nodes().forEach((n) => {
      const id = n.id()
      if (id.endsWith('_halo')) {
        const cls = ['halo']
        const baseId = id.replace(/_halo$/, '')
        if (neigh && !neigh.contains(cy.$id(baseId))) cls.push('faded')
        n.classes(cls.join(' '))
        return
      }
      if (label[id]) n.data('label', label[id])
      const baseKind = kindOverride[id] || (n.data('kind') as GraphKind) || 'confirmed'
      const cls: string[] = [baseKind]
      if (neigh) {
        if (!neigh.contains(n)) cls.push('faded')
        else if (id === sel) cls.push('sel')
      }
      n.classes(cls.join(' '))
    })
    cy.edges().forEach((e) => {
      const cls = [String(e.data('kind'))]
      if (mode === 'demo' && e.id() === 'e_moved' && !moved) cls.push('hidden')
      if (sel && e.source().id() !== sel && e.target().id() !== sel) cls.push('faded')
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

  // mount — build the graph. In demo the element set is a stable reference so this runs
  // once (preset never moves). In live it rebuilds when the adapted /view data changes.
  useEffect(() => {
    if (!containerRef.current || cyRef.current) return
    const cy = cytoscape({
      container: containerRef.current,
      elements: buildElements(graph.nodes, graph.edges),
      style: cyStyle(),
      layout: { name: 'preset' },
      userZoomingEnabled: false,
      userPanningEnabled: false,
      boxSelectionEnabled: false,
      autoungrabify: true,
      autounselectify: true,
    })
    cyRef.current = cy

    cy.on('tap', 'node', (evt) => {
      const id = evt.target.id()
      if (id.endsWith('_halo')) return
      select(id) // store routes rahwali → drawer
    })
    cy.on('tap', (evt) => {
      if (evt.target === cy) select(null)
    })

    const fit = () => {
      try {
        cy.fit(cy.nodes(), 44)
      } catch {
        /* container not sized yet — harmless */
      }
    }

    if (mode === 'demo') {
      // preset layout — positions are already set; just fit once and never move.
      setTimeout(fit, 0)
    } else {
      // LIVE — no positions from the adapter; run a force layout, then park each halo
      // behind its chokepoint node (halos aren't edge-linked, so cose scatters them).
      const l = cy.layout({ name: 'cose', animate: false, padding: 44 })
      l.one('layoutstop', () => {
        cy.nodes('.halo').forEach((h) => {
          const base = cy.$id(h.id().replace(/_halo$/, ''))
          if (base.nonempty()) h.position(base.position())
        })
        fit()
      })
      l.run()
    }

    syncGraph(cy, {
      selected: useWorkbench.getState().selected,
      moved: selMoved(useWorkbench.getState()),
      confirmed: selRahwaliConfirmed(useWorkbench.getState()),
      mode,
    })

    return () => {
      cy.destroy()
      cyRef.current = null
    }
  }, [graph, mode, select])

  // rewire (edges/statuses/labels only) when state changes — layout never moves
  useEffect(() => {
    const cy = cyRef.current
    if (!cy) return
    syncGraph(cy, { selected, moved, confirmed, mode })
  }, [graph, selected, moved, confirmed, mode])

  return (
    <div style={{ position: 'absolute', inset: 0, paddingTop: 52 }}>
      <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
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
      >
        border = status · fill = freshness · dashed ring = candidate chokepoint
        {mode === 'live' && <> · grey arrow = replaced by</>}
      </div>
    </div>
  )
}
