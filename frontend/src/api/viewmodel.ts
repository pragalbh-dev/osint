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
import type { GraphNodeDef, GraphEdgeDef } from '@/demo/scenario'
import {
  viewToPins,
  viewToGraph,
  viewToTripwires,
  nameResolver,
  unplacedLocations,
  clusterAreaPins,
} from './adapters'
import type { LiveTripwire, StagePin, UnplacedLocation } from './adapters'

export function useStagePins(): StagePin[] {
  const mode = useWorkbench((s) => s.mode)
  const liveView = useWorkbench((s) => s.liveView)
  return useMemo(() => {
    if (mode !== 'live') return PINS
    // area pins that share one anchor are folded into a single counted marker (adapters)
    return liveView ? clusterAreaPins(viewToPins(liveView)) : PINS
  }, [mode, liveView])
}

/** Entities the graph knows are somewhere, and that we refuse to draw at a point.
 *  DEMO has none: its fixture pins are all hand-placed. LIVE reads them off /view, so
 *  "insufficient evidence to place" is on screen next to the map instead of being an
 *  absence the analyst has to notice for themselves. */
const NO_UNPLACED: UnplacedLocation[] = []

export function useUnplacedLocations(): UnplacedLocation[] {
  const mode = useWorkbench((s) => s.mode)
  const liveView = useWorkbench((s) => s.liveView)
  return useMemo(() => {
    if (mode !== 'live' || !liveView) return NO_UNPLACED
    return unplacedLocations(liveView)
  }, [mode, liveView])
}

/** `(id) => human name` over the live graph. In DEMO (or before the first /view lands) it is
 *  the identity function: the demo's own copy is hand-authored and carries no raw ids. Never
 *  invents a name — an id the graph does not know comes back unchanged. */
export function useDisplayName(): (id: string) => string {
  const mode = useWorkbench((s) => s.mode)
  const liveView = useWorkbench((s) => s.liveView)
  return useMemo(() => (mode === 'live' ? nameResolver(liveView) : (id: string) => id), [mode, liveView])
}

export function useStageGraph(): { nodes: GraphNodeDef[]; edges: GraphEdgeDef[] } {
  const mode = useWorkbench((s) => s.mode)
  const liveView = useWorkbench((s) => s.liveView)
  return useMemo(() => {
    if (mode !== 'live') return { nodes: GRAPH_NODES, edges: GRAPH_EDGES }
    return liveView ? viewToGraph(liveView) : { nodes: GRAPH_NODES, edges: GRAPH_EDGES }
  }, [mode, liveView])
}

/** The Watch panel's tripwire rows. `null` means "no live feed to read" — the caller
 *  falls back to the frozen demo tripwires. A live view that HAS been fetched and simply
 *  carries no alerts returns `[]`, which is the honest live state (nothing has fired) and
 *  must NOT be papered over with demo content — same golden rule as the stage surfaces. */
export function useTripwires(): LiveTripwire[] | null {
  const mode = useWorkbench((s) => s.mode)
  const liveView = useWorkbench((s) => s.liveView)
  return useMemo(() => {
    if (mode !== 'live' || !liveView) return null
    return viewToTripwires(liveView)
  }, [mode, liveView])
}
