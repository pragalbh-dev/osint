// Source-tier dot ladder — official(4) > analysis(3) > named-social(2) > anonymous(1).
// Chips + drawer ONLY, never a map pin (that's what collapses 60 states to 15).
// `struck` = tier discounted (same-side / too-clean / adversary-denial): "four dots,
// and we're not counting them." NOT dimming — dimming would read as a lower tier.

export function TierDots({ n, of = 4, struck = false }: { n: number; of?: number; struck?: boolean }) {
  return (
    <span className="relative inline-flex items-center" style={{ gap: 'var(--tier-dot-gap)' }}>
      {Array.from({ length: of }).map((_, i) => (
        <i
          key={i}
          style={{
            width: 'var(--tier-dot-size)',
            height: 'var(--tier-dot-size)',
            borderRadius: '50%',
            background: i < n ? 'var(--tier-dot-on)' : 'var(--tier-dot-off)',
          }}
        />
      ))}
      {struck && (
        <span
          aria-hidden
          style={{
            position: 'absolute',
            left: 0,
            right: 0,
            top: '50%',
            borderTop: 'var(--tier-strike-width) solid var(--tier-strike-color)',
          }}
        />
      )}
    </span>
  )
}
