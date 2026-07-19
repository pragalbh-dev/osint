// Credibility rubric — weights recompute a live claim (mockup 525-571). This
// is the one surface where a percentage is legitimate: the rubric's own weight
// sliders and the recomputed source score/bar ARE the rubric, not a false-precision
// confidence readout. Weighted, not averaged (scoreSource in the store).
import { useWorkbench, scoreSource } from '@/store/workbench'
import { CRED_SOURCES, CRED_FACTORS, CRED_INTRO } from '@/demo/scenario'
import { StatusSwatch } from '@/components/status/StatusSwatch'

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

export function CredView() {
  const backToZero = useWorkbench((s) => s.backToZero)
  const weights = useWorkbench((s) => s.weights)
  const setWeight = useWorkbench((s) => s.setWeight)

  const [srcA, srcB] = CRED_SOURCES
  const s08 = scoreSource(weights, srcA)
  const s09 = scoreSource(weights, srcB)
  const credConfirmed = s08 > s09
  const scores: Record<string, number> = { [srcA.key]: s08, [srcB.key]: s09 }

  const credVerdictClaim = credConfirmed
    ? 'HQ-9 unit actively deployed, Karachi-East'
    : 'Deployment unconfirmed — reads as routine movement'
  const credVerdictNote = credConfirmed
    ? 'Weighting directness, the firsthand imagery (d08) outweighs the official denial. Status recomputes to confirmed.'
    : 'Weighting authority, the official statement (d09) outweighs the social imagery. Status holds at probable.'

  return (
    <div>
      <div className="mb-[6px] flex items-center gap-[10px]">
        <BackButton onClick={backToZero} />
        <span className="text-[10.5px] tracking-[0.06em] text-text-faint">Credibility · rubric weights</span>
      </div>
      <div className="mb-[18px] text-[13px] leading-[1.55] text-text-dim">{CRED_INTRO}</div>

      <div className="flex flex-col gap-4">
        {CRED_FACTORS.map((f) => (
          <div key={f.key}>
            <div className="mb-[6px] flex items-baseline justify-between">
              <span className="text-[12.5px] text-text">{f.label}</span>
              <span className="font-mono text-[12px] text-accent">{weights[f.key]}</span>
            </div>
            <input
              type="range"
              min={0}
              max={100}
              step={5}
              value={weights[f.key]}
              onChange={(e) => setWeight(f.key, Number(e.target.value))}
              onInput={(e) => setWeight(f.key, Number((e.target as HTMLInputElement).value))}
              className="h-[3px] w-full cursor-pointer accent-accent"
            />
            <div className="mt-1 text-[10.5px] text-text-faint">{f.hint}</div>
          </div>
        ))}
      </div>

      {/* the payoff: a live-recomputing claim */}
      <div className="mt-[22px] border-t border-hairline pt-[18px]">
        <div className="mb-[10px] text-[10.5px] tracking-[0.06em] text-text-faint">
          recomputes now · Karachi-East, 09 May 2025
        </div>
        <div className="mb-3 flex items-center gap-3">
          <StatusSwatch status={credConfirmed ? 'confirmed' : 'probable'} size={15} />
          <span className="text-[18px] text-text">{credConfirmed ? 'Confirmed' : 'Probable'}</span>
        </div>
        <div className="mb-[14px] text-[13px] leading-[1.5] text-text">{credVerdictClaim}</div>

        <div className="flex flex-col gap-[11px]">
          {CRED_SOURCES.map((src) => {
            const score = scores[src.key]
            return (
              <div key={src.key} className="rounded-[3px] border border-hairline px-[11px] py-[10px]">
                <div className="mb-[3px] flex items-baseline justify-between gap-2">
                  <span className="font-mono text-[12px] text-text">{src.label}</span>
                  <span className="font-mono text-[13px] text-text">{score}</span>
                </div>
                <div className="mb-2 text-[10.5px] text-text-faint">
                  {src.kind} — asserts &ldquo;{src.asserts}&rdquo;
                </div>
                <div className="h-[3px] overflow-hidden rounded-full bg-hairline">
                  <div
                    className="h-full bg-text-dim"
                    style={{ width: `${Math.max(4, score)}%` }}
                  />
                </div>
              </div>
            )
          })}
        </div>
        <div className="mt-[14px] text-[12px] leading-[1.55] text-text-dim">{credVerdictNote}</div>
      </div>
    </div>
  )
}
