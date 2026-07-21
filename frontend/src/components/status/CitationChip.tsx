// Citation chip — a citation's job is "does this support a briefable claim?", so it
// carries confirmed-vs-not only (solid vs dashed border). Optionally: a leading tier
// dot-ladder, an integrity mark, an expand arrow (opens the L2 date breakdown in place),
// or the dashed Known-Gap variant. One of the "four doors" into the provenance drawer.

import clsx from 'clsx'
import { TierDots } from './TierDots'

export type ChipStatus = 'confirmed' | 'probable' | 'gap'

interface Props {
  label: string
  status?: ChipStatus
  dots?: number
  dotsOf?: number
  struck?: boolean
  integrity?: boolean
  expandable?: boolean
  expanded?: boolean
  onClick?: () => void
  /** native tooltip — the hover hint that a chip is a door into its source (e.g. "Show the claim
   *  this source made"). Undefined leaves the chip exactly as it was, so the frozen demo is untouched. */
  title?: string
  className?: string
}

function border(status: ChipStatus): string {
  if (status === 'confirmed') return '2px solid var(--live)'
  if (status === 'gap') return '1.5px dashed rgba(var(--history-rgb),0.9)'
  return '1.5px dashed var(--live)' // probable
}

export function CitationChip({
  label,
  status = 'confirmed',
  dots,
  dotsOf = 4,
  struck,
  integrity,
  expandable,
  expanded,
  onClick,
  title,
  className,
}: Props) {
  const interactive = !!onClick
  return (
    <button
      type={interactive ? 'button' : undefined}
      onClick={onClick}
      disabled={!interactive}
      title={title}
      className={clsx(
        'inline-flex items-center gap-[9px] font-sans text-text-dim',
        interactive && 'cursor-pointer',
        className,
      )}
      style={{
        height: 'var(--chip-h)',
        padding: '0 11px',
        borderRadius: status === 'gap' ? '4px' : 'var(--radius-chip)',
        border: border(status),
        background: 'transparent',
        fontSize: 12,
        lineHeight: 1,
      }}
    >
      {typeof dots === 'number' && <TierDots n={dots} of={dotsOf} struck={struck} />}
      <span>{label}</span>
      {integrity && (
        <span
          title="integrity flag"
          style={{ width: 7, height: 7, borderRadius: 2, background: 'var(--problem)' }}
        />
      )}
      {expandable && <span style={{ color: 'var(--text-faint)' }}>{expanded ? '▾' : '▸'}</span>}
    </button>
  )
}
