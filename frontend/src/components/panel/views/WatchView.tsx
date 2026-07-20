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
import { useArmedObservables } from '@/api/hooks'
import { TRIPWIRES, WATCH_INTRO } from '@/demo/scenario'
import type { LiveFiring, LiveTripwire } from '@/api/adapters'
import type { ObservableDef } from '@/api/types'
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

/** An armed-but-quiet observable from the live catalogue: a definition, not a firing — so it
 *  carries what it watches, never evidence (there is none until it fires). */
function ArmedObservableCard({ def }: { def: ObservableDef }) {
  const on = typeof def.trigger?.on === 'string' ? String(def.trigger.on) : null
  return (
    <div className="rounded border border-hairline px-[14px] py-[13px]">
      <div className="mb-[7px] flex items-center justify-between gap-3">
        <span className="text-[13px] text-text">{armedTitle(def.observable_id)}</span>
        <StateBadge label="armed" open={false} />
      </div>
      <div className="font-mono text-[10.5px] text-text-faint">
        {[`indicator · ${def.observable_id}`, on ? `watches · ${on}` : null, def.severity ? `severity · ${def.severity}` : null]
          .filter(Boolean)
          .join('  ·  ')}
      </div>
    </div>
  )
}

function LiveTripwireCard({ tripwire }: { tripwire: LiveTripwire }) {
  const open = tripwire.state === 'fired'
  return (
    <div className="rounded border border-hairline px-[14px] py-[13px]">
      <div className="mb-[7px] flex items-center justify-between gap-3">
        <span className="text-[13px] text-text">{tripwire.name}</span>
        <StateBadge label={tripwire.stateLabel} open={open} />
      </div>
      <div className="mb-[2px] font-mono text-[10.5px] text-text-faint">indicator · {tripwire.observableId}</div>
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
  const firedIds = new Set((tripwires ?? []).map((t) => t.observableId))
  const armedQuiet = (armed ?? []).filter((d) => !firedIds.has(d.observable_id))

  return (
    <div>
      <div className="mb-[6px] flex items-center gap-[10px]">
        <BackButton onClick={backToZero} />
        <span className="text-[10.5px] tracking-[0.06em] text-text-faint">Indicators &amp; warning</span>
      </div>
      <div className="mb-[18px] text-[13px] leading-[1.55] text-text-dim">
        {tripwires ? LIVE_INTRO : WATCH_INTRO}
      </div>

      <div className="flex flex-col gap-[10px]">
        {tripwires
          ? tripwires.map((t) => <LiveTripwireCard key={t.observableId} tripwire={t} />)
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
              <ArmedObservableCard key={d.observable_id} def={d} />
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
