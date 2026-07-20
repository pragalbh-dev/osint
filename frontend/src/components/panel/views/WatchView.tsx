// Tripwires · Indicators & warning (mockup 573-608). Each row names the indicator it
// watches; when one fires it routes to Review (the alert-disposition card), never straight
// to the picture. No buttons here — nothing to decide.
//
// LIVE WINS. In live mode this reads the real alert feed that rides in on GET /view and
// renders actual fired state with its evidence — a tripwire, not a picture of one. The
// frozen demo tripwires render only when there is no live feed to read (demo mode, or live
// data genuinely absent); a live view that carries no alerts renders as "nothing has
// fired", which is the honest state, never as demo content.
//
// The state badge is DATA in both modes: the demo fixture asserts 'armed', the live path
// derives 'fired' / the analyst's disposition from the feed. Nothing here hardcodes it.
import { useWorkbench } from '@/store/workbench'
import { useTripwires } from '@/api/viewmodel'
import { TRIPWIRES, WATCH_INTRO } from '@/demo/scenario'
import type { LiveFiring, LiveTripwire } from '@/api/adapters'
import { AlertEvidence } from './AlertEvidence'

const LIVE_INTRO =
  'Fired tripwires on the current view. Each firing carries the evidence behind the change; deciding one routes through Review, never straight to the picture.'

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

      {!tripwires && (
        <div className="mt-4 text-[11px] leading-[1.5] text-text-faint">
          Read-only in this build · definitions are user-set, not hardcoded.
        </div>
      )}

      {/* LIVE: the alert feed tells us what has FIRED; there is no read endpoint for the
          observable catalogue, so an armed-but-quiet tripwire cannot be listed without
          asserting something this view does not say. Name the gap rather than fill it.
          Defining/arming one live additionally needs a config read-modify-write endpoint
          (filed for the API session). Demo never shows this note. */}
      {mode === 'live' && (
        <div className="mt-[14px] rounded border border-dashed border-hairline-strong px-[13px] py-[11px] text-[11px] leading-[1.55] text-text-faint">
          Only tripwires that have fired can be listed — the armed catalogue has no read
          endpoint yet, and arming a new one live needs a config read/modify/write endpoint (filed).
        </div>
      )}
    </div>
  )
}
