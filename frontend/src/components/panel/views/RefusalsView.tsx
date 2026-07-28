// Refused, recorded — identity questions the resolver already answered for the analyst.
//
// The review queue is for decisions. This is not that: every pair here was DISPOSED OF by a rail —
// declined, with a stated ground — and is shown so the refusal is visible rather than silent. The two
// used to share one surface, and on the booted corpus that meant 114 unanswerable items sitting beside
// 18 real ones. An analyst cannot merge a component with a variant however they answer; they cannot
// settle an identity whose deciding attribute the closed vocabulary cannot read. A queue that asks
// questions nobody can answer is how the answerable ones stop being read.
//
// Kept VISIBLE, deliberately — "a gap that does not bind the fusion path is decoration". Silence here
// would read as an all-clear about identity, and it is not one: these pairs are unresolved, they are
// simply not unresolved in a way a decision can fix.
//
// Grouped by the resolver's OWN leading clause, never a re-worded summary, so a rail that changes its
// reasoning cannot leave this surface asserting the old one. Grounds are ordered by weight, because the
// biggest group is the one worth fixing upstream — 66 of these are one unreadable site class away from
// being decidable at all.

import { useMemo, useState } from 'react'
import { useWorkbench } from '@/store/workbench'
import { viewToRecordedRefusals, type RecordedRefusalGroup } from '@/api/adapters'

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

/** One refused pair. The two names, the score that was not enough, and a door to the drawn edge —
 *  a refusal an analyst cannot follow back to its evidence is one they can only take on trust. */
function RefusalRow({
  id,
  leftLabel,
  rightLabel,
  confidence,
}: {
  id: string
  leftLabel: string
  rightLabel: string
  confidence: number | null
}) {
  const openProvenance = useWorkbench((s) => s.openProvenance)
  return (
    <button
      onClick={() => openProvenance(id)}
      className="flex w-full cursor-pointer items-baseline justify-between gap-3 border-b border-hairline bg-transparent px-0 py-[7px] text-left last:border-b-0 hover:bg-surface-raised"
    >
      <span className="text-[12.5px] leading-[1.45] text-text-dim">
        {leftLabel} <span className="text-text-faint">↔</span> {rightLabel}
      </span>
      <span className="flex-none tabular-nums text-[11.5px] text-text-faint">
        {confidence != null ? confidence.toFixed(2) : '—'}
      </span>
    </button>
  )
}

/** One ground, collapsed by default. The count is the point: an analyst scanning this page is looking
 *  for which REASON dominates, not for individual pairs, so the pairs stay one click away. */
function GroundBlock({ group }: { group: RecordedRefusalGroup }) {
  const [open, setOpen] = useState(false)
  const sample = group.items[0]
  return (
    <div className="border border-hairline bg-surface">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full cursor-pointer items-start justify-between gap-3 bg-transparent px-[14px] py-[11px] text-left hover:bg-surface-raised"
      >
        <span className="flex flex-col gap-[3px]">
          <span className="text-[13px] leading-[1.4] text-text">{group.ground}</span>
          <span className="text-[11.5px] text-text-faint">
            {group.items.length} pair{group.items.length === 1 ? '' : 's'} · refused, not queued
          </span>
        </span>
        <span className="flex-none pt-[2px] text-[11px] text-text-faint">{open ? '−' : '+'}</span>
      </button>
      {open && (
        <div className="border-t border-hairline px-[14px] pb-[10px] pt-[8px]">
          {sample?.reason && (
            <p className="mb-[8px] text-[11.5px] leading-[1.55] text-text-faint">{sample.reason}</p>
          )}
          {group.items.map((item) => (
            <RefusalRow key={item.id} {...item} />
          ))}
        </div>
      )}
    </div>
  )
}

export function RefusalsView() {
  const liveView = useWorkbench((s) => s.liveView)
  const backToZero = useWorkbench((s) => s.backToZero)
  const groups = useMemo(() => (liveView ? viewToRecordedRefusals(liveView) : []), [liveView])
  const total = groups.reduce((n, g) => n + g.items.length, 0)

  return (
    <div className="flex flex-col gap-[14px] px-[18px] py-4">
      <div className="flex items-center gap-[10px]">
        <BackButton onClick={backToZero} />
        <span className="text-[13px] text-text">Refused, recorded</span>
      </div>

      <p className="text-[12px] leading-[1.6] text-text-dim">
        Identity questions the resolver settled without an analyst — declined, each with its ground.
        They are here so the refusal is visible, not because there is something to decide: a component
        and a variant cannot be merged however anyone answers, and an identity whose deciding attribute
        no source states readably cannot be settled from this screen. Decisions live in Review.
      </p>

      {total === 0 ? (
        <p className="text-[12px] leading-[1.6] text-text-faint">
          Nothing refused on the current view. That is not an all-clear about identity — it means every
          pair the resolver considered either merged, scored into Review, or stayed on the watch-list.
        </p>
      ) : (
        <>
          <p className="text-[11.5px] text-text-faint">
            {total} pair{total === 1 ? '' : 's'} across {groups.length} ground
            {groups.length === 1 ? '' : 's'}. The largest group is the one worth fixing upstream.
          </p>
          <div className="flex flex-col gap-[6px]">
            {groups.map((g) => (
              <GroundBlock key={g.ground} group={g} />
            ))}
          </div>
        </>
      )}
    </div>
  )
}
