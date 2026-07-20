// LIVE review card — renders one derived queue item (merge / status-override /
// alert-disposition) into the panel's card slot and writes the decision through the
// matching /hitl/* route (store.decideLive). One component covers all three types: the
// shared frame (back, kicker+badge, title, options) plus a type-specific context block,
// in the same visual grammar the demo cards use. THE NO-HINT RULE holds — every option
// is styled identically, no default, no highlight. Renders only in LIVE mode.

import { useWorkbench } from '@/store/workbench'
import type { LiveReviewItem } from '@/api/adapters'
import { AlertEvidence } from './AlertEvidence'
import { MergeCardView, type MergeCardData } from './MergeCard'

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

/** LIVE queue item → the SAME merge card the demo renders, fed from the real proposal.
 *  Every field is derived in `viewToReviewQueue` off the two records and the resolver's own
 *  per-signal breakdown; nothing here authors a number. When a value is genuinely unavailable
 *  the card is given the absence to print (`unknowns`), never a stand-in. */
export function mergeCardDataFromItem(item: LiveReviewItem): MergeCardData {
  const m = item.context.merge
  const left = m?.left
  const right = m?.right
  // A proposal that is one of a connected run is not independent evidence — that belongs with
  // the case AGAINST, where the analyst is actually deciding.
  const differsOn = [
    ...(m?.differsOn ?? []),
    ...(item.cluster
      ? [
          `One of ${item.cluster.size} proposals across ${item.cluster.records} records — ${
            item.cluster.complete
              ? 'every possible pair among them is proposed, so this one is not independent evidence'
              : 'the proposals overlap, so this one is not independent evidence'
          }.`,
        ]
      : []),
  ]
  return {
    badges: item.badges,
    subject: item.question,
    subtitle: item.title,
    left: { name: left?.label ?? item.context.left?.label ?? '—', sub: left?.sub ?? item.context.left?.id ?? '' },
    right: { name: right?.label ?? item.context.right?.label ?? '—', sub: right?.sub ?? item.context.right?.id ?? '' },
    matchedOn: (m?.matchedOn ?? []).map((row) => ({ label: row.label, dots: row.dots, score: row.score })),
    differsOn,
    ifYou: m?.consequence ?? [],
    unknowns: m?.unknowns ?? [],
    options: item.options.map((o) => ({ key: o.key, label: o.label })),
    splitNote: 'Split separates one record that is really two.',
    footer: 'Flagged by the resolver’s merge check · routed to review · reversible',
  }
}

/** "If you decide" — what the decision demonstrably does, then what this card cannot say.
 *  The unknown is printed as plainly as the consequence: a fabricated number beside real data
 *  is the one thing the brief calls disqualifying. */
function Consequence({ item, verb }: { item: LiveReviewItem; verb: string }) {
  const lines = item.context.consequence ?? []
  const unknowns = item.context.unknowns ?? []
  if (lines.length === 0 && unknowns.length === 0) return null
  return (
    <div className="mb-5">
      <div className="mb-[7px] text-[10.5px] tracking-[0.06em] text-text-faint">{verb}</div>
      {lines.map((line) => (
        <div key={line} className="text-[13px] leading-[1.5] text-text">
          {line}
        </div>
      ))}
      {unknowns.map((line) => (
        <div key={line} className="mt-[6px] text-[12px] leading-[1.45] text-text-faint">
          Not known from here — {line}
        </div>
      ))}
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

  // A merge is the ★ marquee control point and has its own authored layout (matched-on quiet,
  // differs-on loud). LIVE feeds that same component with the clicked proposal's real evidence.
  if (item.reviewType === 'merge') {
    return (
      <MergeCardView
        data={mergeCardDataFromItem(item)}
        onBack={backToZero}
        onDecide={(key) => void decideLive(item, key)}
      />
    )
  }

  return (
    <div>
      <div className="mb-[15px] flex flex-wrap items-center gap-[6px]">
        <BackButton onClick={backToZero} />
        {item.badges.map((b) => (
          <span
            key={b}
            className="whitespace-nowrap rounded border border-hairline-strong px-[8px] py-[2px] text-[10.5px] text-text-dim"
          >
            {b}
          </span>
        ))}
        <span className="text-[10.5px] tracking-[0.04em] text-text-faint">{item.kicker}</span>
      </div>

      <div className="mb-1 text-[17px] text-text">{item.question}</div>
      <div className="mb-4 text-[12.5px] leading-[1.4] text-text-dim">{item.title}</div>

      {item.reviewType === 'status-override' && <OverrideContext item={item} />}
      {item.reviewType === 'alert-disposition' && <AlertContext item={item} />}
      <Consequence item={item} verb={item.reviewType === 'status-override' ? 'If you override' : 'If you decide'} />

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
