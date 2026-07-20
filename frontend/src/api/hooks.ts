// TanStack Query hooks — the LIVE-mode data seam. DEMO mode (default) renders from
// the deterministic store + scenario and never calls these. When the app is switched
// to LIVE mode, useLiveSync() pulls the real rebuilt graph from GET /view (the one
// endpoint live today) into the store; the rest (ask/evidence/hitl/ingest) wire in as
// their routes land. Keeping this isolated means demo reproducibility is never at risk.

import { useQuery } from '@tanstack/react-query'
import { useEffect } from 'react'
import { api } from './client'
import type { ObservableDef, ObservablesConfig } from './types'
import { useWorkbench } from '@/store/workbench'

export function useHealth() {
  return useQuery({ queryKey: ['health'], queryFn: api.health, refetchInterval: 15_000 })
}

export function useGraphView(subject?: string, enabled = true) {
  return useQuery({
    queryKey: ['view', subject ?? null],
    queryFn: () => api.view(subject),
    enabled,
  })
}

/** LIVE provenance drawer — pull GET /evidence/{id} for the selected element. Only
 *  fetches when an id is given AND the drawer is open (so closing/deselecting is free).
 *  Never used in demo mode (the demo drawer renders its frozen fixture). */
export function useEvidence(id: string | null, enabled = true) {
  return useQuery({
    queryKey: ['evidence', id],
    queryFn: () => api.evidence(id as string),
    enabled: enabled && !!id,
  })
}

/** LIVE armed-observable catalogue — GET /config/observables from the live config store.
 *
 *  This is what a tripwire count should be counted from: `/view.alerts` says what has FIRED, and on a
 *  cold boot that is empty even though observables are armed and being evaluated on every rebuild.
 *  Returns `null` while unknown (demo mode, in flight, or the fetch failed) so callers can degrade to
 *  something honest rather than to a confident `0` — never claim a catalogue you could not read.
 *
 *  Refetches on an interval because the catalogue is HOT: an observable defined in-app takes effect
 *  without a restart, so a cached count would go stale against a live config store. */
export function useArmedObservables(): ObservableDef[] | null {
  const mode = useWorkbench((s) => s.mode)
  const { data } = useQuery({
    queryKey: ['config', 'observables'],
    queryFn: () => api.configSection('observables'),
    enabled: mode === 'live',
    refetchInterval: 30_000,
  })
  if (mode !== 'live' || !data) return null
  const list = (data.value as ObservablesConfig | undefined)?.observables
  return Array.isArray(list) ? list : null
}

/** In LIVE mode, mirror the real /view into the store so the stage can render it.
 *  A no-op in DEMO mode. Mount once (e.g. in App) if/when live mode is enabled. */
export function useLiveSync(subject?: string) {
  const mode = useWorkbench((s) => s.mode)
  const setLiveView = useWorkbench((s) => s.setLiveView)
  const { data } = useGraphView(subject, mode === 'live')
  useEffect(() => {
    if (mode === 'live' && data) setLiveView(data)
    if (mode !== 'live') setLiveView(null)
  }, [mode, data, setLiveView])
}
