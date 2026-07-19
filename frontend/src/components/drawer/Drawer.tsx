// Provenance drawer (design doc 09) — "how do you know that?" answered in two levels.
// A 560px overlay pinned top-right, full height; slides in over the panel, never pushes.
// It restates the claim so covering the answer is safe, then renders the RAHWALI
// provenance in its richest state (before d19): the lid, the collapse, the integrity
// flag, and the sufficiency check all live at once. Once the discipline-independent
// second look (d19) lands, it collapses to plain "confirmed".
//
// HARD RULES honoured here:
//   · dashed = provisional / solid = settled; status by border + fill, never hue.
//   · no arithmetic / percentages / scores — the binding constraint is ONE sentence.
//   · the three dates ARE the fake — we SHOW them and let the analyst subtract;
//     the system never says "suspicious". The evidence convicts, not the model.
//   · exactly two levels of depth: drawer = L1, a chip expands IN PLACE to L2
//     (three dates + the exact line). One chip expanded at a time. No third level.

import { DRAWER } from '@/demo/scenario'
import { useWorkbench, selRahwaliConfirmed, selSources, selLooks } from '@/store/workbench'
import { CitationChip } from '@/components/status/CitationChip'
import { StatusSwatch } from '@/components/status/StatusSwatch'

// ── shared bits ─────────────────────────────────────────────────────────────

const KICKER = { fontSize: 10.5, color: 'var(--text-faint)', letterSpacing: '0.06em' } as const
const SECTION = { marginTop: 24, paddingTop: 20, borderTop: '1px solid var(--hairline)' } as const

/** L2 — the in-place breakdown a chip expands to: the three dates + the exact line.
 *  The two numbers do the work; the caption states the subtraction, never a verdict. */
function ExpandBox({
  dates,
  dateNote,
  dateNoteStyle,
  quote,
}: {
  dates: { event: string; reported: string; ingested: string }
  dateNote: string
  dateNoteStyle: React.CSSProperties
  quote: string
}) {
  return (
    <div
      style={{
        marginTop: 11,
        padding: '13px 15px',
        background: 'var(--surface-raised)',
        border: '1px solid var(--hairline)',
        borderRadius: 4,
      }}
    >
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'auto 1fr',
          gap: '5px 16px',
          fontFamily: 'var(--mono)',
          fontSize: 12,
        }}
      >
        <span style={{ color: 'var(--text-faint)' }}>Event</span>
        <span style={{ color: 'var(--text)' }}>{dates.event}</span>
        <span style={{ color: 'var(--text-faint)' }}>Reported</span>
        <span style={{ color: 'var(--text)' }}>{dates.reported}</span>
        <span style={{ color: 'var(--text-faint)' }}>Ingested</span>
        <span style={{ color: 'var(--text)' }}>{dates.ingested}</span>
      </div>
      <div style={{ marginTop: 10, lineHeight: 1.5, ...dateNoteStyle }}>{dateNote}</div>
      <div
        style={{
          marginTop: 10,
          paddingTop: 10,
          borderTop: '1px solid var(--hairline)',
          fontSize: 12,
          color: 'var(--text)',
          lineHeight: 1.5,
        }}
      >
        {quote}
      </div>
    </div>
  )
}

// ── the drawer ──────────────────────────────────────────────────────────────

export function Drawer() {
  const drawerOpen = useWorkbench((s) => s.drawerOpen)
  const expanded = useWorkbench((s) => s.expanded)
  const d20 = useWorkbench((s) => s.ingested.d20)
  const confirmed = useWorkbench(selRahwaliConfirmed)
  const sources = useWorkbench(selSources)
  const looks = useWorkbench(selLooks)
  const closeDrawer = useWorkbench((s) => s.closeDrawer)
  const toggleChip = useWorkbench((s) => s.toggleChip)

  const showProbable = !confirmed
  const noop = (e: React.MouseEvent) => e.preventDefault()

  // headline — "N sources · M independent look(s)"; the looks half in --live.
  const sourcesText = `${sources} sources`
  const looksText = `${looks} independent look${looks === 1 ? '' : 's'}`

  // "To raise this" — the closing clause ("A decoy array can't radiate.") drops to
  // text-dim, so the sufficiency test leads and the aphorism trails, per the mockup.
  const [raiseHead, ...raiseRest] = DRAWER.probable.toRaise.split('A decoy array')
  const raiseDim = raiseRest.length ? 'A decoy array' + raiseRest.join('A decoy array') : ''

  return (
    <aside
      aria-hidden={!drawerOpen}
      className="absolute inset-y-0 right-0 flex w-[560px] flex-col border-l border-hairline-strong bg-surface"
      style={{
        zIndex: 50,
        transform: drawerOpen ? 'translateX(0)' : 'translateX(100%)',
        transition: 'transform 160ms ease-out',
        boxShadow: drawerOpen ? '-24px 0 60px rgba(0,0,0,0.45)' : 'none',
      }}
    >
      {/* header — restates the claim, so covering the answer is safe */}
      <div style={{ flex: 'none', padding: '20px 24px 16px', borderBottom: '1px solid var(--hairline)' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16 }}>
          <div>
            <div style={{ ...KICKER, marginBottom: 7 }}>Proving</div>
            <div style={{ fontSize: 16, lineHeight: 1.35, color: 'var(--text)' }}>{DRAWER.proving}</div>
          </div>
          <button
            type="button"
            onClick={closeDrawer}
            title="Dismiss"
            className="text-text-dim hover:border-hairline-strong hover:text-text"
            style={{
              flex: 'none',
              width: 30,
              height: 30,
              border: '1px solid var(--hairline)',
              borderRadius: 4,
              background: 'transparent',
              fontSize: 15,
              cursor: 'pointer',
              lineHeight: 1,
            }}
          >
            ✕
          </button>
        </div>
      </div>

      {/* body */}
      <div style={{ flex: 1, overflow: 'auto', padding: '20px 24px 28px' }}>
        {/* 1 · verdict + lid */}
        <div>
          {showProbable && (
            <>
              <div style={{ borderTop: '2px dashed rgba(var(--history-rgb),0.85)' }} />
              <div style={{ fontSize: 11, color: 'var(--text-faint)', margin: '9px 0 12px' }}>
                {DRAWER.probable.capLine}
              </div>
            </>
          )}
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, paddingTop: 4 }}>
            <StatusSwatch status={confirmed ? 'confirmed' : 'probable'} size={16} />
            <span style={{ fontSize: 21, color: 'var(--text)', letterSpacing: '-0.01em' }}>
              {confirmed ? DRAWER.confirmed.verdictWord : DRAWER.probable.verdictWord}
            </span>
            <span className="font-mono" style={{ fontSize: 12, color: 'var(--text-dim)' }}>
              {DRAWER.asOf}
            </span>
          </div>
        </div>

        {/* 2 · why — the binding constraint, one sentence (only while capped) */}
        {showProbable && (
          <div style={{ marginTop: 22 }}>
            <div style={{ ...KICKER, marginBottom: 8 }}>Why</div>
            <div style={{ fontSize: 16.5, lineHeight: 1.4, color: 'var(--text)', textWrap: 'pretty' }}>
              {DRAWER.probable.why}
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-faint)', marginTop: 8, lineHeight: 1.5 }}>
              {DRAWER.probable.whySecond}
            </div>
            <a
              href="#"
              onClick={noop}
              style={{ display: 'inline-block', marginTop: 10, fontSize: 11.5, color: 'var(--text-faint)' }}
            >
              Show the working
            </a>
          </div>
        )}

        {/* 3 · headline — N sources · M independent look(s) */}
        <div style={SECTION}>
          <div style={{ fontSize: 22, letterSpacing: '-0.01em', color: 'var(--text)' }}>
            {sourcesText} · <span style={{ color: 'var(--live)' }}>{looksText}</span>
          </div>
        </div>

        {/* 4 · Look 1 — overhead imagery */}
        <div style={{ marginTop: 22 }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'baseline',
              justifyContent: 'space-between',
              marginBottom: 11,
            }}
          >
            <span style={{ fontSize: 12.5, color: 'var(--text)' }}>{DRAWER.look1.title}</span>
            <span className="font-mono" style={{ fontSize: 10.5, color: 'var(--text-faint)' }}>
              {DRAWER.look1.meta}
            </span>
          </div>
          <CitationChip
            label={DRAWER.look1.chip}
            status="probable"
            dots={DRAWER.look1.chipDots}
            expandable
            expanded={expanded === 'd18'}
            onClick={() => toggleChip('d18')}
          />
          {expanded === 'd18' && (
            <ExpandBox
              dates={DRAWER.look1.dates}
              dateNote={DRAWER.look1.dateNote}
              dateNoteStyle={{ fontSize: 12, color: 'var(--text-dim)' }}
              quote={DRAWER.look1.quote}
            />
          )}
          <div style={{ marginTop: 11, fontSize: 12.5, color: 'var(--text-dim)', lineHeight: 1.55 }}>
            {DRAWER.look1.body}
          </div>
        </div>

        {/* 5 · Social imagery — contributes nothing, shown in full so you can SEE it adds nothing */}
        <div style={SECTION}>
          <div
            style={{
              display: 'flex',
              alignItems: 'baseline',
              justifyContent: 'space-between',
              marginBottom: 11,
            }}
          >
            <span style={{ fontSize: 12.5, color: 'var(--text)' }}>{DRAWER.social.title}</span>
            <span style={{ fontSize: 10.5, color: 'var(--text-faint)' }}>{DRAWER.social.meta}</span>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center' }}>
            <CitationChip
              label={DRAWER.social.chip}
              status="probable"
              dots={DRAWER.social.chipDots}
              integrity
              expandable
              expanded={expanded === 'd11'}
              onClick={() => toggleChip('d11')}
            />
            {DRAWER.social.reshareChips.map((label) => (
              <span
                key={label}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  height: 'var(--chip-h)',
                  padding: '0 11px',
                  borderRadius: 3,
                  border: '1px solid var(--hairline-strong)',
                  color: 'var(--text-faint)',
                  fontSize: 12,
                }}
              >
                {label}
              </span>
            ))}
          </div>
          {expanded === 'd11' && (
            <ExpandBox
              dates={DRAWER.social.dates}
              dateNote={DRAWER.social.dateNote}
              dateNoteStyle={{ fontSize: 13, color: 'var(--text)' }}
              quote={DRAWER.social.quote}
            />
          )}
          <div style={{ marginTop: 11, fontSize: 12.5, color: 'var(--text-dim)', lineHeight: 1.55 }}>
            {DRAWER.social.collapse}
          </div>
          <div style={{ marginTop: 10, display: 'flex', gap: 9, alignItems: 'flex-start' }}>
            <span
              style={{
                flex: 'none',
                width: 8,
                height: 8,
                borderRadius: 2,
                background: 'var(--problem)',
                marginTop: 5,
              }}
            />
            <span style={{ fontSize: 12.5, color: 'var(--text)', lineHeight: 1.55 }}>
              {DRAWER.social.integrity}
            </span>
          </div>
        </div>

        {/* 6 · confirmed — the second, discipline-independent look that lifted the cap */}
        {confirmed && (
          <>
            <div style={SECTION}>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'baseline',
                  justifyContent: 'space-between',
                  marginBottom: 11,
                }}
              >
                <span style={{ fontSize: 12.5, color: 'var(--text)' }}>{DRAWER.confirmed.look2Title}</span>
                <span className="font-mono" style={{ fontSize: 10.5, color: 'var(--text-faint)' }}>
                  {DRAWER.confirmed.look2Meta}
                </span>
              </div>
              <CitationChip label={DRAWER.confirmed.look2Chip} status="probable" dots={1} />
              <div
                style={{
                  marginTop: 11,
                  fontSize: 12.5,
                  color: 'var(--text-dim)',
                  lineHeight: 1.55,
                  textWrap: 'pretty',
                }}
              >
                {DRAWER.confirmed.look2Body}
              </div>
            </div>
            <div style={SECTION}>
              <div style={{ ...KICKER, marginBottom: 9 }}>Settled</div>
              <div style={{ fontSize: 14.5, lineHeight: 1.5, color: 'var(--text)', textWrap: 'pretty' }}>
                {DRAWER.confirmed.settled}
              </div>
            </div>
          </>
        )}

        {/* 7 · to raise this — the sufficiency check (only while capped) */}
        {showProbable && (
          <div style={SECTION}>
            <div style={{ ...KICKER, marginBottom: 9 }}>To raise this</div>
            <div style={{ fontSize: 14.5, lineHeight: 1.5, color: 'var(--text)', textWrap: 'pretty' }}>
              {raiseHead}
              {raiseDim && <span style={{ color: 'var(--text-dim)' }}>{raiseDim}</span>}
            </div>
          </div>
        )}

        {/* 8 · since then — the number moves, the picture doesn't (beat 8's stillness) */}
        {d20 && (
          <div
            style={{
              marginTop: 22,
              padding: '13px 15px',
              border: '1px solid var(--hairline-strong)',
              borderRadius: 4,
              background: 'var(--surface-raised)',
            }}
          >
            <div style={{ ...KICKER, marginBottom: 8 }}>Since then</div>
            <div style={{ fontSize: 13, color: 'var(--text)', lineHeight: 1.55, textWrap: 'pretty' }}>
              {DRAWER.spoofNote}
            </div>
          </div>
        )}

        {/* 9 · override — quiet escape hatch; starts a decision, doesn't end one */}
        <div style={{ marginTop: 24, paddingTop: 18, borderTop: '1px solid var(--hairline)' }}>
          <a href="#" onClick={noop} style={{ fontSize: 12.5, color: 'var(--text-dim)' }}>
            Override this verdict →
          </a>
        </div>
      </div>
    </aside>
  )
}
