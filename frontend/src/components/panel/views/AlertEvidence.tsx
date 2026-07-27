// The evidence behind one fired tripwire — the alert's provenance block, shared by the
// Watch panel (the feed) and the live alert-disposition card (the decision). An alert
// asserts that the world changed; under this system's non-negotiable that assertion is
// one click from its exact sources like every other element, and BOTH sides are traceable
// separately, because "what changed" is only auditable if the before and the after can be
// checked independently.
//
// Every clickable ref routes through store.openProvenance → the SAME provenance drawer
// (GET /evidence/{id}) that selecting a node opens. There is no second drill-down path.
// Claim ids are clickable only when their side names a resolvable element — a claim id is
// not an element id, and sending one to /evidence would 404 into an "insufficient
// evidence" panel that would be a lie about the evidence rather than a report of it.

import { useWorkbench } from '@/store/workbench'
import type { LiveAlertOriginContest, LiveAlertProvenanceModel } from '@/api/adapters'

const SIDE_LABEL = { before: 'Before', after: 'After' } as const

function RefChip({
  label,
  title,
  onClick,
}: {
  label: string
  title: string
  onClick?: () => void
}) {
  if (!onClick) {
    return (
      <span title={title} className="rounded-[3px] border border-hairline px-[6px] py-[1px] font-mono text-[10px] text-text-faint">
        {label}
      </span>
    )
  }
  return (
    <button
      type="button"
      onClick={onClick}
      title={title}
      className="cursor-pointer rounded-[3px] border border-hairline bg-transparent px-[6px] py-[1px] font-mono text-[10px] text-text-dim hover:border-live hover:text-live"
    >
      {label}
    </button>
  )
}

/** The alert says the move came from one place; the graph's own supersession says another.
 *
 *  Both are honestly derived and neither is a mistake: the tripwire's "before" is whichever basing
 *  edge represented the group in the previous view, and with four un-adjudicated basings on one unit
 *  that representative is settled by an id sort rather than by adjudication — while `supersedes`
 *  records the assertion the new one actually overtook. Two surfaces, two origins. This system's
 *  whole thesis is that a contest gets reported, so nothing here picks a winner: it names both, and
 *  names the other basings still on file that make "from" an open question rather than a fact. */
function OriginContest({ contest }: { contest: LiveAlertOriginContest }) {
  const openProvenance = useWorkbench((s) => s.openProvenance)
  return (
    <div className="mt-[10px] rounded border border-dashed border-problem px-[13px] py-[11px]">
      <div className="mb-[6px] font-mono text-[10px] tracking-[0.06em] text-problem">
        WHERE IT MOVED FROM IS CONTESTED
      </div>
      <div className="text-[12px] leading-[1.55] text-text-dim">
        The tripwire reports the move as coming from{' '}
        <span className="text-text">{contest.statedFrom}</span>, while the supersession this graph
        recorded says the assertion that was overtaken was the one at{' '}
        <span className="text-text">{contest.recordedFrom}</span>. Both are on file; nothing has
        adjudicated between them, so the origin is not settled here.
      </div>
      {contest.otherBasings.length > 0 && (
        <div className="mt-[8px] text-[12px] leading-[1.55] text-text-dim">
          {contest.otherBasings.length === 1
            ? 'One further basing is still recorded for this unit and no supersession retired it: '
            : `${contest.otherBasings.length} further basings are still recorded for this unit and no supersession retired them: `}
          {contest.otherBasings.map((b, i) => (
            <span key={b.ref}>
              {i > 0 ? ', ' : ''}
              <span className="text-text">{b.name}</span>
              {b.status ? ` (${b.status})` : ''}
            </span>
          ))}
          .
        </div>
      )}
      <div className="mt-[9px] flex flex-wrap gap-[6px]">
        {contest.statedFromRef && (
          <RefChip
            label="the tripwire's origin"
            title="Open the provenance of the basing the alert named"
            onClick={() => openProvenance(contest.statedFromRef as string)}
          />
        )}
        {contest.recordedFromRef && (
          <RefChip
            label="the recorded origin"
            title="Open the provenance of the assertion the successor overtook"
            onClick={() => openProvenance(contest.recordedFromRef as string)}
          />
        )}
        {contest.otherBasings.map((b) => (
          <RefChip
            key={b.ref}
            label={b.name}
            title="Open this basing's provenance"
            onClick={() => openProvenance(b.ref)}
          />
        ))}
      </div>
    </div>
  )
}

export function AlertEvidence({
  provenance,
  holdReasons = [],
  originContest = null,
}: {
  provenance?: LiveAlertProvenanceModel | null
  holdReasons?: string[]
  originContest?: LiveAlertOriginContest | null
}) {
  const openProvenance = useWorkbench((s) => s.openProvenance)

  return (
    <div className="mt-3 rounded border border-hairline px-[13px] py-[11px]">
      <div className="mb-[8px] text-[10.5px] tracking-[0.06em] text-text-faint">Evidence</div>

      {!provenance ? (
        // Never fabricate a citation to fill the block — say what is missing instead.
        <div className="text-[12px] leading-[1.5] text-text-dim">
          No evidence was recorded for this firing — there is nothing to trace to a source.
        </div>
      ) : (
        <>
          {provenance.status && (
            // The status word IS the verdict. No score is rendered beside it: the
            // numbers are uncalibrated, so a printed "0.79" is false precision
            // (copy deck §2) and the drawer rule "no percentages, not one" (doc 09).
            <div className="mb-[9px] text-[12px] leading-[1.5] text-text-dim">
              The new state reads {provenance.status}
            </div>
          )}

          {provenance.sides.length === 0 && (
            <div className="text-[12px] leading-[1.5] text-text-dim">
              No claims were recorded on either side of this change.
            </div>
          )}

          {provenance.sides.map((side) => (
            <div key={side.side} className="mb-[7px] flex flex-wrap items-center gap-[6px]">
              <span className="w-[42px] flex-none text-[11.5px] text-text-faint">{SIDE_LABEL[side.side]}</span>
              {side.elementRef && (
                <RefChip
                  label={side.elementRef}
                  title="Open this element's provenance"
                  onClick={() => openProvenance(side.elementRef as string)}
                />
              )}
              {side.claimIds.map((claimId) => (
                <RefChip
                  key={claimId}
                  label={claimId}
                  title={side.elementRef ? 'Trace this claim to its source' : 'Claim id (no element recorded to trace it through)'}
                  onClick={side.elementRef ? () => openProvenance(side.elementRef as string, claimId) : undefined}
                />
              ))}
              {!side.elementRef && side.claimIds.length === 0 && (
                <span className="text-[11.5px] text-text-dim">nothing recorded</span>
              )}
            </div>
          ))}
        </>
      )}

      {originContest && <OriginContest contest={originContest} />}

      {holdReasons.length > 0 && (
        // The old assertion was NOT auto-retired. The gate's own words, verbatim — a
        // paraphrase would put the UI between the analyst and the rule that fired.
        <div className="mt-[10px] border-t border-hairline pt-[9px]">
          <div className="mb-[6px] text-[12px] leading-[1.5] text-text-dim">
            Held for review rather than retired automatically, because:
          </div>
          {holdReasons.map((reason) => (
            // verbatim, but at the dim text token — it reads as evidence on the record,
            // not as headline copy the interface is asserting in its own voice.
            <div key={reason} className="font-mono text-[11px] leading-[1.6] text-text-dim">
              · {reason}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
