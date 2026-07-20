// LIVE provenance drawer — renders GET /evidence/{id} (formatted by evidenceToDrawerModel)
// in the demo drawer's visual language, but fully DATA-DRIVEN: one row per backing claim,
// each with its exact source locator (the one-click-to-source non-negotiable), grouped by
// independent look (cluster), plus an explicit "what's missing / when's next coverage" block
// when evidence is insufficient (the insufficient-evidence non-negotiable). NOT AI — this is
// deterministic formatting of the structured response. Demo keeps its own frozen Drawer.tsx;
// this mounts only in LIVE mode (see DrawerHost).
//
// The drawer answers "how do you know that?" — so it must first answer "know WHAT?". A status
// hung over a bare node name ("PAF Base Nur Khan is Probable") grades no proposition an analyst
// can judge. So the header states the assertion under assessment, and every claim row states the
// proposition that claim makes, read straight off its payload (never paraphrased, never generated).

import type { ReactNode } from 'react'
import { useWorkbench } from '@/store/workbench'
import { useEvidence } from '@/api/hooks'
import { evidenceToDrawerModel } from '@/api/adapters'
import type { LiveDrawerModel, LiveClaimRow, LiveDrawerCluster, LiveDrawerSource } from '@/api/adapters'
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

// What each verdict MEANS for the proposition in the header — the analyst reads a status word and
// a claim, and should not have to remember the rubric to join them. Sentence-cased, no arithmetic.
const STATUS_GLOSS: Record<Status, string> = {
  confirmed: 'Independent, credible sources agree — briefable.',
  probable: 'Supported, but thinner than confirmed — lean on it, do not bet on it.',
  possible: 'A weak lead. One low-credibility look.',
  contradicted: 'Credible sources disagree about the same moment — a human call.',
  stale: 'Was supported, but has aged past its shelf life with no fresh confirmation.',
  insufficient: 'Not enough evidence on file to assess this.',
}

/** Status-less edges that are an IDENTITY question rather than a version link (see the verdict block). */
const IDENTITY_LINK_TYPES = new Set(['same-as', 'distinct-from'])

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
const MONO_FAINT = {
  font: '10.5px/1.5 ui-monospace,Menlo,monospace',
  color: 'var(--text-faint)',
} as const

function Kicker({ children }: { children: ReactNode }) {
  return <div style={{ ...KICKER, marginBottom: 8 }}>{children}</div>
}

function Section({ children }: { children: ReactNode }) {
  return <div style={{ padding: '18px 22px', borderTop: '1px solid var(--hairline)' }}>{children}</div>
}

/** The cluster's attribution: WHO said it, by class and reliability grade. A raw `d17b_withheld_gap`
 *  is an internal filename, not a source an analyst can weigh — so the class leads and the id drops
 *  to the technical line beneath it. An id the registry does not know shows as the id alone. */
function SourceLine({ source }: { source: LiveDrawerSource }) {
  const meta = [
    source.grade ? `reliability ${source.grade}` : null,
    source.bias ? `${source.bias} interest` : null,
    source.reportDate ? `dated ${source.reportDate}` : null,
  ].filter(Boolean)
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ font: '12.5px/1.4 ui-sans-serif,system-ui,sans-serif', color: 'var(--text)' }}>
        {source.known ? source.label : source.sourceId}
        {!source.known && (
          <span style={{ color: 'var(--text-faint)', fontSize: 11 }}> · not in the source registry</span>
        )}
      </div>
      {source.known && (
        <div style={{ ...MONO_FAINT, marginTop: 3 }}>
          {[source.sourceId, ...meta].join(' · ')}
        </div>
      )}
      {source.flags.map((flag) => (
        <div
          key={flag}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 7,
            marginTop: 4,
            font: '11px/1.4 ui-sans-serif,system-ui,sans-serif',
            color: 'var(--text-dim)',
          }}
        >
          <span style={{ width: 7, height: 7, borderRadius: 2, background: 'var(--problem)' }} />
          {flag}
        </div>
      ))}
    </div>
  )
}

function ClaimRow({ row, expanded, onToggle, status }: { row: LiveClaimRow; expanded: boolean; onToggle: () => void; status: Status }) {
  return (
    <div style={{ marginBottom: 14 }}>
      {/* the chip carries the kind + the claim's OWN locator, so two claims lifted from one
          document are distinguishable at a glance instead of rendering as the same string */}
      <CitationChip
        label={[row.kindLabel, row.locatorShort].filter(Boolean).join(' · ')}
        status={chipStatusFor(status)}
        dots={row.dots}
        expandable
        expanded={expanded}
        onClick={onToggle}
      />
      {/* WHAT the claim says. Read off its payload — never a paraphrase. When the payload shape is
          one this build cannot phrase, we say nothing here and let the verbatim quote speak. */}
      {row.proposition && (
        <div
          style={{
            font: '13px/1.5 ui-sans-serif,system-ui,sans-serif',
            color: 'var(--text)',
            margin: '8px 0 0 2px',
            textWrap: 'pretty',
          }}
        >
          {row.proposition}
        </div>
      )}
      {row.attrLines.length > 0 && (
        <div
          style={{
            font: '11.5px/1.6 ui-sans-serif,system-ui,sans-serif',
            color: 'var(--text-dim)',
            margin: '5px 0 0 2px',
          }}
        >
          {row.attrLines.map((line) => (
            <div key={line}>{line}</div>
          ))}
        </div>
      )}
      <div style={{ ...MONO_FAINT, margin: '6px 0 0 2px' }}>
        {[row.detail, row.dates.reported ? `reported ${row.dates.reported}` : null, row.locatorShort]
          .filter(Boolean)
          .join(' · ')}
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

function ClusterSection({
  cluster,
  index,
  looks,
  status,
  identityLink,
}: {
  cluster: LiveDrawerCluster
  index: number
  looks: number
  status: Status
  /** T10 — the subject is a `same-as`/`distinct-from`. Its claims are not "also cited" alongside an
   *  assessment; they ARE the assertion, and independent looks are not counted for it at all. */
  identityLink?: boolean
}) {
  const expanded = useWorkbench((s) => s.expanded)
  const toggleChip = useWorkbench((s) => s.toggleChip)
  const axis = cluster.axis
  const axisBits = axis ? [axis.discipline, axis.interest].filter(Boolean) : []
  return (
    <Section>
      <Kicker>
        {cluster.ungrouped
          ? identityLink
            ? 'Who asserts it'
            : 'Also cited · not counted as an independent look'
          : `Independent look ${index + 1} of ${looks}${axisBits.length ? ` · ${axisBits.join(' / ')}` : ''}`}
      </Kicker>
      {cluster.sources.map((source) => (
        <SourceLine key={source.sourceId} source={source} />
      ))}
      <div style={{ ...MONO_FAINT, marginBottom: 12 }}>
        {cluster.rows.length} claim{cluster.rows.length === 1 ? '' : 's'}
        {cluster.ungrouped ? '' : ' from this look'}
      </div>
      {cluster.rows.length === 0 && (
        <div style={{ font: '11px/1.5 ui-sans-serif,system-ui,sans-serif', color: 'var(--text-faint)' }}>
          (no resolvable backing claims)
        </div>
      )}
      {cluster.rows.map((row) => (
        <ClaimRow
          key={row.claimId}
          row={row}
          status={status}
          expanded={expanded === row.claimId}
          onToggle={() => toggleChip(row.claimId)}
        />
      ))}
    </Section>
  )
}

function DrawerBody({ model }: { model: LiveDrawerModel }) {
  const select = useWorkbench((s) => s.select)
  const why = whySentence(model)
  const statusless = model.subject?.statusless === true
  const looks = model.clusters.filter((c) => !c.ungrouped).length

  return (
    <div>
      {/* verdict */}
      <Section>
        <Kicker>Provenance</Kicker>
        {statusless ? (
          // A `supersedes` / `same-as` / `distinct-from` link carries no status BY DESIGN — it is a
          // version or identity link between two already-scored assertions. Rendering its null
          // status as "insufficient evidence" invented an evidence gap that does not exist.
          // T10 — but the two kinds are not the same statement, so they do not get the same sentence:
          // an identity link is an OPEN QUESTION about who two records are (and the claims below are a
          // source's answer to it), where a version link records a change that already happened.
          <div style={{ font: '13px/1.55 ui-sans-serif,system-ui,sans-serif', color: 'var(--text)' }}>
            {IDENTITY_LINK_TYPES.has(model.subject?.edgeType ?? '') ? (
              <>
                This link carries no status of its own — it is a question about identity, not a fact
                about the world. The two records it connects are each scored separately; anything below
                is a source asserting they are one thing, and it is for you to weigh.
              </>
            ) : (
              <>
                This link carries no status of its own — it records a change of state, not a fact about
                the world. The two assertions it connects are each scored separately.
              </>
            )}
          </div>
        ) : (
          <>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
              <StatusSwatch status={model.status} size={16} />
              <span style={{ font: '15px/1.2 ui-sans-serif,system-ui,sans-serif', color: 'var(--text)' }}>
                {STATUS_WORD[model.status]}
              </span>
            </div>
            <div style={{ font: '12.5px/1.5 ui-sans-serif,system-ui,sans-serif', color: 'var(--text-dim)' }}>
              {STATUS_GLOSS[model.status]}
            </div>
          </>
        )}
        {/* the arithmetic, stated so the header can never disagree with the body below it: the
            claim count is the number of rows actually rendered. A status-less link is not scored,
            so it has no independent looks — printing "0 independent looks" would read as a
            shortfall rather than as "this is not the kind of thing looks are counted for". */}
        <div style={{ font: '12px/1.4 ui-sans-serif,system-ui,sans-serif', color: 'var(--text-dim)', marginTop: 10 }}>
          {[
            `${model.sources} source${model.sources === 1 ? '' : 's'}`,
            statusless ? null : `${looks} independent look${looks === 1 ? '' : 's'}`,
            `${model.claimCount} claim${model.claimCount === 1 ? '' : 's'} on file`,
          ]
            .filter(Boolean)
            .join(' · ')}
        </div>
      </Section>

      {/* a relocation, told as a relocation: what moved, from where, to where, and the two
          assertions it is made of — each one click away in its own drawer. */}
      {model.supersession && (() => {
        const s = model.supersession
        const who = s.subjectName ?? 'The recorded occupant'
        const here =
          s.role === 'older'
            ? ' This drawer is the assertion that was overtaken — it is history, not a mistake.'
            : s.role === 'newer'
              ? ' This drawer is the assertion that replaced it.'
              : ''
        return (
          <Section>
            <Kicker>What changed</Kicker>
            <div style={{ font: '13px/1.6 ui-sans-serif,system-ui,sans-serif', color: 'var(--text)', textWrap: 'pretty' }}>
              {who} was based at <strong style={{ fontWeight: 500 }}>{s.fromName}</strong> and is now
              based at <strong style={{ fontWeight: 500 }}>{s.toName}</strong>. {s.fromName} itself is
              unchanged — it was not replaced; the basing there was.{here}
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 12 }}>
              {s.olderEdgeId && s.role !== 'older' && (
                <CitationChip
                  label="the earlier basing (now history)"
                  status="gap"
                  onClick={() => select(s.olderEdgeId!)}
                />
              )}
              {s.newerEdgeId && s.role !== 'newer' && (
                <CitationChip
                  label="the basing that replaced it"
                  status="probable"
                  onClick={() => select(s.newerEdgeId!)}
                />
              )}
            </div>
          </Section>
        )
      })()}

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
      {model.clusters.map((cluster, i) => (
        <ClusterSection
          key={cluster.groupId}
          cluster={cluster}
          index={i}
          looks={looks}
          status={model.status}
          identityLink={IDENTITY_LINK_TYPES.has(model.subject?.edgeType ?? '')}
        />
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

/** Panel width (App.tsx: Rail 240 | Stage flex | Panel 400 | Drawer 560 overlay). */
const PANEL_W = 400

export function LiveDrawer() {
  const drawerOpen = useWorkbench((s) => s.drawerOpen)
  const selected = useWorkbench((s) => s.selected)
  const closeDrawer = useWorkbench((s) => s.closeDrawer)
  const liveView = useWorkbench((s) => s.liveView)
  // T10 — while an adjudication is open in the panel, the drawer slides in BESIDE it instead of on top
  // of it. Checking the evidence must not take the decision off the screen: the three options and the
  // record pair stay visible the whole time the analyst is reading the claims. It still overlays (the
  // stage), never pushes, and everywhere else the drawer is exactly where it has always been.
  const besideCard = useWorkbench((s) => s.panelView === 'card' && s.activeLiveItem !== null)
  const { data, isLoading, isError } = useEvidence(selected, drawerOpen)
  const model = data ? evidenceToDrawerModel(data, liveView) : null
  // `site_rahwali` is a database key, not a claim. The analyst-facing headline is the PROPOSITION
  // under assessment ("«Rahwali airfield» exists, as a basing site"), built from the graph's own
  // names and types — never invented — with the id kept underneath as the technical handle for
  // anyone reading a log or a citation.
  const heading = model?.subject?.headline ?? selected ?? '—'
  const showId = selected != null && heading !== selected

  return (
    <aside
      style={{
        position: 'fixed',
        top: 0,
        right: besideCard ? PANEL_W : 0,
        height: '100vh',
        width: 560,
        // Beside the card it must never eat the panel it is meant to sit next to; the floor keeps it
        // legible if someone runs this far below the 1440×900 the workbench is tuned for.
        maxWidth: besideCard ? `max(320px, calc(100vw - ${PANEL_W + 24}px))` : '92vw',
        background: 'var(--surface)',
        borderLeft: '1px solid var(--hairline-strong)',
        borderRight: besideCard ? '1px solid var(--hairline-strong)' : undefined,
        boxShadow: '-8px 0 24px rgba(0,0,0,0.35)',
        transform: drawerOpen ? 'translateX(0)' : `translateX(calc(100% + ${besideCard ? PANEL_W : 0}px))`,
        // doc 12's drawer budget — 160ms ease-out. It overlays, it never pushes.
        transition: 'transform 160ms ease-out',
        zIndex: 50,
        overflowY: 'auto',
      }}
    >
      {/* header — restates what is being proved, so covering the answer is safe (doc 08).
          Ported from the demo drawer: "Proving" kicker + the claim line + a bordered
          30x30 close control. */}
      {/* no borderBottom here: the first <Section> below already draws that one hairline,
          and two adjacent 1px rules read as a 2px rule that means nothing. */}
      <div style={{ flex: 'none', padding: '20px 24px 16px' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16 }}>
          <div>
            <div style={{ ...KICKER, marginBottom: 7 }}>Proving</div>
            <div style={{ fontSize: 16, lineHeight: 1.35, color: 'var(--text)', textWrap: 'pretty' }}>
              {heading}
            </div>
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
                {model?.subject?.typeLabel ? `${model.subject.typeLabel} · ` : ''}
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
      ) : isError || !model ? (
        <Section>
          <Kicker>Provenance</Kicker>
          <div style={{ font: '12.5px/1.6 ui-sans-serif,system-ui,sans-serif', color: 'var(--text-dim)' }}>
            Insufficient evidence to assess this element — no provenance record was returned.
          </div>
        </Section>
      ) : (
        <DrawerBody model={model} />
      )}
    </aside>
  )
}
