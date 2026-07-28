// Trigger reachability, turned into what a card actually shows (AH-3). Pure — no React, no fetch —
// so every honesty rule below is unit-testable, exactly like watchSummary.ts. The component does the
// pixels; this file does the judgement.
//
// THE BUG THIS EXISTS TO PREVENT. The Watch panel already learned one lesson: a tripwire aimed at no
// real node must SAY it is watching nothing rather than sit there looking armed. Reachability is the
// same lesson one step later. A wire can bind every anchor, watch 66 nodes, and still filter on an
// edge type that no document in coverage produces — armed, quiet, and structurally incapable of ever
// firing. The backend computes this and serves a verdict per observable. Until now it rendered
// nowhere, so the panel showed three sentries when only one of them could actually trip.
//
// And the sharp part, which is why the anchor check alone was not enough: the two failures resolve
// INDEPENDENTLY. The interceptor wire's anchor gap clears the moment a reviewer ingests the withheld
// documents — so the "awaiting coverage" block correctly disappears — while the wire remains just as
// incapable of firing as before. Without this file the panel gets *less* honest after ingest, which
// is the worst possible direction for a monitoring surface to move in.
//
// REGISTERS. The panel already speaks two: neutral dashed ("AWAITING COVERAGE" — a coverage gap that
// clears itself, nobody needs to do anything) and loud ("WATCHING NOTHING" — a defect a human must
// fix). Reachability verdicts sort into exactly those same two, and the sort is `gap_kind`, because
// gap_kind IS the question "does a human have to do something?".
import type { TriggerReachability } from '@/api/types'
import { isReachabilityFault } from '@/api/types'

/** Which of the panel's two existing registers a verdict belongs in — plus `unknown`, which is
 *  neither, and must never be collapsed into either one. */
export type ReachabilityRegister = 'fault' | 'gap' | 'unknown'

export interface ReachabilityNotice {
  register: ReachabilityRegister
  /** The block's eyebrow, in the panel's existing all-caps idiom. */
  label: string
  /** The BACKEND's sentence, verbatim — it already names the specific missing thing and the remedy.
   *  Never composed here: a UI paraphrase is how the surface and the engine drift apart, and the
   *  engine is the one that actually knows. `''` when the backend supplied none, in which case the
   *  block renders `detail` alone rather than inventing prose. */
  warning: string
  /** The terse machine line under it: status, then what is missing. Composed from tokens, never
   *  from the warning text. */
  detail: string
}

function humanKind(kind: string): string {
  return kind.replace(/_/g, ' ')
}

/** `no_coverage · edge type 'replenishes' · node type 'interceptor_stockpile'` */
function detailLine(r: TriggerReachability): string {
  const missing = (r.missing ?? []).map((m) => `${humanKind(m.kind)} '${m.name}'`)
  return [r.status, ...missing].filter(Boolean).join('  ·  ')
}

/**
 * The block to render under a tripwire card, or `null` when there is nothing to say.
 *
 * `null` is returned in exactly three cases, and each is deliberate:
 *  - the wire CAN fire — the positive verdict belongs on the card's one-line meta (see
 *    `reachabilityMeta`), not in a block of its own. A green reassurance box on every healthy card
 *    is how a panel becomes wallpaper, and then the one box that matters gets skimmed past too.
 *  - `gap_kind === 'scope'` — the anchor check already owns that remedy and already renders it on
 *    this very card. Diagnosing it twice, in two different vocabularies, is worse than once.
 *  - no verdict at all for this observable — we know nothing, so we assert nothing. Note this is
 *    silence, never a pass: nothing anywhere else on the card claims the wire can fire.
 */
export function reachabilityNotice(r: TriggerReachability | undefined): ReachabilityNotice | null {
  if (!r) return null

  // The check did not run. This is the one state that is neither good nor bad news, and the backend
  // already refuses to report "reachable" here — so the UI refuses too. Rendering nothing would let
  // an unrun check read as a passed one, which is precisely the failure this whole panel is about.
  if (r.checked === false) {
    return {
      register: 'unknown',
      label: 'REACHABILITY UNVERIFIED',
      warning: r.warning ?? '',
      detail: 'not checked',
    }
  }

  if (r.can_fire) return null
  if (r.gap_kind === 'scope') return null // the anchor block on this card already says it

  // `data` = modelled right, just no coverage yet, and it self-heals the instant a document asserts
  // the missing thing — live, no restart, no human. That is the same shape of news as the anchor
  // check's "awaiting coverage", so it gets the same quiet treatment. Everything else is a fault: no
  // volume of documents fixes it, someone must edit the trigger or the ontology.
  const fault = isReachabilityFault(r)
  return {
    register: fault ? 'fault' : 'gap',
    label: fault ? 'CANNOT FIRE' : 'UNCOVERED',
    warning: r.warning ?? '',
    detail: detailLine(r),
  }
}

/**
 * What the card's state badge should say — the GLANCE layer, and the single most important line here.
 *
 * An analyst scanning this panel reads three badges and nothing else. If a wire that cannot fire
 * shows a neutral "armed", the panel has told them the opposite of the truth before they read one
 * word of prose. The card already does exactly this for the anchor case (`watching nothing`), so
 * this extends an established pattern rather than inventing a second one.
 *
 * Returns `null` to leave the caller's own label alone (healthy wire, scope gap, or no verdict).
 */
export function reachabilityBadge(r: TriggerReachability | undefined): string | null {
  const notice = reachabilityNotice(r)
  if (!notice) return null
  if (notice.register === 'unknown') return 'unverified'
  return notice.register === 'fault' ? 'cannot fire' : 'uncovered'
}

/** The positive verdict, for the card's existing mono meta line. The backend serves a COMPLETE list
 *  (one entry per armed observable, not problems-only) precisely so a card can state "and it could
 *  fire" rather than leave an analyst inferring it from an absence — an inference that is exactly
 *  what was wrong before. Cheap, one token, no extra chrome. */
export function reachabilityMeta(r: TriggerReachability | undefined): string | null {
  if (!r || r.checked === false || !r.can_fire) return null
  return typeof r.candidate_count === 'number'
    ? `can fire · ${r.candidate_count} candidate${r.candidate_count === 1 ? '' : 's'}`
    : 'can fire'
}

/** observable_id → verdict, for a card to look up its own. */
export function reachabilityIndex(
  check: { observables?: readonly TriggerReachability[] } | null,
): Map<string, TriggerReachability> {
  return new Map((check?.observables ?? []).map((r) => [r.observable_id, r]))
}

/** How many armed wires cannot fire right now — the number the rail caption needs.
 *
 *  Counts BOTH gap kinds, unlike the rail's anchor half which deliberately drops `pending_coverage`.
 *  That is not an inconsistency, it is the same principle applied to a different fact: a
 *  pending-coverage anchor still leaves its wire watching real nodes (2 and 66 of them, on the
 *  shipped config), so the wire is degraded, not dead. `can_fire: false` means the wire is dead —
 *  zero percent functional — whatever the reason. A rail that hides half the dead wires because they
 *  might revive later is making the same all-clear promise this fix exists to stop making.
 *
 *  `scope` gaps are excluded: the anchor half of the caption already counts those. */
export function cannotFireCount(check: { observables?: readonly TriggerReachability[] } | null): number {
  return (check?.observables ?? []).filter(
    (r) => r.checked !== false && !r.can_fire && r.gap_kind !== 'scope',
  ).length
}
