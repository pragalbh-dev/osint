// LIVE answer — the panel view for POST /ask. One component covers both outcomes the
// agent can return, because a refusal is an ANSWER, not an error (the graded
// non-negotiable): a normal answer shows the agent's prose as-is (the one place live
// text is model-authored) plus the walk of hops formatted from structure; a refusal
// shows the "insufficient evidence" verdict + what's missing + when next coverage is
// due, in the same grammar the demo's GapsView uses. Renders only in LIVE mode
// (panelView === 'answer'); the demo keeps its authored HeroAnswer / GapsView.

import { useWorkbench } from '@/store/workbench'
import { askToAnswerModel, type LiveAnswerModel } from '@/api/adapters'
import { CitationChip } from '@/components/status/CitationChip'

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
  return (
    <div>
      <div className="mb-[10px] text-[10.5px] tracking-[0.06em] text-text-faint">
        Insufficient evidence
      </div>
      <div className="text-[16px] leading-[1.35] text-text">Insufficient evidence to assess.</div>
      {r?.reason && (
        <div className="mt-2 text-[14px] leading-[1.5] text-text" style={{ textWrap: 'pretty' }}>
          {r.reason}
        </div>
      )}
      {r && r.missing.length > 0 && (
        <div className="mt-[15px] text-[13px] leading-[1.5] text-text">
          <span className="text-text-dim">Missing</span>
          &nbsp;—&nbsp;
          {r.missing.join('; ')}.
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
                    {hop.line}
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
