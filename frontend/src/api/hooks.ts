// TanStack Query hooks — the LIVE-mode data seam. DEMO mode (default) renders from
// the deterministic store + scenario and never calls these. When the app is switched
// to LIVE mode, useLiveSync() pulls the real rebuilt graph from GET /view (the one
// endpoint live today) into the store; the rest (ask/evidence/hitl/ingest) wire in as
// their routes land. Keeping this isolated means demo reproducibility is never at risk.

import { useQuery } from '@tanstack/react-query'
import { useEffect } from 'react'
import { api } from './client'
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
