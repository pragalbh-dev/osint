// Merge card — "Same system, or two?" (mockup 399-460). Matched-on is long and
// quiet (the machine's case FOR merging); differs-on is short and loud (what
// actually decides it — design doc 10, the ACH inversion). THE NO-HINT RULE:
// the three options below are styled identically — no default, no highlight,
// no implied order. If the system had a view, this card wouldn't exist.
import { useWorkbench } from '@/store/workbench'
import { MERGE_CARD } from '@/demo/scenario'
import { TierDots } from '@/components/status/TierDots'

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

export function MergeCard() {
  const backToZero = useWorkbench((s) => s.backToZero)
  const decide = useWorkbench((s) => s.decide)

  return (
    <div>
      <div className="mb-[15px] flex items-center gap-[10px]">
        <BackButton onClick={backToZero} />
        <div className="flex flex-wrap gap-[6px]">
          {MERGE_CARD.badges.map((b) => (
            <span
              key={b}
              className="whitespace-nowrap rounded border border-hairline-strong px-[8px] py-[2px] text-[10.5px] text-text-dim"
            >
              {b}
            </span>
          ))}
        </div>
      </div>

      <div className="mb-4 text-[17px] text-text">{MERGE_CARD.subject}</div>

      <div className="mb-5 flex items-stretch gap-[9px]">
        <div className="flex-1 rounded border border-hairline bg-surface-raised p-3">
          <div className="text-[13.5px] text-text">{MERGE_CARD.left.name}</div>
          <div className="mt-[3px] text-[11.5px] text-text-dim">{MERGE_CARD.left.sub}</div>
        </div>
        <div className="flex-none self-center text-[13px] text-text-faint">↔</div>
        <div className="flex-1 rounded border border-hairline bg-surface-raised p-3">
          <div className="text-[13.5px] text-text">{MERGE_CARD.right.name}</div>
          <div className="mt-[3px] text-[11.5px] text-text-dim">{MERGE_CARD.right.sub}</div>
        </div>
      </div>

      <div className="mb-[18px]">
        <div className="mb-[6px] text-[10.5px] tracking-[0.06em] text-text-faint">Matched on</div>
        {MERGE_CARD.matchedOn.map((row, i) => (
          <div
            key={row.label}
            className={`flex items-center justify-between gap-3 py-[7px] ${
              i < MERGE_CARD.matchedOn.length - 1 ? 'border-b border-hairline' : ''
            }`}
          >
            <span className="text-[12.5px] text-text-dim">{row.label}</span>
            <TierDots n={row.dots} />
          </div>
        ))}
      </div>

      <div className="rounded border-[1.5px] border-problem bg-[var(--fill-problem)] px-[14px] py-[13px]">
        <div className="mb-2 text-[10.5px] tracking-[0.06em] text-problem">Differs on</div>
        {MERGE_CARD.differsOn.map((line, i) => (
          <div key={line} className={`text-[13.5px] leading-[1.5] text-text ${i > 0 ? 'mt-1' : ''}`}>
            {line}
          </div>
        ))}
      </div>

      <div className="mt-[18px]">
        <div className="mb-[7px] text-[10.5px] tracking-[0.06em] text-text-faint">If you merge</div>
        <div className="text-[13px] leading-[1.5] text-text">{MERGE_CARD.ifYou}</div>
      </div>

      <div className="mt-[18px] flex gap-2">
        {MERGE_CARD.options.map((opt) => (
          <button
            key={opt.key}
            onClick={() => decide(opt.key)}
            className="min-h-[40px] flex-1 cursor-pointer rounded border border-hairline-strong bg-transparent px-[6px] font-sans text-[12px] leading-[1.25] text-text hover:border-text-dim hover:bg-surface-raised"
          >
            {opt.label}
          </button>
        ))}
      </div>
      <div className="mt-[9px] text-[11px] leading-[1.45] text-text-faint">{MERGE_CARD.splitNote}</div>
      <div className="mt-[18px] border-t border-hairline pt-[14px] text-[11px] text-text-faint">
        {MERGE_CARD.footer}
      </div>
    </div>
  )
}
