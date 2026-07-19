// Hero answer — "trace this battery back to its component supplier." The decomposition
// IS the structure (design doc 11): each sub-question is one hop of a numbered WALK
// (places the system went and looked); the inference below is a conclusion DRAWN from
// the walk, sealed behind a dashed wall. Dashed = provisional — the fifth application of
// the one rule, so the boundary between observed and inferred is structural, not a tag.
// Hop 4 returns nothing and is still a hop: the guard against inferring sole-source from
// absence. (mockup lines 279-354)

import { useEffect, useState } from 'react'
import { useWorkbench, selHeroRevised } from '@/store/workbench'
import { TARGET_QUERIES, HERO_HOPS, HERO_REVISION, HERO_INFERENCE } from '@/demo/scenario'
import { CitationChip } from '@/components/status/CitationChip'

// Colour the load-bearing word without reducing the wall to a tag. "candidate" is doing
// the work (design doc 11 / copy deck §6): substitutable-by UNKNOWN is not proof of a
// single point of failure.
function highlightCandidate(text: string) {
  const idx = text.indexOf('candidate')
  if (idx === -1) return text
  return (
    <>
      {text.slice(0, idx)}
      <span style={{ color: 'var(--live)' }}>candidate</span>
      {text.slice(idx + 'candidate'.length)}
    </>
  )
}

// Deterministic stagger — the hops light as they land. No spinner; the answer forming
// IS the loading state (design doc 11 OPEN 3). Every item ends visible.
function useStaggeredReveal(count: number, stepMs = 120) {
  const [shown, setShown] = useState(0)
  useEffect(() => {
    const timers: ReturnType<typeof setTimeout>[] = []
    for (let i = 1; i <= count; i++) {
      timers.push(setTimeout(() => setShown(i), i * stepMs))
    }
    return () => timers.forEach(clearTimeout)
  }, [count, stepMs])
  return shown
}

export function HeroAnswer() {
  const backToZero = useWorkbench((s) => s.backToZero)
  const revised = useWorkbench(selHeroRevised)

  // hops + the inference wall as the final item
  const shown = useStaggeredReveal(HERO_HOPS.length + 1)
  const reveal = (i: number) => ({
    opacity: i < shown ? 1 : 0,
    transform: i < shown ? 'translateY(0)' : 'translateY(4px)',
    transition: 'opacity 300ms ease, transform 300ms ease',
  })

  return (
    <div>
      {/* back + echoed question */}
      <div className="mb-5 flex items-start gap-[10px]">
        <button
          type="button"
          onClick={backToZero}
          title="Ask something else"
          className="flex h-[26px] w-[26px] flex-none cursor-pointer items-center justify-center rounded border border-hairline bg-transparent text-[14px] leading-none text-text-dim hover:border-hairline-strong hover:text-text"
        >
          ←
        </button>
        <div className="pt-1 text-[12.5px] leading-[1.45] text-text-dim">{TARGET_QUERIES.hero}</div>
      </div>

      <div className="mb-[14px] text-[10.5px] tracking-[0.06em] text-text-faint">Observed · the walk</div>

      {/* the numbered walk */}
      {HERO_HOPS.map((hop, i) => {
        const isLast = i === HERO_HOPS.length - 1
        return (
          <div key={hop.step} className="flex gap-[13px]" style={reveal(i)}>
            {/* rail: numbered circle + connector (all but the last) */}
            <div className="flex flex-none flex-col items-center">
              <span
                className="flex h-[24px] w-[24px] items-center justify-center rounded-full border font-mono text-[11px] text-text-dim"
                style={{ borderColor: 'var(--hairline-strong)' }}
              >
                {hop.step}
              </span>
              {!isLast && <span className="mt-1 w-px flex-1 bg-hairline" />}
            </div>

            {/* content */}
            <div style={{ paddingBottom: isLast ? 4 : 20 }}>
              <div className="text-[12.5px] text-text-dim">{hop.question}</div>
              <div
                className={`mt-1 text-[14px] leading-[1.45] ${hop.dim ? 'text-text-dim' : 'text-text'}`}
              >
                {hop.finding}
              </div>

              {(hop.chips.length > 0 || hop.gapChip) && (
                <div className="mt-[9px] flex flex-wrap gap-[7px]">
                  {hop.chips.map((c) => (
                    <CitationChip key={c} label={c} status="confirmed" />
                  ))}
                  {hop.gapChip && <CitationChip label={hop.gapChip} status="gap" />}
                </div>
              )}

              {/* hop-2 diff-highlight after the merge decision — instant, no fade */}
              {hop.step === 2 && revised && (
                <div
                  className="mt-[11px] rounded px-[11px] py-[9px]"
                  style={{
                    background: 'rgba(var(--live-rgb),0.12)',
                    border: '1px solid rgba(var(--live-rgb),0.4)',
                  }}
                >
                  <span className="text-[10px] tracking-[0.06em] text-live">Revised</span>
                  <div className="mt-[3px] text-[12.5px] leading-[1.45] text-text">{HERO_REVISION}</div>
                </div>
              )}
            </div>
          </div>
        )
      })}

      {/* the inference — a WALL, not a tag. Dashed = provisional. */}
      <div
        className="mt-[22px] rounded-[3px]"
        style={{
          padding: '16px 17px',
          border: '1.5px dashed var(--live)',
          background: 'var(--fill-aging)',
          ...reveal(HERO_HOPS.length),
        }}
      >
        <div className="mb-[10px] text-[10.5px] tracking-[0.06em] text-text-faint">
          Inferred · a conclusion drawn from the walk
        </div>
        <div className="text-[14px] leading-[1.5] text-text" style={{ textWrap: 'pretty' }}>
          {highlightCandidate(HERO_INFERENCE.primary)}
        </div>
        <div
          className="mt-[12px] text-[13px] leading-[1.5] text-text-dim"
          style={{ textWrap: 'pretty' }}
        >
          {HERO_INFERENCE.secondary}
        </div>
      </div>
    </div>
  )
}
