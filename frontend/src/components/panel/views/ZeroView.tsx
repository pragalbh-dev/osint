// Screen zero — the analyst arrives at a SITUATION, not a prompt. Already populated;
// no welcome, no empty centred text box. Three target queries as affordances. After a
// review decision, a quiet "resolved · reversible" note appears here. (design docs 08 / 13 P1)
import { useWorkbench } from '@/store/workbench'
import { TARGET_QUERIES } from '@/demo/scenario'

function Affordance({ text, onClick }: { text: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="flex cursor-pointer items-center justify-between gap-3 rounded border border-hairline bg-surface-raised px-[15px] py-[14px] text-left hover:border-hairline-strong hover:bg-[#242a30]"
    >
      <span className="text-[13.5px] leading-[1.45] text-text">{text}</span>
      <span className="text-[14px] text-text-faint">→</span>
    </button>
  )
}

export function ZeroView() {
  const askHero = useWorkbench((s) => s.askHero)
  const askGaps = useWorkbench((s) => s.askGaps)
  const select = useWorkbench((s) => s.select)
  const lastResolved = useWorkbench((s) => s.lastResolved)
  const live = useWorkbench((s) => s.mode) === 'live'

  return (
    <div>
      {lastResolved && (
        <div className="mb-4 flex items-start gap-[9px] rounded border border-hairline-strong bg-surface-raised px-3 py-[10px]">
          <span className="mt-[5px] h-[6px] w-[6px] flex-none rounded-full bg-live" />
          <span className="text-[12px] leading-[1.5] text-text-dim">
            {lastResolved}. Reversible — the same case resolves automatically next time.
          </span>
        </div>
      )}

      <div className="mb-[18px] text-[13px] text-text-dim">Ask about this subject.</div>

      <div className="flex flex-col gap-[10px]">
        <Affordance text={TARGET_QUERIES.hero} onClick={askHero} />
        {/* The two lower affordances are demo-script bindings: one opens the scripted Rahwali
            drawer by its demo-only id, the other poses a question with no subject to point at.
            In live mode both misfire (a 404 drawer / a context-free refusal), so live shows
            only the hero query — the one that routes through the real agent. */}
        {!live && <Affordance text={TARGET_QUERIES.provenance} onClick={() => select('rahwali')} />}
        {!live && <Affordance text={TARGET_QUERIES.gaps} onClick={askGaps} />}
      </div>

      <div className="mt-[26px] text-[11.5px] leading-[1.5] text-text-faint">
        Or select any pin to see how it&apos;s known.{!live && ' Rahwali is open for provenance.'}
      </div>
    </div>
  )
}
