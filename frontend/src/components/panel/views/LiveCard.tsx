// LIVE review card — renders one derived queue item (merge / status-override /
// alert-disposition) into the panel's card slot and writes the decision through the
// matching /hitl/* route (store.decideLive). One component covers all three types: the
// shared frame (back, kicker+badge, title, options) plus a type-specific context block,
// in the same visual grammar the demo cards use. THE NO-HINT RULE holds — every option
// is styled identically, no default, no highlight. Renders only in LIVE mode.

import { useWorkbench } from '@/store/workbench'
import type { LiveReviewItem } from '@/api/adapters'
import { TierDots } from '@/components/status/TierDots'
import { AlertEvidence } from './AlertEvidence'

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

function MergeContext({ item }: { item: LiveReviewItem }) {
  const c = item.context
  return (
    <div className="mb-5">
      <div className="mb-5 flex items-stretch gap-[9px]">
        <div className="flex-1 rounded border border-hairline bg-surface-raised p-3">
          <div className="text-[13.5px] text-text">{c.left?.label}</div>
          <div className="mt-[3px] font-mono text-[10.5px] text-text-dim">{c.left?.id}</div>
        </div>
        <div className="flex-none self-center text-[13px] text-text-faint">↔</div>
        <div className="flex-1 rounded border border-hairline bg-surface-raised p-3">
          <div className="text-[13.5px] text-text">{c.right?.label}</div>
          <div className="mt-[3px] font-mono text-[10.5px] text-text-dim">{c.right?.id}</div>
        </div>
      </div>
      {typeof c.dots === 'number' && (
        <div className="flex items-center justify-between gap-3 py-[7px]">
          <span className="text-[12.5px] text-text-dim">Identity match</span>
          <TierDots n={c.dots} />
        </div>
      )}
      <div className="text-[13px] leading-[1.5] text-text-dim">{c.summary}</div>
    </div>
  )
}

function OverrideContext({ item }: { item: LiveReviewItem }) {
  const c = item.context
  return (
    <div className="mb-5">
      <div className="mb-4 text-[13px] leading-[1.55] text-text-dim">{c.summary}</div>
      {c.detail && c.detail.length > 0 && (
        <div className="rounded border-[1.5px] border-problem bg-[var(--fill-problem)] px-[14px] py-[13px]">
          <div className="mb-[9px] text-[10.5px] tracking-[0.06em] text-problem">Opposing claims</div>
          {c.detail.map((line) => (
            <div key={line} className="font-mono text-[11.5px] leading-[1.6] text-text">
              {line}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function AlertContext({ item }: { item: LiveReviewItem }) {
  const c = item.context
  return (
    <div className="mb-5">
      {c.changed && (c.changed.from || c.changed.to) && (
        <div className="mb-4 rounded border border-hairline bg-surface-raised px-[14px] py-[13px]">
          <div className="mb-[9px] text-[10.5px] tracking-[0.06em] text-text-faint">What changed</div>
          <div className="flex flex-wrap items-center gap-[10px] text-[13px] text-text">
            <span>{c.changed.from || '—'}</span>
            <span className="text-text-faint">→</span>
            <span>{c.changed.to || '—'}</span>
          </div>
        </div>
      )}
      <div className="text-[13px] leading-[1.55] text-text-dim">{c.summary}</div>
      {c.severity && (
        <div className="mt-2 font-mono text-[10.5px] text-text-faint">severity · {c.severity}</div>
      )}
      {/* "Is it real?" is only answerable from evidence — both sides of the change are one
          click from their sources, and a held supersession explains itself in its own words. */}
      <AlertEvidence provenance={c.provenance} holdReasons={c.holdReasons} />
    </div>
  )
}

export function LiveCard() {
  const item = useWorkbench((s) => s.activeLiveItem)
  const backToZero = useWorkbench((s) => s.backToZero)
  const decideLive = useWorkbench((s) => s.decideLive)

  if (!item) return null

  return (
    <div>
      <div className="mb-[15px] flex items-center gap-[10px]">
        <BackButton onClick={backToZero} />
        <span className="whitespace-nowrap rounded border border-hairline-strong px-[8px] py-[2px] text-[10.5px] text-text-dim">
          {item.badge}
        </span>
        <span className="text-[10.5px] tracking-[0.04em] text-text-faint">{item.kicker}</span>
      </div>

      <div className="mb-4 text-[17px] text-text">{item.title}</div>

      {item.reviewType === 'merge' && <MergeContext item={item} />}
      {item.reviewType === 'status-override' && <OverrideContext item={item} />}
      {item.reviewType === 'alert-disposition' && <AlertContext item={item} />}

      <div className="flex gap-2">
        {item.options.map((opt) => (
          <button
            key={opt.key}
            onClick={() => void decideLive(item, opt.key)}
            className="min-h-[44px] flex-1 cursor-pointer rounded border border-hairline-strong bg-transparent px-[6px] font-sans text-[11.5px] leading-[1.25] text-text hover:border-text-dim hover:bg-surface-raised"
          >
            {opt.label}
          </button>
        ))}
      </div>

      <div className="mt-[18px] border-t border-hairline pt-[14px] text-[11px] text-text-faint">
        Routed to review · reversible
      </div>
    </div>
  )
}
