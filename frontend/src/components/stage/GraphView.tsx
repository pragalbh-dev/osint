// Graph view — Cytoscape, deterministic PRESET layout (mockup ensureGraph/syncGraph,
// lines 901-1031). The layout NEVER moves: positions are frozen in the scenario and
// re-used verbatim; only edges/statuses/labels change (layout:'preset', never 'cose').
// Node status is carried by BORDER + FILL, never hue; the chokepoint halo stays a
// DASHED ring (candidate only). userZooming/userPanning are disabled to match the
// mockup; we fit once on mount. Rewire is edges-only, ~200ms.

import { useEffect, useRef } from 'react'
import cytoscape from 'cytoscape'
import { GRAPH_NODES, GRAPH_EDGES } from '@/demo/scenario'
import type { GraphKind } from '@/demo/scenario'
import { useWorkbench, selMoved, selRahwaliConfirmed } from '@/store/workbench'
import { COLORS, HALO, fillFor } from '@/design/tokens'

// stale/gap label text — the mockup's lighter grey (#8a949c), between history and text-dim
const GREY_TEXT = '#8a949c'

function buildElements(): cytoscape.ElementDefinition[] {
  const nodes: cytoscape.ElementDefinition[] = GRAPH_NODES.map((n) => ({
    data: { id: n.id, label: n.label },
    position: { x: n.x, y: n.y },
  }))
  // non-interactive dashed halo behind the candidate chokepoint (ht233)
  const choke = GRAPH_NODES.find((n) => n.id === 'ht233')!
  nodes.push({
    data: { id: 'ht233_halo', label: '' },
    position: { x: choke.x, y: choke.y },
    classes: 'halo',
    selectable: false,
    grabbable: false,
  })
  const edges: cytoscape.ElementDefinition[] = GRAPH_EDGES.map((e) => ({
    data: { id: e.id, source: e.source, target: e.target, kind: e.kind },
  }))
  return nodes.concat(edges)
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
    { selector: '.e-history', style: { 'line-style': 'dashed', 'line-color': COLORS.history, opacity: 0.55 } },
    { selector: '.sel', style: { 'overlay-color': COLORS.accent, 'overlay-opacity': 0.16, 'overlay-padding': 7 } },
    { selector: '.faded', style: { opacity: 0.16 } },
    { selector: '.hidden', style: { display: 'none' } },
  ]
  return style as unknown as cytoscape.CytoscapeOptions['style']
}

function syncGraph(
  cy: cytoscape.Core,
  state: { selected: string | null; moved: boolean; confirmed: boolean },
) {
  const { selected: sel, moved, confirmed } = state

  const kind: Record<string, GraphKind> = Object.fromEntries(GRAPH_NODES.map((n) => [n.id, n.kind]))
  kind.rawalpindi = moved ? 'stale' : 'confirmed'
  kind.rahwali = confirmed ? 'confirmed' : 'probable'

  const label: Record<string, string> = {
    rawalpindi: 'Rawalpindi\n' + (moved ? 'superseded · 2021' : 'HQ-9B fire-unit'),
    rahwali: 'Rahwali\n' + (confirmed ? 'confirmed · 2025' : 'single pass · 2025'),
  }

  const selNode = sel ? cy.$id(sel) : null
  const neigh = selNode && selNode.nonempty() ? selNode.closedNeighborhood() : null

  cy.batch(() => {
    cy.nodes().forEach((n) => {
      const id = n.id()
      if (id === 'ht233_halo') {
        const cls = ['halo']
        if (neigh && !neigh.contains(cy.$id('ht233'))) cls.push('faded')
        n.classes(cls.join(' '))
        return
      }
      if (label[id]) n.data('label', label[id])
      const cls: string[] = [kind[id] || 'confirmed']
      if (neigh) {
        if (!neigh.contains(n)) cls.push('faded')
        else if (id === sel) cls.push('sel')
      }
      n.classes(cls.join(' '))
    })
    cy.edges().forEach((e) => {
      const cls = [String(e.data('kind'))]
      if (e.id() === 'e_moved' && !moved) cls.push('hidden')
      if (sel && e.source().id() !== sel && e.target().id() !== sel) cls.push('faded')
      e.classes(cls.join(' '))
    })
  })
}

export function GraphView() {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const cyRef = useRef<cytoscape.Core | null>(null)

  const selected = useWorkbench((s) => s.selected)
  const moved = useWorkbench(selMoved)
  const confirmed = useWorkbench(selRahwaliConfirmed)
  const select = useWorkbench((s) => s.select)

  // mount — build the graph once with the frozen preset
  useEffect(() => {
    if (!containerRef.current || cyRef.current) return
    const cy = cytoscape({
      container: containerRef.current,
      elements: buildElements(),
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
      if (id === 'ht233_halo') return
      select(id) // store routes rahwali → drawer
    })
    cy.on('tap', (evt) => {
      if (evt.target === cy) select(null)
    })

    // fit once — the layout is a preset and never moves after this
    setTimeout(() => {
      try {
        cy.fit(cy.nodes(), 44)
      } catch {
        /* container not sized yet — harmless */
      }
    }, 0)

    syncGraph(cy, {
      selected: useWorkbench.getState().selected,
      moved: selMoved(useWorkbench.getState()),
      confirmed: selRahwaliConfirmed(useWorkbench.getState()),
    })

    return () => {
      cy.destroy()
      cyRef.current = null
    }
  }, [select])

  // rewire (edges/statuses/labels only) when state changes — layout never moves
  useEffect(() => {
    const cy = cyRef.current
    if (!cy) return
    syncGraph(cy, { selected, moved, confirmed })
  }, [selected, moved, confirmed])

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
      </div>
    </div>
  )
}
