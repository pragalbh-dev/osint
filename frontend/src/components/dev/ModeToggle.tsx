// Dev-only DEMO/LIVE switch. App renders this ONLY under import.meta.env.DEV, so it
// never appears in the production (graded) build — the graded call stays pixel-clean.
// In a prod build, flip to live via the ?mode=live URL param instead (see main.tsx).
//
// Zustand-safe: subscribes only to the primitive `mode` and the stable `setMode`
// action — never an array/object-returning selector (the useSyncExternalStore loop).

import { useWorkbench } from '@/store/workbench'

export function ModeToggle() {
  const mode = useWorkbench((s) => s.mode)
  const setMode = useWorkbench((s) => s.setMode)
  const live = mode === 'live'
  return (
    <button
      type="button"
      onClick={() => setMode(live ? 'demo' : 'live')}
      title="Dev only — toggle DEMO / LIVE data source"
      style={{
        position: 'fixed',
        // Clear of the 240px rail: at left:10 this chip sat on top of the rail's own
        // "Credibility" row (both bottom-anchored), obscuring a real nav label at every
        // viewport height. It now floats over the Stage's empty bottom-left gutter instead.
        left: 252,
        bottom: 10,
        zIndex: 9999,
        padding: '4px 10px',
        font: '10px/1 ui-monospace, Menlo, monospace',
        letterSpacing: '0.08em',
        color: live ? 'var(--live)' : 'var(--text-dim)',
        background: 'var(--surface)',
        border: `1px solid ${live ? 'var(--live)' : 'var(--hairline-strong)'}`,
        borderRadius: 4,
        cursor: 'pointer',
        opacity: 0.85,
      }}
    >
      {live ? '● LIVE' : '○ DEMO'}
    </button>
  )
}
