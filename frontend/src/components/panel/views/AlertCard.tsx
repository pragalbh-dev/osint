// Alert-disposition card — "A tripwire fired. Is it real?" (mockup 491-523).
// The triage ramp is the ONE place non-status colour appears, and only ever
// with a text label next to each dot — "Watch" is the emphasised state here.
// THE NO-HINT RULE: accept / dismiss / hold are styled identically.
import { useWorkbench } from '@/store/workbench'
import { ALERT_CARD } from '@/demo/scenario'

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

export function AlertCard() {
  const backToZero = useWorkbench((s) => s.backToZero)
  const decide = useWorkbench((s) => s.decide)

  return (
    <div>
      <div className="mb-[15px] flex items-center gap-[10px]">
        <BackButton onClick={backToZero} />
        <span className="whitespace-nowrap rounded border border-hairline-strong px-[8px] py-[2px] text-[10.5px] text-text-dim">
          {ALERT_CARD.badge}
        </span>
      </div>

      <div className="mb-[14px] text-[17px] text-text">{ALERT_CARD.subject}</div>

      {/* triage severity ramp — alert cards ONLY, always text-labelled */}
      <div className="mb-4 flex items-center gap-[14px] rounded border border-hairline bg-surface-raised px-3 py-[9px]">
        <span className="text-[10px] tracking-[0.06em] text-text-faint">Triage</span>
        <span className="inline-flex items-center gap-[6px]">
          <span className="h-2 w-2 rounded-full bg-sev-high" />
          <span className="text-[11px] text-text-faint">High</span>
        </span>
        <span className="inline-flex items-center gap-[6px]">
          <span
            className="h-[9px] w-[9px] rounded-full bg-sev-watch"
            style={{ boxShadow: '0 0 0 3px rgba(214,164,74,0.18)' }}
          />
          <span className="text-[12px] text-text">Watch</span>
        </span>
        <span className="inline-flex items-center gap-[6px]">
          <span className="h-2 w-2 rounded-full bg-sev-clear" />
          <span className="text-[11px] text-text-faint">Clear</span>
        </span>
      </div>

      <div className="mb-4 rounded border border-hairline bg-surface-raised px-[14px] py-[13px]">
        <div className="mb-[9px] text-[10.5px] tracking-[0.06em] text-text-faint">What changed</div>
        <div className="flex flex-wrap items-center gap-[10px] text-[13px] text-text">
          <span>{ALERT_CARD.changed.from}</span>
          <span className="text-text-faint">→</span>
          <span>{ALERT_CARD.changed.to}</span>
        </div>
      </div>

      <div className="mb-[18px] text-[13px] leading-[1.55] text-text-dim">{ALERT_CARD.note}</div>

      <div className="flex gap-2">
        {ALERT_CARD.options.map((opt) => (
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
        {ALERT_CARD.footer}
      </div>
    </div>
  )
}
