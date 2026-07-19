// Gaps / refusals — the money moment. "What do we not know here?" answered three ways,
// because the three are NOT the same kind of thing (design doc 11 OPEN 2 / copy deck §5):
//   confirmable      → a pending task. Names the next pass, ends in an action.
//   probable-max     → a ceiling. An estimate + "collecting more won't change this." No action.
//   never-observable → a boundary. Hatched mark, "this is a boundary, not a gap." Nothing to collect.
// State the standard BEFORE the failure so it reads as rigour, not breakage. No icon, no grey
// box, no apology, no spinner — a refusal is an ANSWER. (mockup lines 356-397)

import { useWorkbench } from '@/store/workbench'
import { TARGET_QUERIES, GAP_BLOCKS, type GapBlock } from '@/demo/scenario'
import { CitationChip } from '@/components/status/CitationChip'

// Hatched square that marks the boundary block — repeating diagonal in the history
// (achromatic/absence) family. The visual tell that there is genuinely nothing to collect.
function HatchMark() {
  return (
    <span
      className="inline-block flex-none"
      style={{
        width: 12,
        height: 12,
        borderRadius: 2,
        border: '1px solid var(--text-dim)',
        background:
          'repeating-linear-gradient(45deg,transparent,transparent 2px,rgba(var(--history-rgb),0.5) 2px,rgba(var(--history-rgb),0.5) 3px)',
      }}
    />
  )
}

function Lines({ block }: { block: GapBlock }) {
  const hasLabels = block.lines.some((l) => l.label)

  // Held / Missing / Next pass — mirrors the hop structure, so a refusal reads as an answer.
  if (hasLabels) {
    return (
      <div className="mt-[15px] flex flex-col gap-[12px]">
        {block.lines.map((line, i) => (
          <div key={i} className="text-[13px] leading-[1.5] text-text">
            {line.label && <span className="text-text-dim">{line.label}</span>}
            {line.label && <>&nbsp;—&nbsp;</>}
            {line.text}
            {line.chip && (
              <span className="ml-[6px] inline-block align-middle">
                <CitationChip label={line.chip} status="probable" />
              </span>
            )}
          </div>
        ))}
      </div>
    )
  }

  // Ceiling / boundary — first line is the estimate/statement (louder), the rest explain.
  return (
    <>
      {block.lines.map((line, i) => (
        <div
          key={i}
          className={
            i === 0
              ? 'mt-2 text-[14px] leading-[1.5] text-text'
              : 'mt-[10px] text-[13px] leading-[1.5] text-text-dim'
          }
          style={{ textWrap: 'pretty' }}
        >
          {line.text}
        </div>
      ))}
    </>
  )
}

function Block({ block, first, last }: { block: GapBlock; first: boolean; last: boolean }) {
  const isBoundary = block.ceiling === 'never-observable'
  return (
    <div
      style={{
        borderTop: first ? undefined : '1px solid var(--hairline)',
        paddingTop: first ? undefined : 22,
        paddingBottom: last ? 4 : 22,
      }}
    >
      {/* kicker — hatched mark precedes it only on the boundary block */}
      {isBoundary ? (
        <div className="mb-[10px] flex items-center gap-2">
          <HatchMark />
          <span className="text-[10.5px] tracking-[0.06em] text-text-faint">{block.kicker}</span>
        </div>
      ) : (
        <div className="mb-[10px] text-[10.5px] tracking-[0.06em] text-text-faint">{block.kicker}</div>
      )}

      {/* verdict */}
      <div className="text-[16px] leading-[1.35] text-text">{block.verdict}</div>

      {/* the rule, stated BEFORE the failure */}
      {block.standard && (
        <div
          className="mt-2 text-[14.5px] leading-[1.5] text-text"
          style={{ textWrap: 'pretty' }}
        >
          {block.standard}
        </div>
      )}

      <Lines block={block} />

      {/* tail — a ceiling states its own limit as fact; a boundary labels the absence */}
      {block.tail && (
        <div
          className={
            block.ceiling === 'never-observable'
              ? 'mt-[15px] text-[12.5px] leading-[1.5] text-text-faint'
              : 'mt-3 text-[13.5px] leading-[1.5] text-text'
          }
        >
          {block.tail}
        </div>
      )}

      {/* a refusal that produces a work order is not a failure — it's the next move */}
      {block.actionKind === 'button' && block.action && (
        <button
          type="button"
          className="mt-4 h-[34px] cursor-pointer rounded border border-accent bg-transparent px-[15px] font-sans text-[12.5px] text-accent hover:bg-[rgba(var(--accent-primary-rgb),0.10)]"
        >
          {block.action}
        </button>
      )}
    </div>
  )
}

export function GapsView() {
  const backToZero = useWorkbench((s) => s.backToZero)

  return (
    <div>
      {/* back + echoed question */}
      <div className="mb-[18px] flex items-start gap-[10px]">
        <button
          type="button"
          onClick={backToZero}
          title="Ask something else"
          className="flex h-[26px] w-[26px] flex-none cursor-pointer items-center justify-center rounded border border-hairline bg-transparent text-[14px] leading-none text-text-dim hover:border-hairline-strong hover:text-text"
        >
          ←
        </button>
        <div className="pt-1 text-[12.5px] leading-[1.45] text-text-dim">{TARGET_QUERIES.gaps}</div>
      </div>

      <div className="mb-[22px] text-[13px] leading-[1.5] text-text-dim">
        Three things — and they are not the same kind of thing.
      </div>

      {GAP_BLOCKS.map((block, i) => (
        <Block
          key={block.ceiling}
          block={block}
          first={i === 0}
          last={i === GAP_BLOCKS.length - 1}
        />
      ))}
    </div>
  )
}
