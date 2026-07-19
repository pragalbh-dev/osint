// The status swatch — one grammar, every state. A small square (verdicts, legend) or
// circle (pin core) that composes status (border style) × freshness (fill value) ×
// cap (the lid) × integrity (corner triangle) × Known-Gap (hollow / hatched wall).
// Hue is never load-bearing. Used inline in the drawer/cred verdicts and any legend.

import clsx from 'clsx'
import type { Ceiling } from '@/demo/scenario'
import { fillVar, opacityFor, statusBorder, type Freshness, type StatusLike } from './util'

interface Props {
  status: StatusLike
  freshness?: Freshness
  size?: number
  shape?: 'rect' | 'circle'
  cap?: 'liftable' | 'welded'
  integrity?: boolean
  gap?: boolean
  ceiling?: Ceiling
  className?: string
}

const HATCH =
  'repeating-linear-gradient(45deg, transparent, transparent 2px, rgba(var(--history-rgb),0.5) 2px, rgba(var(--history-rgb),0.5) 3px)'

export function StatusSwatch({
  status,
  freshness = 'fresh',
  size = 16,
  shape = 'rect',
  cap,
  integrity,
  gap,
  ceiling,
  className,
}: Props) {
  const isNever = gap && ceiling === 'never-observable'
  const border = gap
    ? isNever
      ? 'var(--gap-border-never)'
      : 'var(--gap-border-probable-max)'
    : statusBorder(status)
  const background = gap ? (isNever ? HATCH : 'var(--fill-none)') : fillVar(freshness)
  const radius = shape === 'circle' ? '50%' : 'var(--radius-node)'

  return (
    <span
      className={clsx('relative inline-block align-middle', className)}
      style={{
        width: size,
        height: size,
        border,
        background,
        borderRadius: radius,
        opacity: gap ? 1 : opacityFor(freshness),
      }}
    >
      {/* the lid — dashed = liftable, solid = welded */}
      {cap && (
        <span
          aria-hidden
          style={{
            position: 'absolute',
            left: 0,
            right: 0,
            top: 'calc(-1 * var(--lid-offset))',
            borderTop:
              cap === 'welded'
                ? 'var(--lid-welded-width) solid var(--lid-welded-color)'
                : 'var(--lid-liftable-width) dashed var(--lid-liftable-color)',
          }}
        />
      )}
      {/* integrity — corner triangle, shares coral with contradicted */}
      {integrity && (
        <span
          aria-hidden
          style={{
            position: 'absolute',
            top: 0,
            right: 0,
            width: 0,
            height: 0,
            borderTop: 'var(--integrity-mark-size) solid var(--integrity-mark-color)',
            borderLeft: 'var(--integrity-mark-size) solid transparent',
            borderTopRightRadius: radius,
          }}
        />
      )}
    </span>
  )
}
