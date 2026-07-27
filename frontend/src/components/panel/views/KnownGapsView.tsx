// Known gaps — the named absences, live.
//
// This is the non-negotiable made visible. "Where evidence is absent, ambiguous or contradictory the
// system returns an explicit insufficient-evidence, NAMES what is missing and when next coverage is
// due" is the thing this system is FOR, and the rebuilt view computes 48 of them — with their
// coverage statements. Almost none of it reached a human: five gap-styled nodes on the canvas,
// twenty-two hanging off edges no surface could click, and an authored demo-only panel next door.
// A judgement that reaches no analyst is the same defect class as never computing it.
//
// The three ceilings are kept apart, because they are NOT the same kind of thing (spine/04, and the
// demo panel's own grammar): a collectable gap is a pending task, a probable-max gap is a ceiling
// that more collection will not lift, and a never-observable gap is a boundary with nothing to
// collect at all. Flattening them would turn a limit of the discipline into an unmet task.
//
// Nothing here composes a coverage sentence or a date. `coverage` is the backend's own words —
// including the honest "unscheduled — no collection is tasked against this gap", which a bare null
// date cannot say. A gap that carries none says the schedule was not recorded.

import { useMemo } from 'react'
import { useWorkbench } from '@/store/workbench'
import { groupGaps, viewToGaps, type LiveGapRow } from '@/api/adapters'
import { StatusSwatch } from '@/components/status/StatusSwatch'
import type { Ceiling } from '@/demo/scenario'

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

/** One gap. What is missing, when coverage is next due, and a door to the thing it is about —
 *  a gap the analyst cannot follow back to its element is a statement they can only agree with. */
function GapRow({ row }: { row: LiveGapRow }) {
  const openProvenance = useWorkbench((s) => s.openProvenance)
  return (
    <div className="border-t border-hairline py-[13px] first:border-t-0 first:pt-0">
      <div className="flex items-start gap-[9px]">
        <span className="mt-[3px] flex-none">
          <StatusSwatch status="known-gap" gap ceiling={row.ceiling as Ceiling} size={12} />
        </span>
        <div className="min-w-0">
          <div className="text-[13px] leading-[1.45] text-text" style={{ textWrap: 'pretty' }}>
            {row.whatMissing}
          </div>

          {row.missingSlots.length > 0 && (
            <div className="mt-[5px] font-mono text-[10.5px] leading-[1.5] text-text-faint">
              missing · {row.missingSlots.join(' · ')}
            </div>
          )}

          {/* WHEN coverage is next due — the backend's sentence, verbatim. */}
          <div className="mt-[7px] text-[12px] leading-[1.55] text-text-dim" style={{ textWrap: 'pretty' }}>
            {row.coverage ||
              'No coverage schedule was recorded for this gap. Treat it as untasked rather than as due soon.'}
          </div>
          {row.nextCoverageDue && (
            <div className="mt-[5px] font-mono text-[10.5px] text-text-faint">
              next coverage due · {row.nextCoverageDue}
            </div>
          )}

          {/* …and what it is ABOUT. One click into the same provenance drawer everything else uses. */}
          {row.aboutRef && (
            <div className="mt-[8px]">
              {row.aboutKind ? (
                <button
                  type="button"
                  onClick={() => openProvenance(row.aboutRef as string)}
                  title={row.aboutRef}
                  className="cursor-pointer rounded-[3px] border border-hairline bg-transparent px-[7px] py-[2px] text-left text-[11px] leading-[1.4] text-text-dim hover:border-live hover:text-live"
                >
                  about {row.aboutKind === 'edge' ? 'the relationship' : ''} {row.aboutName}
                </button>
              ) : (
                // The gap names a ref this view no longer carries. Say so; never link a dead id
                // into a drawer that would answer "insufficient evidence" about the wrong thing.
                <span className="font-mono text-[10.5px] text-text-faint">
                  about {row.aboutRef} — not in the current view
                </span>
              )}
            </div>
          )}

          {row.alsoRaisedAs.length > 0 && (
            <div className="mt-[6px] font-mono text-[10.5px] leading-[1.5] text-text-faint">
              the same absence is also raised on {row.alsoRaisedAs.length} other element
              {row.alsoRaisedAs.length === 1 ? '' : 's'}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export function KnownGapsView() {
  const backToZero = useWorkbench((s) => s.backToZero)
  const liveView = useWorkbench((s) => s.liveView)
  const groups = useMemo(() => groupGaps(viewToGaps(liveView)), [liveView])
  const total = groups.reduce((n, g) => n + g.rows.length, 0)

  return (
    <div>
      <div className="mb-[6px] flex items-center gap-[10px]">
        <BackButton onClick={backToZero} />
        <span className="text-[10.5px] tracking-[0.06em] text-text-faint">Known gaps</span>
      </div>

      <div className="mb-[18px] text-[13px] leading-[1.55] text-text-dim" style={{ textWrap: 'pretty' }}>
        {liveView == null
          ? 'The graph has not been read yet, so what is missing from it cannot be listed. Treat this as unknown, not as nothing missing.'
          : total === 0
            ? 'No gap is recorded against the current graph. That is the honest state of this view — not a claim that nothing is missing from the world.'
            : `${total} named absences, and they are not the same kind of thing.`}
      </div>

      {groups.map((group) => (
        <div key={group.ceiling} className="mb-[22px]">
          <div className="mb-[3px] text-[10.5px] tracking-[0.06em] text-text-faint">
            {group.label} · {group.rows.length}
          </div>
          <div className="mb-[12px] text-[12px] leading-[1.5] text-text-dim" style={{ textWrap: 'pretty' }}>
            {group.blurb}
          </div>
          {group.rows.map((row) => (
            <GapRow key={row.id} row={row} />
          ))}
        </div>
      ))}
    </div>
  )
}
