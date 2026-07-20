// The rail — subject (static lens), review queue (expands inline), watching,
// the ingest drop surface, and a quiet credibility link. Self-contained: reads the
// global store + demo scenario, takes no props. Faithful port of the handoff
// mockup's <aside> (design docs 08-layout §"eight surfaces → four zones",
// 10-review-card §"the queue list lives in the rail").
import { useMemo, useRef, useState } from 'react'
import clsx from 'clsx'
import { useWorkbench, type DocId } from '@/store/workbench'
import { INGEST_DOCS, QUEUE_ITEMS, TRIPWIRES } from '@/demo/scenario'
import { groupReviewQueue, viewToReviewQueue, type LiveReviewGroup } from '@/api/adapters'
import { useTripwires } from '@/api/viewmodel'
import { useArmedObservables } from '@/api/hooks'
import { watchSummary } from './watchSummary'
import { LiveIngest } from './LiveIngest'

/** One queue row — the same shape in both modes. A row has to be readable WITHOUT opening it:
 *  `kicker` says what kind of decision it is, `title` names the records it is about, `note`
 *  carries the one fact that separates it from its neighbours. */
interface RailRow {
  key: string
  kicker: string
  badges: string[]
  title: string
  note?: string
  onClick: () => void
}

function Chip({ label }: { label: string }) {
  return (
    <span className="whitespace-nowrap rounded-[4px] border border-hairline-strong px-[6px] py-[1px] text-[9.5px] text-text-dim">
      {label}
    </span>
  )
}

/** The mockup's grammar (kicker left, one chip right) is kept for the PRIMARY badge; any extra
 *  chip — materiality, severity — wraps under the title rather than squeezing the kicker, which
 *  at a 240px rail would truncate the one word that says what kind of decision this is. */
function Row({ row, inset = false }: { row: RailRow; inset?: boolean }) {
  const [primary, ...extra] = row.badges
  return (
    <div
      onClick={row.onClick}
      className={clsx(
        'cursor-pointer rounded border border-hairline bg-surface-raised px-[11px] py-[10px] hover:border-hairline-strong',
        inset && 'ml-[10px] border-l-2 border-l-hairline-strong',
      )}
    >
      <div className="mb-1 flex items-start justify-between gap-2">
        <span className="min-w-0 shrink truncate text-[10.5px] leading-[1.3] tracking-[0.04em] text-text-faint">
          {row.kicker}
        </span>
        {primary && <span className="flex-none">{<Chip label={primary} />}</span>}
      </div>
      <div className="text-[12.5px] leading-[1.35] text-text">{row.title}</div>
      {extra.length > 0 && (
        <div className="mt-[5px] flex flex-wrap gap-[3px]">
          {extra.map((b) => (
            <Chip key={b} label={b} />
          ))}
        </div>
      )}
      {row.note && <div className="mt-[3px] text-[10.5px] leading-[1.35] text-text-faint">{row.note}</div>}
    </div>
  )
}

/** A run of connected identity proposals, presented as ONE question with N decisions inside it.
 *  Collapsed by default; expanding lists every member row, each still individually decidable —
 *  the cluster is a lens on the queue, never a filter over it. */
function ClusterRow({
  group,
  open,
  onToggle,
  onOpenItem,
}: {
  group: LiveReviewGroup
  open: boolean
  onToggle: () => void
  onOpenItem: (item: LiveReviewGroup['items'][number]) => void
}) {
  return (
    <div className="flex flex-col gap-[6px]">
      <div
        onClick={onToggle}
        className="cursor-pointer rounded border border-hairline bg-surface-raised px-[11px] py-[10px] hover:border-hairline-strong"
      >
        <div className="mb-1 flex items-start justify-between gap-2">
          <span className="min-w-0 shrink truncate text-[10.5px] leading-[1.3] tracking-[0.04em] text-text-faint">
            {group.kicker}
          </span>
          <span className="flex-none">{<Chip label={`${group.items.length}`} />}</span>
        </div>
        <div className="flex items-center justify-between gap-2 text-[12.5px] leading-[1.35] text-text">
          <span>{group.title}</span>
          <span className="flex-none text-[10px] text-text-faint">{open ? '▾' : '▸'}</span>
        </div>
        {group.badges.length > 0 && (
          <div className="mt-[5px] flex flex-wrap gap-[3px]">
            {group.badges.map((b) => (
              <Chip key={b} label={b} />
            ))}
          </div>
        )}
        <div className="mt-[3px] text-[10.5px] leading-[1.35] text-text-faint">{group.note}</div>
      </div>
      {open &&
        group.items.map((item) => (
          <Row
            key={item.itemId}
            inset
            row={{
              key: item.itemId,
              kicker: item.kicker,
              badges: item.badges,
              title: item.title,
              note: item.note,
              onClick: () => onOpenItem(item),
            }}
          />
        ))}
    </div>
  )
}

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

  // LIVE: the derived queue, ordered by the triage rule and with connected identity proposals
  // collapsed into clusters. Nothing is dropped or auto-decided — `groups` is a permutation of
  // the undecided queue, so the count below is still the true escalation count.
  const groups: LiveReviewGroup[] = useMemo(() => {
    if (mode !== 'live') return []
    const queue = liveView ? viewToReviewQueue(liveView) : []
    return groupReviewQueue(queue.filter((i) => !liveDecided[i.itemId]))
  }, [mode, liveView, liveDecided])

  // DEMO: the three scripted cards, unchanged in behaviour and order.
  const demoRows: RailRow[] = useMemo(
    () =>
      QUEUE_ITEMS.filter((i) => !decided[i.id]).map((i) => ({
        key: i.id,
        kicker: i.type,
        badges: [i.badge],
        // the records first (what this row IS), the question underneath — same grammar as live
        title: i.detail,
        note: i.subject,
        onClick: () => openCard(i.id),
      })),
    [decided, openCard],
  )

  const reviewCount =
    mode === 'live' ? groups.reduce((n, g) => n + g.items.length, 0) : demoRows.length
  const clusterCount = groups.filter((g) => g.kind === 'cluster').length

  // Clusters start collapsed — a run of connected proposals is ONE question until the analyst
  // chooses to take it apart. Purely presentational: every member is one click from the surface.
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})
  const toggleGroup = (key: string) => setExpanded((e) => ({ ...e, [key]: !e[key] }))

  // Watching — count + caption are DERIVED, never a hardcoded "3 · armed", and now from TWO
  // sources rather than one: the ARMED catalogue (GET /config/observables, the live config store)
  // and the FIRED feed (/view.alerts). Deriving both from the feed is what used to render
  // "Watching 0 — none fired" on a cold boot of a system watching three things. If the catalogue
  // can't be read we say so instead of printing 0 — see watchSummary(). Demo output is unchanged.
  const tripwires = useTripwires()
  const armed = useArmedObservables()
  const watch = useMemo(
    () => watchSummary(armed, tripwires, TRIPWIRES.length),
    [armed, tripwires],
  )

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
          {reviewOpen && clusterCount > 0 && (
            <div className="mt-[6px] text-[11.5px] text-text-faint">
              {reviewCount} items · {groups.length} decisions — {clusterCount} identity cluster
              {clusterCount === 1 ? '' : 's'}
            </div>
          )}
        </div>
        {reviewOpen && (
          // Scrolls on its own: expanding a 28-member cluster must not push Watching, Documents
          // and Credibility off the bottom of the rail.
          <div className="flex max-h-[52vh] flex-col gap-[6px] overflow-y-auto px-3 pb-[14px]">
            {mode === 'live' &&
              groups.map((group) =>
                group.kind === 'cluster' ? (
                  <ClusterRow
                    key={group.key}
                    group={group}
                    open={!!expanded[group.key]}
                    onToggle={() => toggleGroup(group.key)}
                    onOpenItem={openLiveCard}
                  />
                ) : (
                  <Row
                    key={group.key}
                    row={{
                      key: group.key,
                      kicker: group.kicker,
                      badges: group.badges,
                      title: group.title,
                      note: group.note,
                      onClick: () => openLiveCard(group.items[0]),
                    }}
                  />
                ),
              )}
            {mode !== 'live' && demoRows.map((row) => <Row key={row.key} row={row} />)}
            {mode === 'live' && groups.length === 0 && (
              <div className="px-[11px] py-[10px] text-[11.5px] text-text-faint">
                Nothing in the uncertain middle right now.
              </div>
            )}
          </div>
        )}
      </div>

      {/* Watching — a count without a config screen; both halves are data (see `watch`). */}
      <div onClick={openWatch} className="cursor-pointer border-b border-hairline px-[18px] py-4 hover:bg-surface-raised">
        <div className="flex items-center justify-between">
          <span className="text-[13px] text-text">Watching</span>
          <span className="inline-flex h-5 min-w-[22px] items-center justify-center rounded-[3px] border border-hairline-strong px-[7px] text-[12px] tabular-nums text-text-dim">
            {watch.count}
          </span>
        </div>
        <div className="mt-[6px] text-[11.5px] text-text-faint">indicators &amp; warning — {watch.note}</div>
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
