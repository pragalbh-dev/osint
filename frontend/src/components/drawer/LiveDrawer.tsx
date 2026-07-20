// LIVE provenance drawer — renders GET /evidence/{id} (formatted by evidenceToDrawerModel)
// in the demo drawer's visual language, but fully DATA-DRIVEN: one row per backing claim,
// each with its exact source locator (the one-click-to-source non-negotiable), grouped by
// independent look (cluster), plus an explicit "what's missing / when's next coverage" block
// when evidence is insufficient (the insufficient-evidence non-negotiable). NOT AI — this is
// deterministic formatting of the structured response. Demo keeps its own frozen Drawer.tsx;
// this mounts only in LIVE mode (see DrawerHost).

import type { ReactNode } from 'react'
import { useWorkbench } from '@/store/workbench'
import { useEvidence } from '@/api/hooks'
import { useDisplayName } from '@/api/viewmodel'
import { evidenceToDrawerModel } from '@/api/adapters'
import type { LiveDrawerModel, LiveClaimRow } from '@/api/adapters'
import type { DocRef, Status } from '@/api/types'
import { CitationChip, type ChipStatus } from '@/components/status/CitationChip'
import { StatusSwatch } from '@/components/status/StatusSwatch'

const STATUS_WORD: Record<Status, string> = {
  confirmed: 'Confirmed',
  probable: 'Probable',
  possible: 'Possible',
  contradicted: 'Contradicted',
  stale: 'Stale',
  insufficient: 'Insufficient evidence',
}

function chipStatusFor(status: Status): ChipStatus {
  if (status === 'confirmed') return 'confirmed'
  if (status === 'contradicted' || status === 'insufficient') return 'gap'
  return 'probable'
}

// One claim's exact source pointer, rendered as a precise locator string (file + page/line/
// row/frame/region/span). The locator is the ADDRESS of the evidence; the verbatim span the
// backend reads back from that address (see chanakya.api.quotes) is the evidence itself, and
// leads the block. Deep-linking into a served source viewer is a follow-up once a doc route exists.
function docRefLabel(ref: DocRef): string {
  const parts: string[] = [ref.file]
  if (ref.page != null) parts.push(`p.${ref.page}`)
  if (ref.line != null) parts.push(`L${ref.line}`)
  if (ref.row != null) parts.push(`row ${ref.row}`)
  if (ref.frame != null) parts.push(`frame ${ref.frame}`)
  if (ref.region) parts.push(ref.region)
  if (ref.span) parts.push(`${ref.span[0]}–${ref.span[1]}`)
  return parts.join(' · ')
}

function whySentence(m: LiveDrawerModel): string {
  const s = m.sufficiency
  if (!s || s.satisfied) return ''
  if (s.ceiling === 'never-observable')
    return 'Not directly observable from open sources — probable is the ceiling here.'
  const bits: string[] = []
  if (s.missingSlots.length) bits.push(`still missing ${s.missingSlots.join(', ')}`)
  if (m.looks < 2) bits.push('only one independent look so far')
  if (!bits.length) return 'Not yet enough corroboration to confirm.'
  return `Held at ${STATUS_WORD[m.status].toLowerCase()} — ${bits.join('; ')}.`
}

// The demo drawer's KICKER, verbatim (Drawer.tsx) — 10.5px sans, 0.06em tracking,
// SENTENCE CASE. The copy deck is explicit: "Sentence case. Always. No ALL CAPS."
// A mono/uppercase variant here was a second visual language for the same object.
const KICKER = { fontSize: 10.5, color: 'var(--text-faint)', letterSpacing: '0.06em' } as const

function Kicker({ children }: { children: ReactNode }) {
  return <div style={{ ...KICKER, marginBottom: 8 }}>{children}</div>
}

function Section({ children }: { children: ReactNode }) {
  return <div style={{ padding: '18px 22px', borderTop: '1px solid var(--hairline)' }}>{children}</div>
}

function ClaimRow({ row, expanded, onToggle, status }: { row: LiveClaimRow; expanded: boolean; onToggle: () => void; status: Status }) {
  return (
    <div style={{ marginBottom: 12 }}>
      <CitationChip
        label={row.sourceId}
        status={chipStatusFor(status)}
        dots={row.dots}
        expandable
        expanded={expanded}
        onClick={onToggle}
      />
      <div style={{ font: '11px/1.5 ui-sans-serif,system-ui,sans-serif', color: 'var(--text-dim)', margin: '6px 0 0 2px' }}>
        {row.detail}
      </div>
      {expanded && (
        <div
          style={{
            marginTop: 8,
            padding: '10px 12px',
            border: '1px solid var(--hairline)',
            borderRadius: 4, // --radius-node; 6 was off-system
            background: 'var(--bg)',
            font: '10.5px/1.6 ui-monospace,Menlo,monospace',
            color: 'var(--text-dim)',
          }}
        >
          {row.dates.event && <div>event · {row.dates.event}</div>}
          {row.dates.reported && <div>reported · {row.dates.reported}</div>}
          {row.dates.ingested && <div>ingested · {row.dates.ingested}</div>}
          {/* The cited source, quote first. Same order the demo drawer uses: dates, hairline,
              then the words. The locator drops underneath as technical detail — an analyst
              audits the claim by READING it, not by reading a byte range. */}
          {row.docRefs.map((ref, i) => {
            const quote = row.quotes[i] ?? ''
            return (
              <div
                key={i}
                style={{ marginTop: 10, paddingTop: 10, borderTop: '1px solid var(--hairline)' }}
              >
                {quote ? (
                  <div
                    style={{
                      font: '12px/1.5 ui-sans-serif,system-ui,sans-serif',
                      color: 'var(--text)',
                      textWrap: 'pretty',
                    }}
                  >
                    “{quote}”
                  </div>
                ) : (
                  // No quote is never papered over with a paraphrase — say the span could not
                  // be read and leave the locator as the only claim being made.
                  <div style={{ color: 'var(--text-faint)' }}>
                    (the cited span could not be read back from this document)
                  </div>
                )}
                <div style={{ marginTop: 6, color: 'var(--text-faint)' }} title="exact source locator">
                  → {docRefLabel(ref)}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

function DrawerBody({ model }: { model: LiveDrawerModel }) {
  const expanded = useWorkbench((s) => s.expanded)
  const toggleChip = useWorkbench((s) => s.toggleChip)
  const why = whySentence(model)

  return (
    <div>
      {/* verdict */}
      <Section>
        <Kicker>Provenance</Kicker>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
          <StatusSwatch status={model.status} size={16} />
          <span style={{ font: '15px/1.2 ui-sans-serif,system-ui,sans-serif', color: 'var(--text)' }}>
            {STATUS_WORD[model.status]}
          </span>
        </div>
        {/* the ref itself now leads the header block above — not repeated here */}
        <div style={{ font: '12px/1.4 ui-sans-serif,system-ui,sans-serif', color: 'var(--text-dim)', marginTop: 10 }}>
          {model.sources} source{model.sources === 1 ? '' : 's'} · {model.looks} independent look
          {model.looks === 1 ? '' : 's'}
        </div>
      </Section>

      {/* the sufficiency check — the pack's own copy ("To raise this", doc 09 §hierarchy
          item 7). It names the next action and its date rather than the shortfall. */}
      {why && (
        <Section>
          <Kicker>To raise this</Kicker>
          <div style={{ font: '12.5px/1.6 ui-sans-serif,system-ui,sans-serif', color: 'var(--text)' }}>{why}</div>
          {model.sufficiency?.nextCoverageDue && (
            <div style={{ font: '11px/1.4 ui-monospace,Menlo,monospace', color: 'var(--text-faint)', marginTop: 8 }}>
              next coverage due · {model.sufficiency.nextCoverageDue}
            </div>
          )}
        </Section>
      )}

      {/* the independent looks + their claims */}
      {model.clusters.map((cluster) => (
        <Section key={cluster.groupId}>
          <Kicker>
            Independent look
            {cluster.axis &&
              (cluster.axis.discipline || cluster.axis.origin) &&
              ` · ${[cluster.axis.discipline, cluster.axis.origin].filter(Boolean).join(' / ')}`}
          </Kicker>
          {cluster.rows.length === 0 && (
            <div style={{ font: '11px/1.5 ui-sans-serif,system-ui,sans-serif', color: 'var(--text-faint)' }}>
              (no resolvable backing claims)
            </div>
          )}
          {cluster.rows.map((row) => (
            <ClaimRow
              key={row.claimId}
              row={row}
              status={model.status}
              expanded={expanded === row.claimId}
              onToggle={() => toggleChip(row.claimId)}
            />
          ))}
        </Section>
      ))}

      {/* integrity + opposing evidence */}
      {(model.integrityFlags.length > 0 || model.opposingCount > 0) && (
        <Section>
          <Kicker>Caveats</Kicker>
          {model.integrityFlags.map((flag) => (
            <div
              key={flag}
              style={{ display: 'flex', alignItems: 'center', gap: 8, font: '11.5px/1.5 ui-sans-serif,system-ui,sans-serif', color: 'var(--text-dim)', marginBottom: 4 }}
            >
              <span style={{ width: 7, height: 7, borderRadius: 2, background: 'var(--problem)' }} />
              integrity flag · {flag}
            </div>
          ))}
          {model.opposingCount > 0 && (
            <div style={{ font: '11.5px/1.5 ui-sans-serif,system-ui,sans-serif', color: 'var(--text-dim)' }}>
              {model.opposingCount} opposing claim{model.opposingCount === 1 ? '' : 's'} on file
            </div>
          )}
        </Section>
      )}
    </div>
  )
}

export function LiveDrawer() {
  const drawerOpen = useWorkbench((s) => s.drawerOpen)
  const selected = useWorkbench((s) => s.selected)
  const closeDrawer = useWorkbench((s) => s.closeDrawer)
  const displayName = useDisplayName()
  const { data, isLoading, isError } = useEvidence(selected, drawerOpen)
  // `site_rahwali` is a database key, not a name. The analyst-facing headline is the node's OWN
  // name (never a paraphrase, never invented — an unnamed node falls back to its id), with the id
  // kept underneath as the technical handle for anyone reading a log or a citation.
  const heading = selected ? displayName(selected) : '—'
  const showId = selected != null && heading !== selected

  return (
    <aside
      style={{
        position: 'fixed',
        top: 0,
        right: 0,
        height: '100vh',
        width: 560,
        maxWidth: '92vw',
        background: 'var(--surface)',
        borderLeft: '1px solid var(--hairline-strong)',
        boxShadow: '-8px 0 24px rgba(0,0,0,0.35)',
        transform: drawerOpen ? 'translateX(0)' : 'translateX(100%)',
        // doc 12's drawer budget — 160ms ease-out. It overlays, it never pushes.
        transition: 'transform 160ms ease-out',
        zIndex: 50,
        overflowY: 'auto',
      }}
    >
      {/* header — restates what is being proved, so covering the answer is safe (doc 08).
          Ported from the demo drawer: "Proving" kicker + the claim line + a bordered
          30x30 close control. Live has no prose claim, so the element ref IS the claim. */}
      {/* no borderBottom here: the first <Section> below already draws that one hairline,
          and two adjacent 1px rules read as a 2px rule that means nothing. */}
      <div style={{ flex: 'none', padding: '20px 24px 16px' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16 }}>
          <div>
            <div style={{ ...KICKER, marginBottom: 7 }}>Proving</div>
            <div style={{ fontSize: 16, lineHeight: 1.35, color: 'var(--text)' }}>{heading}</div>
            {showId && (
              <div
                style={{
                  fontFamily: 'var(--mono)',
                  fontSize: 10.5,
                  lineHeight: 1.4,
                  color: 'var(--text-faint)',
                  marginTop: 5,
                }}
              >
                {selected}
              </div>
            )}
          </div>
          <button
            type="button"
            onClick={closeDrawer}
            title="Dismiss"
            style={{
              flex: 'none',
              width: 30,
              height: 30,
              border: '1px solid var(--hairline)',
              borderRadius: 4,
              background: 'transparent',
              color: 'var(--text-dim)',
              fontSize: 15,
              cursor: 'pointer',
              lineHeight: 1,
            }}
            aria-label="Close provenance drawer"
          >
            ✕
          </button>
        </div>
      </div>
      {!selected ? null : isLoading ? (
        <Section>
          <div style={{ font: '12px/1.5 ui-sans-serif,system-ui,sans-serif', color: 'var(--text-faint)' }}>Loading provenance…</div>
        </Section>
      ) : isError || !data ? (
        <Section>
          <Kicker>Provenance</Kicker>
          <div style={{ font: '12.5px/1.6 ui-sans-serif,system-ui,sans-serif', color: 'var(--text-dim)' }}>
            Insufficient evidence to assess this element — no provenance record was returned.
          </div>
        </Section>
      ) : (
        <DrawerBody model={evidenceToDrawerModel(data)} />
      )}
    </aside>
  )
}
