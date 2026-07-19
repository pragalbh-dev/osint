// The central stage (design doc 08 · mockup <main> lines 129-247). Holds the
// Map|Graph toggle, the mono date readout, the active view (Leaflet map or
// Cytoscape graph), and the scripted ingest-trace overlay. Selection lives in the
// store, so it persists across the Map/Graph toggle (both views read s.selected).
// Deterministic by construction: no props, reads the store + frozen scenario only.

import { useWorkbench } from '@/store/workbench'
import { INGEST_DOCS, INGEST_STEPS } from '@/demo/scenario'
import { MapView } from './MapView'
import { GraphView } from './GraphView'

export function Stage() {
  const stage = useWorkbench((s) => s.stage)
  const setStage = useWorkbench((s) => s.setStage)
  const trace = useWorkbench((s) => s.ingestTrace)

  const isMap = stage === 'map'

  return (
    <main className="relative flex-1 overflow-hidden bg-bg">
      {/* Map | Graph toggle — mockup 132-135 */}
      <div
        style={{
          position: 'absolute',
          top: 16,
          left: 16,
          display: 'inline-flex',
          background: 'var(--surface)',
          border: '1px solid var(--hairline)',
          borderRadius: 4,
          overflow: 'hidden',
          zIndex: 6,
        }}
      >
        <span
          onClick={() => setStage('map')}
          style={{
            padding: '6px 14px',
            fontSize: 12.5,
            cursor: 'pointer',
            background: isMap ? 'var(--surface-raised)' : 'transparent',
            color: isMap ? 'var(--text)' : 'var(--text-dim)',
          }}
        >
          Map
        </span>
        <span
          onClick={() => setStage('graph')}
          style={{
            padding: '6px 14px',
            fontSize: 12.5,
            cursor: 'pointer',
            borderLeft: '1px solid var(--hairline)',
            background: !isMap ? 'var(--surface-raised)' : 'transparent',
            color: !isMap ? 'var(--text)' : 'var(--text-dim)',
          }}
        >
          Graph
        </span>
      </div>

      {/* mono date readout — mockup 136 */}
      <div
        style={{
          position: 'absolute',
          top: 18,
          right: 18,
          font: '11px/1 ui-monospace, Menlo, monospace',
          color: 'var(--text-faint)',
          zIndex: 6,
        }}
      >
        18 Jul 2026 · 06:42
      </div>

      {/* the active view — one instance at a time; selection persists via the store */}
      {isMap ? <MapView /> : <GraphView />}

      {/* ingest trace — steps render as they resolve, no spinner (mockup 229-245) */}
      {trace && <IngestTrace docId={trace.doc} step={trace.step} />}
    </main>
  )
}

function IngestTrace({ docId, step }: { docId: string; step: number }) {
  const doc = INGEST_DOCS.find((d) => d.id === docId)
  if (!doc) return null
  const steps = INGEST_STEPS(doc.file, doc.claims)

  return (
    <div
      style={{
        position: 'absolute',
        top: 16,
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 8,
        background: 'var(--surface)',
        border: '1px solid var(--hairline-strong)',
        borderRadius: 4,
        padding: '12px 16px 13px',
        minWidth: 308,
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          marginBottom: 10,
          paddingBottom: 9,
          borderBottom: '1px solid var(--hairline)',
        }}
      >
        <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--accent-primary)' }} />
        <span style={{ fontSize: 11, color: 'var(--text)', fontFamily: 'var(--mono)' }}>{doc.file}</span>
        <span style={{ fontSize: 10, color: 'var(--text-faint)' }}>· {doc.kind}</span>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {steps.map((text, i) => {
          const done = i < step
          const active = i === step
          const mark = done ? '✓' : active ? '▸' : '·'
          const col = done ? 'var(--live)' : active ? 'var(--accent-primary)' : 'var(--text-faint)'
          return (
            <div
              key={i}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                fontSize: 11.5,
                fontFamily: 'var(--mono)',
                color: col,
              }}
            >
              <span style={{ width: 9, display: 'inline-block', textAlign: 'center' }}>{mark}</span>
              <span>{text}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
