// View-model hooks — the one seam every stage surface reads through, so components
// never know whether they're in DEMO or LIVE mode. In DEMO (default) they return the
// frozen scenario fixtures BY REFERENCE (so the graded demo is byte-identical and the
// mount effects run exactly once). In LIVE they return the adapted GET /view.
//
// Fallback rule (golden rule): fall back to the demo fixtures only when live data is
// genuinely ABSENT (liveView === null: not fetched yet, or errored) — NOT when it was
// fetched successfully but empty. An empty live graph is the honest live state (e.g. a
// backend booted with no evidence bundles) and must render as empty, not as fake demo data.
//
// Zustand-safe: subscribe to the primitive `mode` and the stable `liveView` reference
// (swapped atomically by setLiveView, never recomputed per call); derive the arrays with
// useMemo. Never return a fresh array from a store selector (the useSyncExternalStore loop).

import { useMemo } from 'react'
import { useWorkbench } from '@/store/workbench'
import { PINS, GRAPH_NODES, GRAPH_EDGES } from '@/demo/scenario'
import type { PinDef, GraphNodeDef, GraphEdgeDef } from '@/demo/scenario'
import { viewToPins, viewToGraph } from './adapters'

export function useStagePins(): PinDef[] {
  const mode = useWorkbench((s) => s.mode)
  const liveView = useWorkbench((s) => s.liveView)
  return useMemo(() => {
    if (mode !== 'live') return PINS
    return liveView ? viewToPins(liveView) : PINS
  }, [mode, liveView])
}

export function useStageGraph(): { nodes: GraphNodeDef[]; edges: GraphEdgeDef[] } {
  const mode = useWorkbench((s) => s.mode)
  const liveView = useWorkbench((s) => s.liveView)
  return useMemo(() => {
    if (mode !== 'live') return { nodes: GRAPH_NODES, edges: GRAPH_EDGES }
    return liveView ? viewToGraph(liveView) : { nodes: GRAPH_NODES, edges: GRAPH_EDGES }
  }, [mode, liveView])
}
