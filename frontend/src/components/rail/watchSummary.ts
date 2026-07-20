// The rail's "Watching" row, derived — two independent truths, never one number standing in for
// both. Pure (no React, no fetch) so the honesty rules below are unit-testable.
//
// The bug this exists to prevent: the row used to derive its count from the ALERT FEED, i.e. from
// what has FIRED. On a cold boot nothing has fired, so a system with three armed tripwires rendered
// "Watching 0 — none fired", which a reviewer reads as "nothing is being monitored". That is false,
// and on a monitoring system it is the worst possible false statement to make about yourself.
//
// So there are two numbers, from two different sources:
//   * ARMED  — the observable catalogue (GET /config/observables, the live config store). What the
//              system is watching for. Non-zero from boot.
//   * FIRED  — the alert feed on GET /view. What has actually tripped. Zero at boot, by design.
//
// And one rule for the third case: when the catalogue cannot be read, say so. Never substitute the
// fired count for the armed count, and never print a confident 0 — an underclaim is as dishonest as
// an overclaim, just quieter.

/** The minimum a caller must give us about a fired tripwire: `state === 'fired'` means at least one
 *  firing is still un-adjudicated (see `viewToTripwires`); anything else is the analyst's own
 *  disposition, i.e. fired and decided. */
export interface WatchTripwire {
  state: string
}

export interface WatchSummary {
  /** The badge. A string so "unknown" can be an em-dash rather than a lie. */
  count: string
  /** The caption after "indicators & warning — ". */
  note: string
}

/** How the fired half reads on its own. */
function firedNote(tripwires: readonly WatchTripwire[]): string {
  const open = tripwires.filter((t) => t.state === 'fired').length
  if (open > 0) return `${open} fired`
  if (tripwires.length > 0) return 'fired · all decided'
  return 'none fired'
}

/**
 * @param armed      the armed catalogue, or `null` if it could not be read (never treat as 0)
 * @param tripwires  observables with at least one firing on the current view, or `null` in demo mode
 * @param demoCount  the frozen demo tripwire count, used only when there is no live feed at all
 */
export function watchSummary(
  armed: readonly unknown[] | null,
  tripwires: readonly WatchTripwire[] | null,
  demoCount: number,
): WatchSummary {
  // No live feed at all → demo mode's frozen scenario. Unchanged output: "3" · "armed".
  if (!tripwires) return { count: String(demoCount), note: 'armed' }

  const fired = firedNote(tripwires)

  // Catalogue unreadable: report the half we do know and NAME the half we don't. The badge shows the
  // fired count when there is one (a real number, correctly labelled) and an em-dash when there is
  // not — because "0" here would be a claim about the catalogue, which we cannot make.
  if (armed === null) {
    return {
      count: tripwires.length > 0 ? String(tripwires.length) : '—',
      note: `${fired} · armed count unavailable`,
    }
  }

  return { count: String(armed.length), note: `${armed.length} armed · ${fired}` }
}
