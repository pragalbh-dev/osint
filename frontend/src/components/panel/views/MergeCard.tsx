// Merge card — "Same system, or two?" (mockup 399-460). Matched-on is long and
// quiet (the machine's case FOR merging); differs-on is short and loud (what
// actually decides it — design doc 10, the ACH inversion). THE NO-HINT RULE:
// the three options below are styled identically — no default, no highlight,
// no implied order. If the system had a view, this card wouldn't exist.
//
// The card is a PURE VIEW over a `MergeCardData` model. DEMO passes the frozen
// scenario constant; LIVE passes a model built from the queue item the analyst
// actually clicked (LiveCard → mergeCardDataFromItem). One component, two feeds —
// so live mode can never silently render the demo's HQ-9/P example next to real data.
//
// T10 — TRACEABILITY. This card used to state its whole case and let you check none of it: the only
// clickable things on it were the back arrow and the three options. That breaks the project's
// non-negotiable ("every claim is one-click traceable to its exact source") on the one screen where an
// analyst is asked to make an identity call. Three doors were added, all into the SAME provenance
// drawer the rest of the app uses (store.openProvenance → GET /evidence/{id}); no second evidence view:
//
//   1. each record panel opens that record's claims (the claim count is the handle);
//   2. the "a source calls them the same" signal opens the claims that assert it — the candidate
//      same-as edge now cites them, so the drawer resolves the edge id directly;
//   3. each "differs on" line declares its own standing — the records it is read from (clickable), or
//      the sentence admitting it is the resolver's arithmetic. A computation is never dressed as a
//      citation, which is the exact failure this card exists to prevent.
//
// Every affordance is OPTIONAL in the model: demo passes no ids, so it renders byte-identically to
// before rather than showing links that open nothing.
import { useWorkbench } from '@/store/workbench'
import { MERGE_CARD } from '@/demo/scenario'
import { TierDots } from '@/components/status/TierDots'
import { CitationChip } from '@/components/status/CitationChip'

export interface MergeCardRow {
  label: string
  dots: number
  /** the raw signal, shown beside the dots when we have it (live); demo has no number */
  score?: number
  /** T10 — element id whose provenance drawer IS this signal's evidence (live, source-asserted only) */
  evidenceId?: string
  /** how many claims that drawer holds — printed on the chip so it says what it opens */
  evidenceCount?: number
}

/** T10 — one "differs on" line plus where it came from. `sides` names the record(s) whose stated values
 *  the line reads; `computed` is the admission that it is arithmetic/a resolver signal instead. */
export interface MergeCardDiff {
  text: string
  sides?: ('left' | 'right')[]
  computed?: string
}

export interface MergeCardSide {
  name: string
  sub: string
  /** T10 — id for GET /evidence/{id}. Present ⇒ the panel is a button into this record's claims. */
  evidenceId?: string
  /** the visible handle on that button. Absent ⇒ the panel is plain text (demo). */
  claimCount?: number
}

export interface MergeCardData {
  badges: readonly string[]
  /** the headline question */
  subject: string
  /** live only — the two records named in the rail row, repeated as the card's subtitle */
  subtitle?: string
  left: MergeCardSide
  right: MergeCardSide
  matchedOn: readonly MergeCardRow[]
  /** T10 — a quiet footnote under "Matched on" saying which rows are somebody's assertion and which
   *  are the resolver's own computation. Live only; omitted ⇒ nothing renders. */
  matchedNote?: string
  differsOn: readonly MergeCardDiff[]
  /** what the merge demonstrably does — counted, never estimated */
  ifYou: readonly string[]
  /** what this card CANNOT tell the analyst. Rendered as plainly as the consequence:
   *  an admitted unknown beside real data, never a plausible-looking number. */
  unknowns?: readonly string[]
  options: readonly { key: string; label: string }[]
  splitNote?: string
  footer: string
}

function BackButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      title="Back"
      className="flex h-[26px] w-[26px] flex-none cursor-pointer items-center justify-center rounded border border-hairline bg-transparent text-[14px] leading-none text-text-dim hover:border-hairline-strong hover:text-text"
    >
      ←
    </button>
  )
}

/** One of the two records. A button into its own evidence when the model carries an id; the same
 *  markup as plain text when it does not (demo), so an absent handle degrades to silence, never to a
 *  link that opens nothing. The claim count is the visible handle — it names what the click yields. */
function RecordPanel({ side, onOpen }: { side: MergeCardSide; onOpen?: (id: string) => void }) {
  const body = (
    <>
      <div className="text-[13.5px] leading-[1.3] text-text">{side.name}</div>
      <div className="mt-[3px] text-[11.5px] text-text-dim">{side.sub}</div>
      {side.evidenceId && typeof side.claimCount === 'number' && (
        <div className="mt-[7px] text-[11px] text-text-dim underline decoration-hairline-strong decoration-dotted underline-offset-[3px] group-hover:decoration-text-dim">
          see the {side.claimCount} claim{side.claimCount === 1 ? '' : 's'} →
        </div>
      )}
    </>
  )
  if (!side.evidenceId || !onOpen) {
    return <div className="flex-1 rounded border border-hairline bg-surface-raised p-3">{body}</div>
  }
  return (
    <button
      type="button"
      onClick={() => onOpen(side.evidenceId as string)}
      title={`Open the claims behind ${side.name}`}
      className="group flex-1 cursor-pointer rounded border border-hairline bg-surface-raised p-3 text-left hover:border-hairline-strong hover:bg-surface"
    >
      {body}
    </button>
  )
}

/** Where a "differs on" line stands: the record(s) it is read from (each one click from its claims),
 *  or the admission that it was computed. Rendered small and faint so the loud box stays loud. */
function DiffProvenance({
  row,
  data,
  onOpen,
}: {
  row: MergeCardDiff
  data: MergeCardData
  onOpen?: (id: string) => void
}) {
  const sides = (row.sides ?? [])
    .map((which) => (which === 'left' ? data.left : data.right))
    .filter((side) => side.evidenceId)
  if (row.computed) {
    return <div className="mt-[3px] text-[10.5px] leading-[1.4] text-text-faint">{row.computed}</div>
  }
  if (!onOpen || sides.length === 0) return null
  return (
    <div className="mt-[3px] text-[10.5px] leading-[1.4] text-text-faint">
      read from{' '}
      {sides.map((side, i) => (
        <span key={side.evidenceId}>
          {i > 0 && ' · '}
          <button
            type="button"
            onClick={() => onOpen(side.evidenceId as string)}
            title={`Open the claims behind ${side.name}`}
            className="cursor-pointer border-0 bg-transparent p-0 font-sans text-[10.5px] text-text-dim underline decoration-dotted underline-offset-[3px] hover:text-text"
          >
            {side.name}
          </button>
        </span>
      ))}
    </div>
  )
}

export function MergeCardView({
  data,
  onBack,
  onDecide,
  onOpenEvidence,
}: {
  data: MergeCardData
  onBack: () => void
  onDecide: (key: string) => void
  /** T10 — open an element's provenance drawer. Omitted in demo, where nothing carries a real id. */
  onOpenEvidence?: (id: string) => void
}) {
  return (
    <div>
      <div className="mb-[15px] flex items-center gap-[10px]">
        <BackButton onClick={onBack} />
        <div className="flex flex-wrap gap-[6px]">
          {data.badges.map((b) => (
            <span
              key={b}
              className="whitespace-nowrap rounded border border-hairline-strong px-[8px] py-[2px] text-[10.5px] text-text-dim"
            >
              {b}
            </span>
          ))}
        </div>
      </div>

      <div className="mb-1 text-[17px] text-text">{data.subject}</div>
      {data.subtitle && <div className="mb-4 text-[12.5px] leading-[1.4] text-text-dim">{data.subtitle}</div>}
      {!data.subtitle && <div className="mb-4" />}

      <div className="mb-5 flex items-stretch gap-[9px]">
        <RecordPanel side={data.left} onOpen={onOpenEvidence} />
        <div className="flex-none self-center text-[13px] text-text-faint">↔</div>
        <RecordPanel side={data.right} onOpen={onOpenEvidence} />
      </div>

      <div className="mb-[18px]">
        <div className="mb-[6px] text-[10.5px] tracking-[0.06em] text-text-faint">Matched on</div>
        {data.matchedOn.length === 0 && (
          <div className="py-[7px] text-[12.5px] text-text-dim">
            No positive identity signal was recorded for this pair.
          </div>
        )}
        {data.matchedOn.map((row, i) => (
          <div
            key={row.label}
            className={`flex items-center justify-between gap-3 py-[7px] ${
              i < data.matchedOn.length - 1 ? 'border-b border-hairline' : ''
            }`}
          >
            {/* A signal a SOURCE asserted is a citation and is rendered as one — the app's own chip,
                opening the same drawer everything else does. A signal the resolver computed over the
                two records has no source to open, so it stays plain text: the difference is the point. */}
            {row.evidenceId && onOpenEvidence ? (
              <CitationChip
                label={
                  typeof row.evidenceCount === 'number'
                    ? `${row.label} · ${row.evidenceCount} claim${row.evidenceCount === 1 ? '' : 's'}`
                    : row.label
                }
                status="probable"
                onClick={() => onOpenEvidence(row.evidenceId as string)}
              />
            ) : (
              <span className="text-[12.5px] text-text-dim">{row.label}</span>
            )}
            <span className="flex flex-none items-center gap-[8px]">
              {typeof row.score === 'number' && (
                <span className="font-mono text-[10.5px] tabular-nums text-text-faint">{row.score.toFixed(2)}</span>
              )}
              <TierDots n={row.dots} />
            </span>
          </div>
        ))}
        {data.matchedNote && (
          <div className="mt-[7px] text-[10.5px] leading-[1.45] text-text-faint">{data.matchedNote}</div>
        )}
      </div>

      <div className="rounded border-[1.5px] border-problem bg-[var(--fill-problem)] px-[14px] py-[13px]">
        <div className="mb-2 text-[10.5px] tracking-[0.06em] text-problem">Differs on</div>
        {data.differsOn.length === 0 && (
          <div className="text-[13.5px] leading-[1.5] text-text">
            Nothing on file separates them — and nothing yet establishes them as one.
          </div>
        )}
        {data.differsOn.map((row, i) => (
          <div key={row.text} className={i > 0 ? 'mt-[7px]' : ''}>
            <div className="text-[13.5px] leading-[1.5] text-text">{row.text}</div>
            <DiffProvenance row={row} data={data} onOpen={onOpenEvidence} />
          </div>
        ))}
      </div>

      <div className="mt-[18px]">
        <div className="mb-[7px] text-[10.5px] tracking-[0.06em] text-text-faint">If you merge</div>
        {data.ifYou.map((line) => (
          <div key={line} className="text-[13px] leading-[1.5] text-text">
            {line}
          </div>
        ))}
        {data.unknowns?.map((line) => (
          <div key={line} className="mt-[6px] text-[12px] leading-[1.45] text-text-faint">
            Not known from here — {line}
          </div>
        ))}
      </div>

      <div className="mt-[18px] flex gap-2">
        {data.options.map((opt) => (
          <button
            key={opt.key}
            onClick={() => onDecide(opt.key)}
            className="min-h-[40px] flex-1 cursor-pointer rounded border border-hairline-strong bg-transparent px-[6px] font-sans text-[12px] leading-[1.25] text-text hover:border-text-dim hover:bg-surface-raised"
          >
            {opt.label}
          </button>
        ))}
      </div>
      {data.splitNote && (
        <div className="mt-[9px] text-[11px] leading-[1.45] text-text-faint">{data.splitNote}</div>
      )}
      <div className="mt-[18px] border-t border-hairline pt-[14px] text-[11px] text-text-faint">{data.footer}</div>
    </div>
  )
}

/** DEMO wrapper — the frozen scenario constant, byte-identical to the authored mockup.
 *
 *  T10: the demo model carries NO evidence ids, and no `onOpenEvidence` is passed, so every affordance
 *  added for live mode is structurally absent here. The demo drawer's frozen fixture is about one
 *  scripted node, not these two records; a link into it would be a lie dressed as provenance. */
export function MergeCard() {
  const backToZero = useWorkbench((s) => s.backToZero)
  const decide = useWorkbench((s) => s.decide)
  const data: MergeCardData = {
    badges: MERGE_CARD.badges,
    subject: MERGE_CARD.subject,
    subtitle: `${MERGE_CARD.left.name} ↔ ${MERGE_CARD.right.name}`,
    left: MERGE_CARD.left,
    right: MERGE_CARD.right,
    matchedOn: MERGE_CARD.matchedOn,
    differsOn: MERGE_CARD.differsOn.map((text) => ({ text })),
    ifYou: [MERGE_CARD.ifYou],
    options: MERGE_CARD.options,
    splitNote: MERGE_CARD.splitNote,
    footer: MERGE_CARD.footer,
  }
  return <MergeCardView data={data} onBack={backToZero} onDecide={decide} />
}
