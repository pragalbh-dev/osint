// The rail — subject (static lens), review queue (expands inline), watching,
// the ingest drop surface, and a quiet credibility link. Self-contained: reads the
// global store + demo scenario, takes no props. Faithful port of the handoff
// mockup's <aside> (design docs 08-layout §"eight surfaces → four zones",
// 10-review-card §"the queue list lives in the rail").
import { useMemo, useRef } from 'react'
import clsx from 'clsx'
import { useWorkbench, type DocId } from '@/store/workbench'
import { INGEST_DOCS, QUEUE_ITEMS } from '@/demo/scenario'
import { viewToReviewQueue } from '@/api/adapters'
import { LiveIngest } from './LiveIngest'

export function Rail() {
  const mode = useWorkbench((s) => s.mode)
  const reviewOpen = useWorkbench((s) => s.reviewOpen)
  const toggleReview = useWorkbench((s) => s.toggleReview)
  const openCard = useWorkbench((s) => s.openCard)
  const openLiveCard = useWorkbench((s) => s.openLiveCard)
  const openWatch = useWorkbench((s) => s.openWatch)
  const openCred = useWorkbench((s) => s.openCred)
  const ingested = useWorkbench((s) => s.ingested)
  const ingestTrace = useWorkbench((s) => s.ingestTrace)
  const startIngest = useWorkbench((s) => s.startIngest)
  const resetIngest = useWorkbench((s) => s.resetIngest)
  // Subscribe to STABLE references only (`decided`, `liveView`, `liveDecided`) and derive
  // arrays with useMemo — never via an array-returning store selector, which returns a
  // fresh array each call and loops under useSyncExternalStore (React #185).
  const decided = useWorkbench((s) => s.decided)
  const liveView = useWorkbench((s) => s.liveView)
  const liveDecided = useWorkbench((s) => s.liveDecided)

  // One rendering shape for both modes; demo output stays byte-identical.
  const rows = useMemo(() => {
    if (mode === 'live') {
      const queue = liveView ? viewToReviewQueue(liveView) : []
      return queue
        .filter((i) => !liveDecided[i.itemId])
        .map((i) => ({ key: i.itemId, kicker: i.kicker, badge: i.badge, title: i.title, onClick: () => openLiveCard(i) }))
    }
    return QUEUE_ITEMS.filter((i) => !decided[i.id]).map((i) => ({
      key: i.id,
      kicker: i.type,
      badge: i.badge,
      title: i.subject,
      onClick: () => openCard(i.id),
    }))
  }, [mode, liveView, liveDecided, decided, openCard, openLiveCard])
  const reviewCount = rows.length

  // Drag payload backup — some browsers restrict dataTransfer.getData on dragover,
  // and this mirrors the mockup's own fallback (this._dragDoc) for the drop handler.
  const dragDocRef = useRef<DocId | null>(null)
  const ingestBusy = !!ingestTrace

  return (
    <aside className="flex w-[240px] flex-none flex-col border-r border-hairline bg-surface">
      {/* Subject — a query-time lens; the selector is decorative for this demo. */}
      <div className="border-b border-hairline px-[18px] pb-4 pt-[18px]">
        <div className="mb-[9px] text-[10.5px] tracking-[0.06em] text-text-faint">Subject</div>
        <div className="flex cursor-default items-center justify-between gap-2 rounded border border-hairline bg-surface-raised px-[10px] py-2">
          <span className="text-[13.5px] text-text">Long-range SAM / Pakistan</span>
          <span className="text-[10px] text-text-faint">▾</span>
        </div>
      </div>

      {/* Review — expands inline; deciding a card elsewhere drops the badge 3→2. */}
      <div className="border-b border-hairline">
        <div onClick={toggleReview} className="cursor-pointer px-[18px] pb-[14px] pt-4 hover:bg-surface-raised">
          <div className="flex items-center justify-between">
            <span className="text-[13px] text-text">Review</span>
            <span className="inline-flex h-5 min-w-[22px] items-center justify-center rounded-[3px] border border-accent px-[7px] text-[12px] tabular-nums text-accent">
              {reviewCount}
            </span>
          </div>
          {!reviewOpen && (
            <div className="mt-[6px] text-[11.5px] text-text-faint">items that landed in the uncertain middle</div>
          )}
        </div>
        {reviewOpen && (
          <div className="flex flex-col gap-[6px] px-3 pb-[14px]">
            {rows.map((row) => (
              <div
                key={row.key}
                onClick={row.onClick}
                className="cursor-pointer rounded border border-hairline bg-surface-raised px-[11px] py-[10px] hover:border-hairline-strong"
              >
                <div className="mb-1 flex items-center justify-between gap-2">
                  <span className="text-[10.5px] tracking-[0.04em] text-text-faint">{row.kicker}</span>
                  <span className="whitespace-nowrap rounded-[4px] border border-hairline-strong px-[7px] py-[1px] text-[10px] text-text-dim">
                    {row.badge}
                  </span>
                </div>
                <div className="text-[12.5px] leading-[1.35] text-text">{row.title}</div>
              </div>
            ))}
            {mode === 'live' && rows.length === 0 && (
              <div className="px-[11px] py-[10px] text-[11.5px] text-text-faint">
                Nothing in the uncertain middle right now.
              </div>
            )}
          </div>
        )}
      </div>

      {/* Watching — armed tripwires; a count without a config screen. */}
      <div onClick={openWatch} className="cursor-pointer border-b border-hairline px-[18px] py-4 hover:bg-surface-raised">
        <div className="flex items-center justify-between">
          <span className="text-[13px] text-text">Watching</span>
          <span className="inline-flex h-5 min-w-[22px] items-center justify-center rounded-[3px] border border-hairline-strong px-[7px] text-[12px] tabular-nums text-text-dim">
            3
          </span>
        </div>
        <div className="mt-[6px] text-[11.5px] text-text-faint">indicators &amp; warning — armed</div>
      </div>

      {/* Ingest — LIVE posts a keyless claim bundle to /ingest; DEMO runs the scripted
          trace (which renders on the stage, not here). */}
      {mode === 'live' && <LiveIngest />}
      {mode !== 'live' && (
      <div className="border-b border-hairline px-[18px] py-[14px]">
        <div className="mb-[9px] flex items-center justify-between">
          <span className="text-[10.5px] tracking-[0.06em] text-text-faint">Documents</span>
          <span onClick={resetIngest} className="cursor-pointer text-[10.5px] text-text-faint hover:text-text-dim">
            reset
          </span>
        </div>
        <div
          onDragOver={(e) => {
            e.preventDefault()
            try {
              e.dataTransfer.dropEffect = 'copy'
            } catch {
              /* noop */
            }
          }}
          onDrop={(e) => {
            e.preventDefault()
            const id = (e.dataTransfer.getData('text/plain') || dragDocRef.current) as DocId | ''
            if (id) startIngest(id)
          }}
          className="mb-[9px] rounded border border-dashed border-hairline-strong px-[10px] py-[13px] text-center"
        >
          <div className="text-[11.5px] text-text-dim">Drop a document</div>
          <div className="mt-[2px] text-[10px] text-text-faint">or select one below</div>
        </div>
        <div className="flex flex-col gap-[5px]">
          {INGEST_DOCS.map((doc) => {
            const done = !!ingested[doc.id]
            return (
              <div
                key={doc.id}
                draggable
                onDragStart={(e) => {
                  dragDocRef.current = doc.id
                  try {
                    e.dataTransfer.setData('text/plain', doc.id)
                    e.dataTransfer.effectAllowed = 'copy'
                  } catch {
                    /* noop */
                  }
                }}
                onClick={() => {
                  if (!ingestBusy) startIngest(doc.id)
                }}
                className={clsx(
                  'cursor-grab rounded-[3px] border px-[9px] py-[7px] hover:border-accent',
                  done ? 'border-live' : 'border-hairline-strong',
                )}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className={clsx('font-mono text-[11.5px]', done ? 'text-live' : 'text-text')}>
                    {done ? '✓ ' : ''}
                    {doc.id}
                  </span>
                  <span className="text-[9.5px] text-text-faint">{doc.kind}</span>
                </div>
                <div className="mt-[3px] font-mono text-[9.5px] text-text-faint">{doc.file}</div>
              </div>
            )
          })}
        </div>
      </div>
      )}

      <div className="flex-1" />

      {/* Credibility — a link, not a room. */}
      <div
        onClick={openCred}
        className="flex cursor-pointer items-center justify-between border-t border-hairline px-[18px] py-4 hover:bg-surface-raised"
      >
        <span className="text-[12.5px] text-text-dim">Credibility</span>
        <span className="text-[11px] text-text-faint">→</span>
      </div>
    </aside>
  )
}
