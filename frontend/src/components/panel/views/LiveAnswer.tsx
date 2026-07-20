// LIVE answer — the panel view for POST /ask. One component covers both outcomes the
// agent can return, because a refusal is an ANSWER, not an error (the graded
// non-negotiable): a normal answer shows the agent's prose as-is (the one place live
// text is model-authored) plus the walk of hops formatted from structure; a refusal
// shows the "insufficient evidence" verdict + what's missing + when next coverage is
// due, in the same grammar the demo's GapsView uses. Renders only in LIVE mode
// (panelView === 'answer'); the demo keeps its authored HeroAnswer / GapsView.

import { useWorkbench } from '@/store/workbench'
import { askToAnswerModel, humanizeEdge, type LiveAnswerModel } from '@/api/adapters'
import { useDisplayName } from '@/api/viewmodel'
import type { RefusalKind } from '@/api/types'
import { CitationChip } from '@/components/status/CitationChip'

// THREE refusals, three different claims about the world — and an analyst must never see them
// conflated. "Insufficient evidence to assess" says WE LOOKED AND THE WORLD IS THIN; printing it
// over a capability outage says the evidence is thin when in fact nothing was ever consulted,
// which overstates a gap that may not exist. Same mislabelling family as stale-vs-insufficient:
// a correctness bug, not copy. The backend tags the kind (RefusalPayload.kind); this only renders it.
const REFUSAL_COPY: Record<RefusalKind, { kicker: string; headline: string; missingLabel: string }> = {
  evidence: {
    kicker: 'Insufficient evidence',
    headline: 'Insufficient evidence to assess.',
    missingLabel: 'Missing',
  },
  capability: {
    kicker: 'Could not run',
    headline: 'The system could not run this query. No evidence was assessed.',
    missingLabel: 'Needs',
  },
  withheld: {
    kicker: 'Answer withheld',
    headline: 'An answer was found but withheld — it could not be fully cited.',
    missingLabel: 'Failed on',
  },
}

function BackButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      title="Ask something else"
      className="flex h-[26px] w-[26px] flex-none cursor-pointer items-center justify-center rounded border border-hairline bg-transparent text-[14px] leading-none text-text-dim hover:border-hairline-strong hover:text-text"
    >
      ←
    </button>
  )
}

function Refusal({ model }: { model: LiveAnswerModel }) {
  const r = model.refusal
  const displayName = useDisplayName()
  const copy = REFUSAL_COPY[r?.kind ?? 'evidence']
  // a missing slot that IS a graph element reads as its name; free text passes through untouched.
  // The withheld kind repeats one problem slug per rejected sentence ("not_entailed" ×4) — aggregate
  // duplicates into a count so the list reads as a tally, not a stutter.
  const counts = new Map<string, number>()
  for (const slot of r?.missing ?? []) {
    const name = displayName(slot)
    counts.set(name, (counts.get(name) ?? 0) + 1)
  }
  const missing = [...counts.entries()].map(([name, n]) => (n > 1 ? `${name} ×${n}` : name))
  return (
    <div>
      <div className="mb-[10px] text-[10.5px] tracking-[0.06em] text-text-faint">{copy.kicker}</div>
      <div className="text-[16px] leading-[1.35] text-text">{copy.headline}</div>
      {r?.reason && (
        <div className="mt-2 text-[14px] leading-[1.5] text-text" style={{ textWrap: 'pretty' }}>
          {r.reason}
        </div>
      )}
      {missing.length > 0 && (
        <div className="mt-[15px] text-[13px] leading-[1.5] text-text">
          <span className="text-text-dim">{copy.missingLabel}</span>
          &nbsp;—&nbsp;
          {missing.join('; ')}.
        </div>
      )}
      {r?.knownGap && (
        <div className="mt-[15px] rounded border border-hairline bg-surface-raised px-[13px] py-[11px]">
          <div className="text-[12.5px] leading-[1.5] text-text">{r.knownGap.what_missing}</div>
          <div className="mt-[6px] font-mono text-[10.5px] text-text-faint">
            ceiling · {r.knownGap.observability_ceiling}
          </div>
        </div>
      )}
      {r?.nextCoverageDue && (
        <div className="mt-[15px] text-[13px] leading-[1.5] text-text">
          <span className="text-text-dim">Next coverage</span>
          &nbsp;—&nbsp;
          {r.nextCoverageDue}.
        </div>
      )}
    </div>
  )
}

function Answer({ model }: { model: LiveAnswerModel }) {
  // the walk names its endpoints; an id the graph does not know passes through unchanged
  const displayName = useDisplayName()
  return (
    <div>
      {/* the agent's answer, as-is */}
      {model.answer && (
        <div className="mb-[22px] text-[15px] leading-[1.55] text-text" style={{ textWrap: 'pretty' }}>
          {model.answer}
        </div>
      )}

      {/* the walk — hops formatted from structure; observed vs inferred is structural */}
      {model.hops.length > 0 && (
        <>
          <div className="mb-[14px] text-[10.5px] tracking-[0.06em] text-text-faint">How this was traced</div>
          {model.hops.map((hop, i) => {
            const isLast = i === model.hops.length - 1
            return (
              <div key={`${hop.step}-${i}`} className="flex gap-[13px]">
                <div className="flex flex-none flex-col items-center">
                  <span
                    className="flex h-[24px] w-[24px] items-center justify-center rounded-full border font-mono text-[11px] text-text-dim"
                    style={{ borderColor: 'var(--hairline-strong)' }}
                  >
                    {hop.step}
                  </span>
                  {!isLast && <span className="mt-1 w-px flex-1 bg-hairline" />}
                </div>
                <div style={{ paddingBottom: isLast ? 4 : 18 }}>
                  <div className={`text-[13.5px] leading-[1.45] ${hop.observed ? 'text-text' : 'text-text-dim'}`}>
                    {`${displayName(hop.src)} — ${humanizeEdge(hop.edge)} → ${displayName(hop.dst)}`}
                  </div>
                  <div className="mt-[3px] text-[11px] text-text-faint">
                    {hop.observed ? 'observed' : 'inferred'}
                  </div>
                  {hop.citations.length > 0 && (
                    <div className="mt-[8px] flex flex-wrap gap-[7px]">
                      {hop.citations.map((c) => (
                        <CitationChip key={c} label={c} status={hop.observed ? 'confirmed' : 'probable'} />
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </>
      )}

      {/* trailing citations not already attached to a hop */}
      {model.citations.length > 0 && (
        <div className="mt-[22px] border-t border-hairline pt-[14px]">
          <div className="mb-[9px] text-[10.5px] tracking-[0.06em] text-text-faint">Sources</div>
          <div className="flex flex-wrap gap-[7px]">
            {model.citations.map((c) => (
              <CitationChip key={c} label={c} status="confirmed" />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export function LiveAnswer() {
  const backToZero = useWorkbench((s) => s.backToZero)
  const question = useWorkbench((s) => s.askQuestion)
  const result = useWorkbench((s) => s.askResult)
  const pending = useWorkbench((s) => s.askPending)
  const isError = useWorkbench((s) => s.askError)

  const model = result ? askToAnswerModel(result) : null

  return (
    <div>
      <div className="mb-5 flex items-start gap-[10px]">
        <BackButton onClick={backToZero} />
        <div className="pt-1 text-[12.5px] leading-[1.45] text-text-dim">{question}</div>
      </div>

      {pending && (
        <div className="text-[13px] leading-[1.5] text-text-faint">Tracing the graph…</div>
      )}

      {!pending && isError && (
        <div>
          <div className="mb-[10px] text-[10.5px] tracking-[0.06em] text-text-faint">No answer</div>
          <div className="text-[13.5px] leading-[1.5] text-text-dim">
            The graph could not be reached to answer this. Nothing was assessed.
          </div>
        </div>
      )}

      {!pending && !isError && model && (model.kind === 'refusal' ? <Refusal model={model} /> : <Answer model={model} />)}
    </div>
  )
}
