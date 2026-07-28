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

/** The third truth (AH-1): ARMED is not the same as WATCHING. A tripwire whose anchors resolve to no
 *  node in the current view is armed and watching an EMPTY SET — it can never fire, so it inflates the
 *  armed count while contributing nothing to coverage. "3 armed · none fired" reads as three quiet
 *  sentries; the honest reading is "3 armed · 1 watching nothing · none fired". */
export interface WatchAnchorCheck {
  checked: boolean
  unresolved: readonly {
    watching_nothing?: boolean
    watched_node_count?: number | null
    severity?: string
  }[]
}

/** AH-2 — the rail is a one-line ALARM surface, so only faults belong on it.
 *
 *  `pending_coverage` means the anchor names a DECLARED entity that no document has produced yet. That
 *  is this system's own default boot state — two docs are withheld from the seed on purpose so the
 *  reviewer can ingest them live — so counting it here would make the rail shout on a perfectly healthy
 *  first paint and then fall silent the moment the demo alert fires. Exactly backwards. It is still
 *  reported one click away in the Watch panel, where there is room to say what it means.
 *
 *  A problem with NO stated severity still counts as a fault: an underclaim is as dishonest as an
 *  overclaim, so an unrecognised payload is never quietly downgraded to "fine". */
function isFault(u: { severity?: string }): boolean {
  return (u.severity ?? 'dangling') !== 'pending_coverage'
}

/** How the anchor half reads on its own; `''` when there is nothing to add. */
function anchorNote(anchors: WatchAnchorCheck | null): string {
  if (anchors === null) return '' // unknown — not a claim either way
  if (!anchors.checked) return 'anchor check unavailable'
  const faults = anchors.unresolved.filter(isFault)
  const dead = faults.filter((u) => u.watching_nothing).length
  // "Scope lost" is NOT a milder partial miss — it evaluates the WHOLE graph, so anything it fires is
  // about the wrong subject. The backend keeps the three modes apart because they have opposite
  // consequences; the first line an analyst reads must not merge two of them back together.
  const unscoped = faults.filter((u) => !u.watching_nothing && u.watched_node_count === null).length
  const degraded = faults.length - dead - unscoped
  const parts: string[] = []
  if (dead > 0) parts.push(`${dead} watching nothing`)
  if (unscoped > 0) parts.push(`${unscoped} scope lost`)
  if (degraded > 0) parts.push(`${degraded} anchor unresolved`)
  return parts.join(' · ')
}

/** The fourth truth (AH-3): binding is not the same as being ABLE TO FIRE. The anchor check above
 *  asks whether a wire is aimed at real nodes; this asks whether the thing it watches for could ever
 *  happen. A wire can pass the first and fail the second — every anchor bound, 66 nodes watched, and
 *  a filter on an edge type nothing in coverage produces. It inflates the armed count exactly like a
 *  blind anchor does, and "3 armed · none fired" is exactly as false about it. */
export interface WatchReachabilityCheck {
  checked: boolean
  observables: readonly { can_fire?: boolean; gap_kind?: string | null; checked?: boolean }[]
}

/** How the reachability half reads on its own; `''` when there is nothing to add.
 *
 *  Both gap kinds are counted, and the caption does NOT split them the way the panel does. That is a
 *  deliberate compression for a one-line surface: the difference between "a document would fix this"
 *  and "a human must fix this" changes what an analyst DOES, but not whether they can trust the
 *  silence — and trust is the only thing the rail has room to speak to. The remedy is one click away
 *  in the Watch panel, where there is room to say which is which.
 *
 *  Note this deliberately differs from `anchorNote`'s rule of faults-only. A `pending_coverage`
 *  anchor leaves its wire watching real nodes — degraded, not dead — so putting it on the alarm line
 *  would cry wolf. `can_fire: false` means dead, whichever gap kind caused it. */
function reachabilityNote(reach: WatchReachabilityCheck | null): string {
  if (reach === null) return '' // unknown — not a claim either way
  if (!reach.checked) return 'reachability unchecked'
  const dead = reach.observables.filter(
    (r) => r.checked !== false && r.can_fire === false && r.gap_kind !== 'scope',
  ).length
  return dead > 0 ? `${dead} cannot fire` : ''
}

/**
 * @param armed      the armed catalogue, or `null` if it could not be read (never treat as 0)
 * @param tripwires  observables with at least one firing on the current view, or `null` in demo mode
 * @param demoCount  the frozen demo tripwire count, used only when there is no live feed at all
 * @param anchors    the live anchor check, or `null` if unknown — never inferred to be clean
 * @param reach      the live trigger-reachability check, or `null` if unknown — likewise
 */
export function watchSummary(
  armed: readonly unknown[] | null,
  tripwires: readonly WatchTripwire[] | null,
  demoCount: number,
  anchors: WatchAnchorCheck | null = null,
  reach: WatchReachabilityCheck | null = null,
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

  // Order is deliberate: the count, then every reason it OVERSTATES coverage, then what has fired. A
  // tripwire that cannot fire — whether because it is aimed at nothing or because the condition it
  // watches for is impossible — is the thing an analyst most needs to see before trusting silence.
  // The badge stays the true armed count: it is correctly labelled "armed", and the caption, not the
  // number, is where the caveat belongs.
  const note = [`${armed.length} armed`, anchorNote(anchors), reachabilityNote(reach), fired]
    .filter(Boolean)
    .join(' · ')
  return { count: String(armed.length), note }
}
