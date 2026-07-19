// Status-override card — "Is this really confirmed?" (mockup 462-489). The
// contradiction beat (d08 vs d09) lands here because `contradicted` is a status
// and resolving it means adjudicating a claim. THE NO-HINT RULE: promote / demote
// / reject are styled identically — no option reads as the "right" one.
import { useWorkbench } from '@/store/workbench'
import { OVERRIDE_CARD } from '@/demo/scenario'

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

export function OverrideCard() {
  const backToZero = useWorkbench((s) => s.backToZero)
  const decide = useWorkbench((s) => s.decide)

  return (
    <div>
      <div className="mb-[15px] flex items-center gap-[10px]">
        <BackButton onClick={backToZero} />
        <span className="whitespace-nowrap rounded border border-hairline-strong px-[8px] py-[2px] text-[10.5px] text-text-dim">
          {OVERRIDE_CARD.badge}
        </span>
      </div>

      <div className="mb-[14px] text-[17px] text-text">{OVERRIDE_CARD.subject}</div>
      <div className="mb-4 text-[13px] leading-[1.55] text-text-dim">{OVERRIDE_CARD.intro}</div>

      <div className="rounded border-[1.5px] border-problem bg-[var(--fill-problem)] px-[14px] py-[13px]">
        <div className="mb-[9px] text-[10.5px] tracking-[0.06em] text-problem">Against · same moment</div>
        {OVERRIDE_CARD.against.map((line, i) => (
          <div key={line} className={`text-[13px] leading-[1.5] text-text ${i > 0 ? 'mt-[5px]' : ''}`}>
            {line}
          </div>
        ))}
        <div className="mt-[9px] text-[12px] leading-[1.5] text-text-dim">{OVERRIDE_CARD.againstNote}</div>
      </div>

      <div className="mt-[18px]">
        <div className="mb-[7px] text-[10.5px] tracking-[0.06em] text-text-faint">If you reject</div>
        <div className="text-[13px] leading-[1.5] text-text">{OVERRIDE_CARD.ifYou}</div>
      </div>

      <div className="mt-[18px] flex gap-2">
        {OVERRIDE_CARD.options.map((opt) => (
          <button
            key={opt.key}
            onClick={() => decide(opt.key)}
            className="min-h-[44px] flex-1 cursor-pointer rounded border border-hairline-strong bg-transparent px-[6px] font-sans text-[11.5px] leading-[1.25] text-text hover:border-text-dim hover:bg-surface-raised"
          >
            {opt.label}
          </button>
        ))}
      </div>
      <div className="mt-[18px] border-t border-hairline pt-[14px] text-[11px] text-text-faint">
        {OVERRIDE_CARD.footer}
      </div>
    </div>
  )
}
