// Tripwires · Indicators & warning (mockup 573-608). Each row names the indicator it
// watches; when one fires it routes to Review (the alert-disposition card), never straight
// to the picture. No buttons here — nothing to decide.
//
// LIVE WINS. In live mode this reads two real sources: the alert feed riding in on GET /view
// (what has FIRED, with its evidence) and the armed catalogue on GET /config/observables
// (what is being WATCHED — the same read the rail's "Watching" count derives from, so the
// panel names exactly what that number counts). The frozen demo tripwires render only when
// there is no live feed to read (demo mode, or live data genuinely absent); a live view that
// carries no alerts renders as "nothing has fired", which is the honest state, never as demo
// content.
//
// The state badge is DATA in both modes: the demo fixture asserts 'armed', the live path
// derives 'fired' / the analyst's disposition from the feed. Nothing here hardcodes it.
import { useWorkbench } from '@/store/workbench'
import { useTripwires } from '@/api/viewmodel'
import { useAnchorCheck, useArmedObservables } from '@/api/hooks'
import { TRIPWIRES, WATCH_INTRO } from '@/demo/scenario'
import type { LiveFiring, LiveTripwire } from '@/api/adapters'
import type { ObservableAnchorProblem, ObservableDef } from '@/api/types'
import { AlertEvidence } from './AlertEvidence'

const LIVE_INTRO =
  'What this view is watching: the armed tripwire catalogue, plus any firing on the current view. Each firing carries the evidence behind the change; deciding one routes through Review, never straight to the picture.'

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

/** Fired-but-undecided is the state that wants the analyst's eye (live border); a decided
 *  firing has left the queue and reads as history (hairline). Status hue is never used here
 *  — this is an alert state, not a truth status. */
function StateBadge({ label, open }: { label: string; open: boolean }) {
  return (
    <span
      className={
        open
          ? 'rounded-[3px] border border-live px-[7px] py-[1px] font-mono text-[10px] text-live'
          : 'rounded-[3px] border border-hairline-strong px-[7px] py-[1px] font-mono text-[10px] text-text-dim'
      }
    >
      {label}
    </span>
  )
}

function Firing({ firing }: { firing: LiveFiring }) {
  return (
    <div className="mt-[10px] border-t border-hairline pt-[10px] first:mt-0 first:border-t-0 first:pt-0">
      {firing.subject && (
        <div className="mb-[6px] font-mono text-[10.5px] text-text-faint">subject · {firing.subject}</div>
      )}

      {firing.changed && (firing.changed.from || firing.changed.to) && (
        <div className="flex flex-wrap items-center gap-[8px] text-[12.5px] text-text">
          <span>{firing.changed.from || '—'}</span>
          <span className="text-text-faint">→</span>
          <span>{firing.changed.to || '—'}</span>
        </div>
      )}

      <div className="mt-[6px] font-mono text-[10.5px] text-text-faint">
        {[
          firing.firedTs ? `fired · ${firing.firedTs}` : null,
          firing.severity ? `severity · ${firing.severity}` : null,
          firing.gate ? `supersession · ${firing.gate}` : null,
          firing.dispositionLabel,
        ]
          .filter(Boolean)
          .join('  ·  ')}
      </div>

      <AlertEvidence provenance={firing.provenance} holdReasons={firing.holdReasons} />
    </div>
  )
}

/** "obs-basing-relocation" → "Basing relocation". The catalogue has no display-name field —
 *  the id is the authored name (config/observables.yaml), so this is a reading, not a label. */
function armedTitle(id: string): string {
  const words = id.replace(/^obs-/, '').replace(/-/g, ' ')
  return words.charAt(0).toUpperCase() + words.slice(1)
}

/** The unresolved-anchor complaint, rendered ON the tripwire it is about (AH-1).
 *
 *  This is the whole point of the fix: a tripwire that is watching nothing must SAY it is watching
 *  nothing, on the card an analyst is already looking at — not in a dict nobody reads. It borrows the
 *  refusal language used everywhere else in this system, because it is the same statement: an absence
 *  here is a coverage failure, never an all-clear. The backend supplies the sentence; nothing is
 *  composed here, so what the API says and what the analyst reads cannot drift. */
function AnchorProblem({ problem }: { problem: ObservableAnchorProblem }) {
  return (
    <div className="mt-[9px] rounded border border-dashed border-live px-[11px] py-[9px]">
      <div className="mb-[4px] font-mono text-[10px] tracking-[0.06em] text-live">
        {problem.watching_nothing
          ? 'WATCHING NOTHING'
          : problem.watched_node_count === null
            ? 'SCOPE LOST — NOW UNSCOPED'
            : 'ANCHOR UNRESOLVED'}
      </div>
      <div className="text-[12px] leading-[1.5] text-text-dim">{problem.warning}</div>
      <div className="mt-[6px] font-mono text-[10.5px] text-text-faint">
        unresolved · {problem.unresolved_anchors.join(', ')}
      </div>
    </div>
  )
}

/** An armed-but-quiet observable from the live catalogue: a definition, not a firing — so it
 *  carries what it watches, never evidence (there is none until it fires). The badge reads "armed"
 *  only when its anchors actually bind; a tripwire watching an empty set is not armed in any sense
 *  an analyst would recognise, and saying "armed" beside it would be the lie this panel exists to
 *  avoid. */
function ArmedObservableCard({ def, problem }: { def: ObservableDef; problem?: ObservableAnchorProblem }) {
  const on = typeof def.trigger?.on === 'string' ? String(def.trigger.on) : null
  const dead = problem?.watching_nothing === true
  return (
    <div className={`rounded border px-[14px] py-[13px] ${problem ? 'border-live' : 'border-hairline'}`}>
      <div className="mb-[7px] flex items-center justify-between gap-3">
        <span className="text-[13px] text-text">{armedTitle(def.observable_id)}</span>
        <StateBadge label={dead ? 'watching nothing' : 'armed'} open={dead} />
      </div>
      <div className="font-mono text-[10.5px] text-text-faint">
        {[`indicator · ${def.observable_id}`, on ? `watches · ${on}` : null, def.severity ? `severity · ${def.severity}` : null]
          .filter(Boolean)
          .join('  ·  ')}
      </div>
      {problem && <AnchorProblem problem={problem} />}
    </div>
  )
}

function LiveTripwireCard({ tripwire, problem }: { tripwire: LiveTripwire; problem?: ObservableAnchorProblem }) {
  const open = tripwire.state === 'fired'
  return (
    <div className={`rounded border px-[14px] py-[13px] ${problem ? 'border-live' : 'border-hairline'}`}>
      <div className="mb-[7px] flex items-center justify-between gap-3">
        <span className="text-[13px] text-text">{tripwire.name}</span>
        <StateBadge label={tripwire.stateLabel} open={open} />
      </div>
      <div className="mb-[2px] font-mono text-[10.5px] text-text-faint">indicator · {tripwire.observableId}</div>
      {/* A tripwire can have fired historically and be blind NOW — the past firing must not read as
          proof that it is still watching. */}
      {problem && <AnchorProblem problem={problem} />}
      {tripwire.firings.map((firing) => (
        <Firing key={firing.key} firing={firing} />
      ))}
    </div>
  )
}

export function WatchView() {
  const backToZero = useWorkbench((s) => s.backToZero)
  const mode = useWorkbench((s) => s.mode)
  const tripwires = useTripwires() // null = no live feed to read → the frozen demo rows
  const armed = useArmedObservables() // null = demo mode, in flight, or the catalogue could not be read
  const anchors = useAnchorCheck() // null = unknown; never treated as "all anchors fine"
  const firedIds = new Set((tripwires ?? []).map((t) => t.observableId))
  const armedQuiet = (armed ?? []).filter((d) => !firedIds.has(d.observable_id))
  const problems = new Map((anchors?.unresolved ?? []).map((p) => [p.observable_id, p]))
  const deadCount = (anchors?.unresolved ?? []).filter((p) => p.watching_nothing).length

  return (
    <div>
      <div className="mb-[6px] flex items-center gap-[10px]">
        <BackButton onClick={backToZero} />
        <span className="text-[10.5px] tracking-[0.06em] text-text-faint">Indicators &amp; warning</span>
      </div>
      <div className="mb-[18px] text-[13px] leading-[1.55] text-text-dim">
        {tripwires ? LIVE_INTRO : WATCH_INTRO}
      </div>

      {/* AH-1 — say it before the list, not only per-card: a panel that opens with "no tripwire has
          fired" while a tripwire is watching nothing has told the analyst the opposite of the truth. */}
      {anchors?.checked === false && (
        <div className="mb-[14px] rounded border border-dashed border-hairline-strong px-[13px] py-[11px] text-[12px] leading-[1.55] text-text-faint">
          Whether these tripwires resolve to real nodes could not be checked{anchors.reason ? ` — ${anchors.reason}` : ''}. Treat the silence below as unverified, not as an all-clear.
        </div>
      )}
      {deadCount > 0 && (
        <div className="mb-[14px] rounded border border-live px-[13px] py-[11px] text-[12.5px] leading-[1.55] text-text">
          {deadCount === 1 ? '1 tripwire is' : `${deadCount} tripwires are`} watching nothing — the
          declared anchors resolve to no node in the current view, so{' '}
          {deadCount === 1 ? 'it cannot' : 'they cannot'} fire. Silence from{' '}
          {deadCount === 1 ? 'it' : 'them'} is not an all-clear.
        </div>
      )}

      <div className="flex flex-col gap-[10px]">
        {tripwires
          ? tripwires.map((t) => (
              <LiveTripwireCard key={t.observableId} tripwire={t} problem={problems.get(t.observableId)} />
            ))
          : TRIPWIRES.map((t) => (
              <div key={t.name} className="rounded border border-hairline px-[14px] py-[13px]">
                <div className="mb-[7px] flex items-center justify-between">
                  <span className="text-[13px] text-text">{t.name}</span>
                  <StateBadge label={t.state} open />
                </div>
                <div className="text-[12.5px] leading-[1.5] text-text-dim">{t.desc}</div>
                <div className="mt-2 font-mono text-[10.5px] text-text-faint">indicator · {t.indicator}</div>
              </div>
            ))}
      </div>

      {tripwires && tripwires.length === 0 && (
        <div className="rounded border border-dashed border-hairline-strong px-[13px] py-[11px] text-[12.5px] leading-[1.55] text-text-dim">
          No tripwire has fired on the current view.
          {deadCount > 0 && (
            <>
              {' '}
              That is not an all-clear: {deadCount === 1 ? 'one of them is' : `${deadCount} of them are`}{' '}
              watching nothing (see below).
            </>
          )}
        </div>
      )}

      {/* LIVE: the armed catalogue (GET /config/observables — the same read behind the rail's
          "Watching" count), minus anything already rendered above as a firing. This is what the
          system is watching while quiet; a definition, so no evidence block until it fires. */}
      {tripwires && armedQuiet.length > 0 && (
        <>
          <div className="mb-[9px] mt-[18px] text-[10.5px] tracking-[0.06em] text-text-faint">
            Armed · watching for
          </div>
          <div className="flex flex-col gap-[10px]">
            {armedQuiet.map((d) => (
              <ArmedObservableCard key={d.observable_id} def={d} problem={problems.get(d.observable_id)} />
            ))}
          </div>
        </>
      )}

      {/* Honesty rule (watchSummary): when the catalogue cannot be read, say so — never render a
          confident "nothing armed". */}
      {tripwires && armed === null && (
        <div className="mt-[14px] rounded border border-dashed border-hairline-strong px-[13px] py-[11px] text-[11px] leading-[1.55] text-text-faint">
          The armed catalogue could not be read — only fired tripwires are listed above.
        </div>
      )}

      {!tripwires && (
        <div className="mt-4 text-[11px] leading-[1.5] text-text-faint">
          Read-only in this build · definitions are user-set, not hardcoded.
        </div>
      )}

      {/* Arming or editing an observable in-app still needs the config WRITE path (filed for the
          API session); the catalogue above is read live from the config store. Demo never shows
          this note. */}
      {mode === 'live' && (
        <div className="mt-[14px] rounded border border-dashed border-hairline-strong px-[13px] py-[11px] text-[11px] leading-[1.55] text-text-faint">
          Definitions are read live from the config store. Arming or editing one in-app needs the
          config write endpoint (filed).
        </div>
      )}
    </div>
  )
}
