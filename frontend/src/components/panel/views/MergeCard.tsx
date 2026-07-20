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
import { useWorkbench } from '@/store/workbench'
import { MERGE_CARD } from '@/demo/scenario'
import { TierDots } from '@/components/status/TierDots'

export interface MergeCardRow {
  label: string
  dots: number
  /** the raw signal, shown beside the dots when we have it (live); demo has no number */
  score?: number
}

export interface MergeCardSide {
  name: string
  sub: string
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
  differsOn: readonly string[]
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

export function MergeCardView({
  data,
  onBack,
  onDecide,
}: {
  data: MergeCardData
  onBack: () => void
  onDecide: (key: string) => void
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
        <div className="flex-1 rounded border border-hairline bg-surface-raised p-3">
          <div className="text-[13.5px] leading-[1.3] text-text">{data.left.name}</div>
          <div className="mt-[3px] text-[11.5px] text-text-dim">{data.left.sub}</div>
        </div>
        <div className="flex-none self-center text-[13px] text-text-faint">↔</div>
        <div className="flex-1 rounded border border-hairline bg-surface-raised p-3">
          <div className="text-[13.5px] leading-[1.3] text-text">{data.right.name}</div>
          <div className="mt-[3px] text-[11.5px] text-text-dim">{data.right.sub}</div>
        </div>
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
            <span className="text-[12.5px] text-text-dim">{row.label}</span>
            <span className="flex flex-none items-center gap-[8px]">
              {typeof row.score === 'number' && (
                <span className="font-mono text-[10.5px] tabular-nums text-text-faint">{row.score.toFixed(2)}</span>
              )}
              <TierDots n={row.dots} />
            </span>
          </div>
        ))}
      </div>

      <div className="rounded border-[1.5px] border-problem bg-[var(--fill-problem)] px-[14px] py-[13px]">
        <div className="mb-2 text-[10.5px] tracking-[0.06em] text-problem">Differs on</div>
        {data.differsOn.length === 0 && (
          <div className="text-[13.5px] leading-[1.5] text-text">
            Nothing on file separates them — and nothing yet establishes them as one.
          </div>
        )}
        {data.differsOn.map((line, i) => (
          <div key={line} className={`text-[13.5px] leading-[1.5] text-text ${i > 0 ? 'mt-1' : ''}`}>
            {line}
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

/** DEMO wrapper — the frozen scenario constant, byte-identical to the authored mockup. */
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
    differsOn: MERGE_CARD.differsOn,
    ifYou: [MERGE_CARD.ifYou],
    options: MERGE_CARD.options,
    splitNote: MERGE_CARD.splitNote,
    footer: MERGE_CARD.footer,
  }
  return <MergeCardView data={data} onBack={backToZero} onDecide={decide} />
}
