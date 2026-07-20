// LIVE-mode adapter: maps the backend GraphView (GET /view) into the same fixture
// shapes the DEMO scenario uses (src/demo/scenario.ts) — PinDef for the map, and
// GraphNodeDef/GraphEdgeDef for the Cytoscape graph. Keeping LIVE and DEMO on one
// output shape means the stage components never need to branch on data source.
//
// Pure functions only — no React, no Zustand, no fetch. Callers own the fetch and
// pass the resulting GraphView in.
//
// Graph-node x/y are always emitted as 0/0: the demo scenario freezes a hand-placed
// preset layout, but a live GraphView carries no positions, so the GraphView
// component is responsible for laying live nodes out algorithmically (e.g. a
// Cytoscape layout run) rather than reading x/y off the fixture.

import type {
  Alert,
  AlertDisposition,
  AnswerHop,
  AskAnswer,
  ClaimKind,
  ClaimRecord,
  DateValue,
  DocRef,
  EdgeView,
  GraphView,
  KnownGap,
  NodeView,
  ObservabilityCeiling,
  ProvenanceDrawer,
  RefusalKind,
  Status,
} from './types'
import type { EdgeKind, GraphEdgeDef, GraphKind, GraphNodeDef, PinDef } from '@/demo/scenario'

/** "24.86°N  67.01°E" — absolute value to 2dp, degree sign, hemisphere letter. */
export function formatCoord(lat: number, lon: number): string {
  const latHemi = lat < 0 ? 'S' : 'N'
  const lonHemi = lon < 0 ? 'W' : 'E'
  return `${Math.abs(lat).toFixed(2)}°${latHemi}  ${Math.abs(lon).toFixed(2)}°${lonHemi}`
}

/** A candidate chokepoint outranks its own status; otherwise status maps directly. */
export function statusToGraphKind(node: NodeView): GraphKind {
  if (node.materiality?.chokepoint_status === 'candidate') return 'chokepoint'
  switch (node.status) {
    case 'confirmed':
      return 'confirmed'
    case 'probable':
    case 'possible':
      return 'probable'
    case 'stale':
      return 'stale'
    case 'insufficient':
      return 'gap'
    // "credible sources disagree" is not "we don't know" — a contradiction is loud
    // (solid coral, filled), a Known Gap is quiet (dashed grey, no fill). Folding one
    // into the other drew a problem as an absence.
    case 'contradicted':
      return 'contradicted'
    default:
      return 'probable'
  }
}

/** Edge types that carry NO status by design — identity (`same-as` / `distinct-from`) and
 *  the `supersedes` version link. Anything switching on edge status must handle these
 *  first, or a status-less edge falls through a default and reads as a truth claim. */
export const STATUSLESS_EDGE_TYPES = new Set(['same-as', 'distinct-from', 'supersedes'])

export function isStatuslessEdge(edge: EdgeView): boolean {
  return STATUSLESS_EDGE_TYPES.has(edge.type)
}

/** Edge → visual kind. Order matters:
 *  1. `supersedes` is a status-LESS timeline link — "replaced by →", never an alarm and
 *     never a contradiction (it is the version link between two already-scored edges).
 *  2. other status-less types (identity) get the neutral link treatment.
 *  3. `stale` / `superseded_by` = HISTORY: we know this assertion was overtaken.
 *  4. `insufficient` = an EVIDENCE GAP: we do NOT know. It must NOT look like `stale`
 *     (history) and must not fall through to `probable` (a live teal assertion).
 *  5. `contradicted` is its own thing — sources disagree, which is a problem, not a gap.
 *
 *  A `supersedes` edge splits on adjudication: PROMOTED is settled ("this replaced that")
 *  and draws solid; a CANDIDATE — flagged `candidate_supersede`, or still sitting behind a
 *  pending/held gate — is provisional ("something moved, but we are not sure it is the same
 *  unit") and draws DASHED. Same arrowhead, so it still reads as a version link and never
 *  as an alarm; THE ONE RULE carries the uncertainty. */
const UNSETTLED_SUPERSEDE_GATES = new Set(['pending', 'held'])

export function edgeToKind(edge: EdgeView): EdgeKind {
  if (edge.type === 'supersedes') {
    const gate = supersedeGate(edge)
    if (isCandidateSupersede(edge) || (gate != null && UNSETTLED_SUPERSEDE_GATES.has(gate)))
      return 'e-supersede-candidate'
    return 'e-supersede'
  }
  if (isStatuslessEdge(edge)) return 'e-link'
  if (edge.superseded_by || edge.status === 'stale') return 'e-stale'
  if (edge.status === 'insufficient') return 'e-gap'
  if (edge.status === 'contradicted') return 'e-contradicted'
  if (edge.status === 'confirmed') return 'e-confirmed'
  return 'e-probable'
}

/** `attrs.supersede_hold_reason` — why an overtaken assertion was NOT auto-retired
 *  (e.g. "newer-below-probable", "newer-deception-gate:decoy-risk"). Returned VERBATIM:
 *  these strings are the backend's own words and rewriting them would put the UI's
 *  paraphrase between the analyst and the gate that actually fired. Tolerates a bare
 *  string as well as the documented list, and returns [] for anything else. */
export function supersedeHoldReasons(edge: EdgeView | null | undefined): string[] {
  const raw = edge?.attrs?.supersede_hold_reason
  if (typeof raw === 'string') return raw ? [raw] : []
  if (Array.isArray(raw)) return raw.filter((r): r is string => typeof r === 'string' && r.length > 0)
  return []
}

/** 'pending' | 'promoted' | 'held' | null — the supersession gate an edge sits behind. */
export function supersedeGate(edge: EdgeView | null | undefined): string | null {
  const gate = edge?.attrs?.supersede_gate
  return typeof gate === 'string' ? gate : null
}

/** true when this edge is half of an un-adjudicated supersession (the analyst decides). */
export function isCandidateSupersede(edge: EdgeView | null | undefined): boolean {
  return edge?.attrs?.candidate_supersede === true
}

function yearOf(value?: string | null): number | null {
  if (!value) return null
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return null
  return parsed.getFullYear()
}

// ───────────────────── analyst-facing naming (no raw ids in copy) ─────────────────────
// `site_rahwali` is a key, not a name. Analyst-facing copy renders the node's OWN `name`
// and keeps the id as secondary/technical detail; nothing here paraphrases or invents a
// label — a node with no `name` falls back to its id rather than to a guess.

/** id → node.name, or the id itself when the graph has no name for it. Never invents one. */
export function displayNameOf(view: GraphView | null | undefined, id: string): string {
  if (!view) return id
  const node = view.nodes.find((n) => n.id === id)
  if (node?.name) return node.name
  const edge = view.edges.find((e) => e.id === id)
  if (edge) {
    // an edge has no name of its own — read it as "source — type → target", each side named.
    return `${displayNameOf(view, edge.source)} — ${humanizeEdge(edge.type)} → ${displayNameOf(view, edge.target)}`
  }
  return id
}

/** Build a reusable resolver over one view (avoids re-scanning per lookup). */
export function nameResolver(view: GraphView | null | undefined): (id: string) => string {
  if (!view) return (id) => id
  const names = new Map(view.nodes.map((n) => [n.id, n.name ?? n.id]))
  return (id) => names.get(id) ?? displayNameOf(view, id)
}

/** True when `s` is an element id the live view knows — i.e. safe to swap for a name.
 *  Free-text slots ("an unobscured pass") must pass through untouched. */
export function isKnownElementId(view: GraphView | null | undefined, s: string): boolean {
  if (!view) return false
  return view.nodes.some((n) => n.id === s) || view.edges.some((e) => e.id === s)
}

// ───────────────────────────── map pins + supersession ─────────────────────────────
// Supersession lives on the EDGE, not the node — a site that a unit left is still a real
// site, it is the *occupancy* that was overtaken. So the map has to derive "this location
// is history now" from the graph rather than read it off a node status, or the relocation
// story that the Graph stage tells correctly is silently lost on the default stage.
//
// Only a SETTLED supersession greys a pin. A candidate/pending/held one means "something
// moved, but we are not sure it is the same unit" — drawing that as settled history would
// assert an adjudication the analyst has not made.

/** LIVE-only pin extras the frozen demo fixture does not carry. Optional, so `PinDef[]`
 *  (the demo's own pins) is assignable wherever a `StagePin[]` is expected. */
export interface StagePinExtras {
  /** this location was overtaken by another — settled history, not an evidence gap */
  superseded?: boolean
  /** the node id that replaced it (the connector's other end), when known */
  supersededBy?: string | null
}

export type StagePin = PinDef & StagePinExtras

/** target-of-a-settled-`supersedes`-edge → the successor's node id. */
export function supersededSites(view: GraphView): Map<string, string> {
  const out = new Map<string, string>()
  for (const edge of view.edges) {
    if (edge.type !== 'supersedes') continue
    if (edgeToKind(edge) !== 'e-supersede') continue // candidate/pending/held → not settled
    out.set(edge.target, edge.source)
  }
  return out
}

/** Nodes without a resolved location live only in the graph, not on the map. */
export function viewToPins(view: GraphView): StagePin[] {
  const pins: StagePin[] = []
  const superseded = supersededSites(view)
  for (const node of view.nodes) {
    const lat = node.location?.wgs84_lat
    const lon = node.location?.wgs84_lon
    if (typeof lat !== 'number' || !Number.isFinite(lat)) continue
    if (typeof lon !== 'number' || !Number.isFinite(lon)) continue

    const surface = node.location?.surface_format
    const coord = typeof surface === 'string' && surface.length > 0 ? surface : formatCoord(lat, lon)
    const year = yearOf(node.freshness?.last_support_time)
    const successor = superseded.get(node.id)

    pins.push({
      id: node.id,
      label: node.name ?? node.id,
      lat,
      lon,
      coord,
      status: node.status ?? 'insufficient',
      // "superseded" states the subtraction; it never claims the site ceased to exist.
      caption: successor
        ? year !== null
          ? `superseded · ${year}`
          : 'superseded'
        : year !== null
          ? `as of ${year}`
          : '',
      superseded: successor != null,
      supersededBy: successor ?? null,
    })
  }
  return pins
}

/** Every node becomes a graph node, located or not; positions are 0/0 (see header). */
export function viewToGraphNodes(view: GraphView): GraphNodeDef[] {
  return view.nodes.map((node) => ({
    id: node.id,
    label: `${node.name ?? node.id}\n${node.type}`,
    x: 0,
    y: 0,
    kind: statusToGraphKind(node),
  }))
}

export function viewToGraphEdges(view: GraphView): GraphEdgeDef[] {
  return view.edges.map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    kind: edgeToKind(edge),
  }))
}

export function viewToGraph(view: GraphView): { nodes: GraphNodeDef[]; edges: GraphEdgeDef[] } {
  return { nodes: viewToGraphNodes(view), edges: viewToGraphEdges(view) }
}

// ─────────────────────── live provenance drawer ───────────────────────
// LIVE-mode formatter: maps the backend's structured GET /evidence/{id} response
// (ProvenanceDrawer) into a display model for the provenance drawer. This is NOT
// AI — it deterministically re-shapes already-structured fields (claims, clusters,
// confidence, sufficiency) for rendering. The demo scenario keeps its own
// hand-authored drawer fixture; this is the live counterpart.
//
// Pure functions only — no React, no Zustand, no fetch.

export interface LiveClaimRow {
  claimId: string
  sourceId: string
  kind: ClaimKind
  detail: string // short human line from kind + asserts (e.g. "observation · relationship")
  dates: { event?: string; reported?: string; ingested?: string }
  docRefs: DocRef[] // ALWAYS an array (normalize DocRef | DocRef[] → DocRef[]); the jump-to-source targets
  /** the VERBATIM text at each docRef, same order/length as `docRefs`. '' = unreadable span —
   *  the row then shows the locator alone. Never a paraphrase: this is the evidence itself. */
  quotes: string[]
  dots: number // 1..4 credibility tier
}

export interface LiveDrawerCluster {
  groupId: string
  axis?: { origin?: string; discipline?: string; interest?: string }
  rows: LiveClaimRow[]
}

export interface LiveDrawerModel {
  subjectRef: string
  status: Status
  sources: number // count of DISTINCT source_id across claims
  looks: number // clusters.length (independent looks)
  sufficiency?: {
    satisfied: boolean
    missingSlots: string[]
    nextCoverageDue?: string | null
    ceiling?: ObservabilityCeiling | null
  }
  clusters: LiveDrawerCluster[]
  opposingCount: number
  integrityFlags: string[]
}

/** undefined/null → undefined; string → itself; object → date, else label, else a start–end
 *  range, else whichever of start/end is present, else undefined. */
export function dateValueToString(d: DateValue | null | undefined): string | undefined {
  if (d === null || d === undefined) return undefined
  if (typeof d === 'string') return d
  if (d.date) return d.date
  if (d.label) return d.label
  if (d.start && d.end) return `${d.start} – ${d.end}`
  return d.start ?? d.end ?? undefined
}

/** undefined/null → 2 (unknown-mid); else bucket a 0..1 credibility score into 1..4 dots. */
export function credibilityToDots(c: number | null | undefined): number {
  if (c === null || c === undefined) return 2
  if (c < 0.25) return 1
  if (c < 0.5) return 2
  if (c < 0.75) return 3
  return 4
}

/** Normalize the doc_ref union (single ref or list) to an array; [] if absent. */
export function docRefsOf(ref: DocRef | DocRef[] | null | undefined): DocRef[] {
  if (ref === null || ref === undefined) return []
  return Array.isArray(ref) ? ref : [ref]
}

/** Structured /evidence/{id} response → display model for the live provenance drawer. */
export function evidenceToDrawerModel(data: ProvenanceDrawer): LiveDrawerModel {
  const claims = data.claims ?? []
  const claimsById = new Map<string, ClaimRecord>(claims.map((c) => [c.claim_id, c]))
  const clusters = data.clusters ?? []

  const sourceIds = new Set(claims.map((c) => c.source_id))

  const liveClusters: LiveDrawerCluster[] = clusters.map((group) => ({
    groupId: group.group_id,
    axis: group.axis_key
      ? {
          origin: group.axis_key.origin,
          discipline: group.axis_key.discipline,
          interest: group.axis_key.interest,
        }
      : undefined,
    rows: group.claim_ids.reduce<LiveClaimRow[]>((rows, claimId) => {
      const claim = claimsById.get(claimId)
      if (!claim) return rows
      const refs = docRefsOf(claim.doc_ref)
      const quotes = data.quotes?.[claimId] ?? []
      rows.push({
        claimId: claim.claim_id,
        sourceId: claim.source_id,
        kind: claim.kind,
        detail: [claim.kind, claim.asserts].filter(Boolean).join(' · '),
        dates: {
          event: dateValueToString(claim.event_time),
          reported: dateValueToString(claim.report_time),
          ingested: dateValueToString(claim.ingest_time),
        },
        docRefs: refs,
        // pad/trim to docRefs length so index i always answers "what does ref i say?"
        quotes: refs.map((_, i) => quotes[i] ?? ''),
        dots: credibilityToDots(data.confidence?.per_claim_credibility?.[claimId]),
      })
      return rows
    }, []),
  }))

  return {
    subjectRef: data.subject_ref,
    status: data.status ?? 'insufficient',
    sources: sourceIds.size,
    looks: clusters.length,
    sufficiency: data.sufficiency
      ? {
          satisfied: data.sufficiency.satisfied,
          missingSlots: data.sufficiency.missing_slots ?? [],
          nextCoverageDue: data.sufficiency.next_coverage_due ?? null,
          ceiling: data.sufficiency.ceiling ?? null,
        }
      : undefined,
    clusters: liveClusters,
    opposingCount: (data.opposing_claims ?? []).length,
    integrityFlags: data.confidence?.integrity_flags ?? [],
  }
}

// ─────────────────────────── live ask / answer ───────────────────────────
// LIVE-mode formatter: maps POST /ask (AskAnswer) into a display model for the
// answer panel. The agent GENUINELY writes `answer` (rendered as-is, the one place
// live prose is model-authored). Everything else — the numbered walk of hops, the
// citations, the refusal layout — is deterministic formatting of the structured
// response into the demo's visual grammar (Observed walk vs Inferred wall; a refusal
// is an answer, not an error). NOT AI here.
//
// Pure functions only — no React, no Zustand, no fetch.

export interface LiveAnswerHop {
  step: number
  src: string
  dst: string
  edge: string
  line: string // readable "src — edge → dst"
  observed: boolean // observed evidence vs. inferred step (the structural wall)
  citations: string[]
}

export interface LiveAnswerRefusal {
  kind: RefusalKind
  reason?: string
  missing: string[]
  nextCoverageDue?: string | null
  knownGap?: KnownGap | null
}

export interface LiveAnswerModel {
  kind: 'answer' | 'refusal'
  question: string
  subQuestions: string[]
  answer: string // '' when refusing
  hops: LiveAnswerHop[]
  citations: string[]
  refusal?: LiveAnswerRefusal
}

/** "supplies-component" / "based_at" → "supplies component" / "based at". */
export function humanizeEdge(edge: string): string {
  return humanizeToken(edge)
}

/** One hop → a readable "src — edge → dst" line (the walk's rungs). */
export function hopLine(hop: AnswerHop): string {
  return `${hop.src} — ${humanizeEdge(hop.edge)} → ${hop.dst}`
}

/** A refusal is signalled by an explicit refusal payload OR a null answer — either
 *  way the response is treated as a refusal (an answer, never an error). */
export function askToAnswerModel(data: AskAnswer): LiveAnswerModel {
  const isRefusal = data.refusal != null || data.answer == null
  const hops: LiveAnswerHop[] = (data.hops ?? []).map((h) => ({
    step: h.step,
    src: h.src,
    dst: h.dst,
    edge: h.edge,
    line: hopLine(h),
    observed: h.observed_or_inferred !== 'inferred',
    citations: h.claim_ids ?? [],
  }))
  return {
    kind: isRefusal ? 'refusal' : 'answer',
    question: data.question,
    subQuestions: data.sub_questions ?? [],
    answer: data.answer ?? '',
    hops,
    citations: data.citations ?? [],
    refusal: isRefusal
      ? {
          // Absent `kind` → 'evidence', the pre-`kind` contract. A capability outage that arrives
          // untagged still reads as an evidence gap, so the tag is set at the producer, not guessed here.
          kind: data.refusal?.kind ?? 'evidence',
          reason: data.refusal?.reason,
          missing: data.refusal?.missing ?? [],
          nextCoverageDue: data.refusal?.next_coverage_due ?? null,
          knownGap: data.refusal?.known_gap ?? null,
        }
      : undefined,
  }
}

// ─────────────────── live tripwires / alert feed (derived from /view) ───────────────────
// The alert feed rides in on GET /view — it is REAL fired state, not a picture of a
// tripwire. Two shapes come out of it: a per-firing model (what changed, its evidence,
// whether a supersession was held) and a per-observable grouping for the Watch panel.
//
// An alert is the one derived artifact that used to have no provenance. It now names the
// claims behind BOTH sides of the change, and `before_ref` / `after_ref` are real view
// element ids — so each side is one click from the same GET /evidence/{id} drawer every
// other element uses. Nothing here invents a citation: an alert with no provenance block
// renders as "no evidence recorded", never as a plausible-looking one.
//
// Pure functions only — no React, no Zustand, no fetch.

/** One side (before / after) of a change, with the element that carried it and its claims. */
export interface LiveAlertSide {
  side: 'before' | 'after'
  elementRef: string | null // → GET /evidence/{id}; null when the backend recorded none
  claimIds: string[]
}

export interface LiveAlertProvenanceModel {
  sides: LiveAlertSide[] // [before, after] — only the sides that carry anything
  claimIds: string[] // union, before-first
  status: Status | null // copied off the after-element (MONITOR never scores)
  assertionConfidence: number | null
}

export interface LiveFiring {
  key: string // stable per-firing key (matches the review-queue itemId suffix)
  observableId: string
  subject: string | null
  firedTs: string | null
  severity: string | null
  changed: { from: string; to: string } | null
  disposition: AlertDisposition | null
  dispositionLabel: string | null // past-tense analyst outcome, null while un-adjudicated
  provenance: LiveAlertProvenanceModel | null
  holdReasons: string[] // verbatim supersede_hold_reason strings off the referenced edges
  gate: string | null // 'pending' | 'promoted' | 'held'
}

export interface LiveTripwire {
  observableId: string
  name: string // humanised observable id — the only label the feed gives us
  state: 'fired' | AlertDisposition
  stateLabel: string // what the badge says — DERIVED, never a hardcoded "armed"
  firings: LiveFiring[]
}

const DISPOSITION_LABEL: Record<AlertDisposition, string> = {
  real: 'accepted as real',
  noise: 'dismissed as noise',
  'needs-more': 'held for a second look',
}

/** Compact "k: v, k: v" summary of an alert before/after snapshot. */
function summarizeSnapshot(snap: Record<string, unknown> | undefined): string {
  if (!snap) return ''
  return Object.entries(snap)
    .map(([k, v]) => `${k}: ${v}`)
    .join(', ')
}

/** 'obs-basing-relocation' → 'Basing relocation'. The observable catalogue is not exposed
 *  by any GET route, so the id is the only name we have — humanise it, don't invent one. */
export function humanizeObservableId(id: string): string {
  const words = id.replace(/^obs[-_]/, '').replace(/[-_]/g, ' ').trim()
  return words ? words.charAt(0).toUpperCase() + words.slice(1) : id
}

/** Stable key for one firing — observable + subject + fired timestamp. */
export function firingKey(alert: Alert): string {
  return `${alert.observable_id}:${alert.subject ?? ''}:${alert.fired_ts ?? ''}`
}

function alertProvenanceModel(alert: Alert): LiveAlertProvenanceModel | null {
  const p = alert.provenance
  if (!p) return null
  const before = p.before_claim_ids ?? []
  const after = p.after_claim_ids ?? []
  const sides: LiveAlertSide[] = []
  if (p.before_ref || before.length) sides.push({ side: 'before', elementRef: p.before_ref ?? null, claimIds: before })
  if (p.after_ref || after.length) sides.push({ side: 'after', elementRef: p.after_ref ?? null, claimIds: after })
  const union = p.claim_ids?.length ? p.claim_ids : [...before, ...after]
  if (!sides.length && !union.length && p.status == null && p.assertion_confidence == null) return null
  return {
    sides,
    claimIds: [...new Set(union)],
    status: p.status ?? null,
    assertionConfidence: p.assertion_confidence ?? null,
  }
}

/** One alert → the display model, resolving its before/after element refs against the view's
 *  edges so a held supersession explains itself in the analyst's own words. */
export function alertToFiring(alert: Alert, edges?: Map<string, EdgeView>): LiveFiring {
  const provenance = alertProvenanceModel(alert)
  const refs = [alert.provenance?.before_ref, alert.provenance?.after_ref].filter(
    (r): r is string => typeof r === 'string' && r.length > 0,
  )
  const referenced = refs.map((r) => edges?.get(r)).filter((e): e is EdgeView => e != null)
  const holdReasons = [...new Set(referenced.flatMap(supersedeHoldReasons))]
  const gate = referenced.map(supersedeGate).find((g) => g != null) ?? null
  const changed =
    alert.before || alert.after
      ? { from: summarizeSnapshot(alert.before), to: summarizeSnapshot(alert.after) }
      : null
  return {
    key: firingKey(alert),
    observableId: alert.observable_id,
    subject: alert.subject ?? null,
    firedTs: alert.fired_ts ?? null,
    severity: alert.severity ?? null,
    changed,
    disposition: alert.disposition ?? null,
    dispositionLabel: alert.disposition ? DISPOSITION_LABEL[alert.disposition] : null,
    provenance,
    holdReasons,
    gate,
  }
}

/** The live Watch panel's rows: one per observable that has actually fired, newest state
 *  first within each. State is DERIVED — 'fired' while any firing is un-adjudicated, else
 *  the analyst's own disposition. There is deliberately no "armed" here: the observable
 *  catalogue has no GET route, so a tripwire that has never fired is not knowable from
 *  /view, and claiming it is armed would be exactly the kind of fabrication this system
 *  refuses elsewhere. The panel says so instead. */
export function viewToTripwires(view: GraphView): LiveTripwire[] {
  const edges = new Map(view.edges.map((e) => [e.id, e]))
  const byObservable = new Map<string, LiveFiring[]>()
  for (const alert of view.alerts ?? []) {
    const firing = alertToFiring(alert, edges)
    const bucket = byObservable.get(firing.observableId)
    if (bucket) bucket.push(firing)
    else byObservable.set(firing.observableId, [firing])
  }
  return [...byObservable.entries()].map(([observableId, firings]) => {
    const open = firings.find((f) => f.disposition == null)
    const latest = firings[firings.length - 1]
    const state: 'fired' | AlertDisposition = open ? 'fired' : (latest.disposition as AlertDisposition)
    return {
      observableId,
      name: humanizeObservableId(observableId),
      firings,
      state,
      stateLabel: open ? 'fired' : (latest.dispositionLabel ?? 'fired'),
    }
  })
}

// ───────────────────── live review queue (derived from /view) ─────────────────────
// There is NO review-queue GET endpoint BY DESIGN — the queue is DERIVED on the client
// by scanning the rebuilt graph for the three kinds of thing that land in the uncertain
// middle: identity merges (same-as edges), assessments with opposing/contradicted
// evidence (status overrides), and un-dispositioned tripwire firings (alerts). Each
// decision is written back via POST /hitl/{verb} with the element's own id as `subject`;
// that response is the full rebuilt graph, so the badge drop + "same question, new
// answer" fall out of re-deriving the queue from the new view. NOT AI — pure scan.
//
// Pure functions only — no React, no Zustand, no fetch.

export type LiveReviewType = 'merge' | 'status-override' | 'alert-disposition'

export interface LiveReviewOption {
  key: string // sent as HitlDecision.decision
  label: string // imperative button label
  done: string // past-tense resolved marker
}

/** One weighted merge signal, as the resolver actually scored it (edge `attrs.breakdown`).
 *  `score` is the raw 0..1 signal; `dots` is the same number in the app's tier grammar. */
export interface MergeSignalRow {
  key: string
  label: string
  score: number
  dots: number
}

/** The identity case, split the way the merge card argues it: `matchedOn` is the long quiet
 *  case FOR (every signal the resolver scored above zero), `differsOn` is the short loud case
 *  AGAINST — derived from the two records themselves (type, stated location, coordinates,
 *  conflicting attributes) plus every signal that scored EXACTLY zero, which is the resolver
 *  telling us in its own words what it could not find. Both are computed; nothing is authored. */
export interface LiveMergeEvidence {
  confidence: number | null
  matchedOn: MergeSignalRow[]
  differsOn: string[]
  /** what the merge demonstrably DOES — counted off the graph, never estimated */
  consequence: string[]
  /** what this card cannot tell the analyst. Printed instead of a plausible number (CLAUDE.md:
   *  a fabricated consequence next to real data is worse than an admitted gap). */
  unknowns: string[]
  left: LiveReviewSide
  right: LiveReviewSide
}

/** One side of a merge — the record itself, in analyst-facing terms. */
export interface LiveReviewSide {
  id: string
  label: string
  /** "basing site · probable · 1 claim" — the record's own facts, not a paraphrase */
  sub: string
  type: string
  status: Status | null
  claimCount: number
  chokepoint: boolean
}

export interface LiveReviewContext {
  summary: string
  left?: { id: string; label: string }
  right?: { id: string; label: string }
  changed?: { from: string; to: string }
  dots?: number
  detail?: string[] // opposing claim ids / extra lines
  severity?: string
  // alert-disposition only — the evidence behind the change (one click per side into the
  // provenance drawer) and, when a supersession was held back, the gate's own words.
  provenance?: LiveAlertProvenanceModel | null
  holdReasons?: string[]
  // merge only — the full identity case (see LiveMergeEvidence).
  merge?: LiveMergeEvidence
  // status-override / alert only — what the decision demonstrably changes, and what it cannot say.
  consequence?: string[]
  unknowns?: string[]
}

export interface LiveReviewItem {
  itemId: string // stable per-item key (de-dup + decided tracking)
  reviewType: LiveReviewType // HitlDecision.type
  hitlVerb: 'merge' | 'status' | 'alert' // which /hitl/* route
  subject: string // the element's own id → HitlDecision.subject
  kicker: string // small type label in the rail ("Merge · basing site")
  /** WHAT this item is about — the two candidate records, the node, the observable. A queue row
   *  has to be readable without opening it, so this is the entities, never the question. */
  title: string
  /** the one-line question the card asks ("Same system, or two?") — the card's headline */
  question: string
  note: string // second rail line: the one fact that most separates this row from its neighbours
  badge: string // primary chip (confidence band / contradiction / first seen)
  badges: string[] // badge + any materiality chips ("Touches a chokepoint")
  /** ranking inputs — the three dimensions spine/05 triage is keyed on. Materiality and
   *  confidence are real values off the graph; `null` confidence means unknown, which sorts
   *  as *more* urgent, never less (recall-biased: unknown is never treated as safe). */
  material: boolean
  confidence: number | null
  options: LiveReviewOption[]
  context: LiveReviewContext
  /** set by `groupReviewQueue` when this proposal is one of a connected run — carried onto the
   *  card so the analyst sees, while deciding, that the proposal is not independent evidence. */
  cluster?: { size: number; records: number; complete: boolean; note: string }
}

const MERGE_OPTIONS: LiveReviewOption[] = [
  { key: 'accept', label: 'Merge', done: 'Merged' },
  { key: 'reject', label: 'Keep separate', done: 'Kept separate' },
  { key: 'split', label: 'Split into two', done: 'Split' },
]
const OVERRIDE_OPTIONS: LiveReviewOption[] = [
  { key: 'promote', label: 'Promote to confirmed', done: 'Promoted' },
  { key: 'demote', label: 'Demote to probable', done: 'Demoted' },
  { key: 'reject', label: 'Reject this claim', done: 'Rejected' },
]
const ALERT_OPTIONS: LiveReviewOption[] = [
  { key: 'real', label: 'Accept the move', done: 'Accepted' },
  { key: 'noise', label: 'Dismiss as noise', done: 'Dismissed' },
  { key: 'needs-more', label: 'Hold for a second look', done: 'Held' },
]

// ── merge evidence, derived off the two records + the resolver's own breakdown ──────────────
// `attrs.breakdown` on a candidate same-as edge is the resolver's per-signal merge score
// (resolve/rconfig SIGNALS). Reading it is what turns "Close call" into an argument the analyst
// can check. Nothing here re-scores or re-weights — it renders what the resolver recorded.

/** The four merge signals, in analyst language (keys = resolve/rconfig SIGNALS). */
const MERGE_SIGNAL_LABEL: Record<string, string> = {
  attribute: 'Name & attributes',
  relational: 'Shared neighbours in the graph',
  temporal_consistency: 'Timeline consistent',
  source_asserted: 'A source calls them the same',
}

/** What a signal scoring EXACTLY zero means, stated as an absence. This is the case AGAINST
 *  merging in the resolver's own terms — it is not a paraphrase of the score, it is the score. */
const MERGE_SIGNAL_ABSENT: Record<string, string> = {
  attribute: 'Names and attributes do not match.',
  relational: 'Nothing in the graph connects them — no shared neighbour.',
  temporal_consistency: 'Their timelines are not consistent.',
  source_asserted: 'No source states they are the same.',
}

/** dots → the band an analyst reads on the row. Uses the app's existing credibility tiers
 *  (credibilityToDots) rather than a second, private set of thresholds. */
const MERGE_BAND: Record<number, string> = {
  4: 'Strong match',
  3: 'Close call',
  2: 'Weak match',
  1: 'Very weak',
}

/** 'basing_site' / 'temporal_consistency' → 'basing site' / 'temporal consistency'. */
export function humanizeToken(token: string): string {
  return token.replace(/[-_]/g, ' ').trim()
}

function attrsBreakdown(edge: EdgeView): Record<string, number> {
  const raw = edge.attrs?.breakdown
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return {}
  const out: Record<string, number> = {}
  for (const [k, v] of Object.entries(raw as Record<string, unknown>)) {
    if (k !== 'total' && typeof v === 'number' && Number.isFinite(v)) out[k] = v
  }
  return out
}

function isChokepoint(node: NodeView | undefined): boolean {
  const s = node?.materiality?.chokepoint_status
  return s === 'candidate' || s === 'confirmed'
}

function reviewSide(id: string, node: NodeView | undefined): LiveReviewSide {
  const claimCount = node?.claim_ids?.length ?? 0
  const type = node?.type ?? 'record'
  const status = node?.status ?? null
  return {
    id,
    label: node?.name ?? id,
    type,
    status,
    claimCount,
    chokepoint: isChokepoint(node),
    sub: [humanizeToken(type), status ?? 'unassessed', `${claimCount} claim${claimCount === 1 ? '' : 's'}`].join(' · '),
  }
}

/** Great-circle distance in km — only ever used to state a difference the graph already holds. */
function haversineKm(aLat: number, aLon: number, bLat: number, bLon: number): number {
  const R = 6371
  const toRad = (d: number) => (d * Math.PI) / 180
  const dLat = toRad(bLat - aLat)
  const dLon = toRad(bLon - aLon)
  const h =
    Math.sin(dLat / 2) ** 2 + Math.cos(toRad(aLat)) * Math.cos(toRad(bLat)) * Math.sin(dLon / 2) ** 2
  return 2 * R * Math.asin(Math.min(1, Math.sqrt(h)))
}

/** Scalar attribute values only — an object/array difference is not a sentence an analyst can read. */
function scalarAttr(v: unknown): string | null {
  if (typeof v === 'string') return v
  if (typeof v === 'number' || typeof v === 'boolean') return String(v)
  return null
}

/** Attribute keys that are plumbing, not description — never rendered as a difference. */
const ATTR_NOT_A_DIFFERENCE = new Set(['coordinates', 'resolved_from', 'merge_band', 'breakdown'])

/** The case AGAINST, computed: what the two records actually disagree about, plus every
 *  merge signal the resolver scored at exactly zero. Returns [] when nothing separates them —
 *  the card then says so rather than manufacturing a doubt. */
export function mergeDiffersOn(
  left: NodeView | undefined,
  right: NodeView | undefined,
  breakdown: Record<string, number>,
): string[] {
  const out: string[] = []
  if (left && right && left.type !== right.type) {
    out.push(`Type — ${humanizeToken(left.type)} vs ${humanizeToken(right.type)}.`)
  }

  const lRaw = left?.location?.raw ?? null
  const rRaw = right?.location?.raw ?? null
  if (lRaw && rRaw && lRaw.trim().toLowerCase() !== rRaw.trim().toLowerCase()) {
    out.push(`Stated location — “${lRaw}” vs “${rRaw}”.`)
  } else if (lRaw && !rRaw) {
    out.push(`Stated location — “${lRaw}” on one side, none recorded on the other.`)
  } else if (rRaw && !lRaw) {
    out.push(`Stated location — “${rRaw}” on one side, none recorded on the other.`)
  }

  const lLat = left?.location?.wgs84_lat
  const lLon = left?.location?.wgs84_lon
  const rLat = right?.location?.wgs84_lat
  const rLon = right?.location?.wgs84_lon
  if (
    typeof lLat === 'number' && typeof lLon === 'number' &&
    typeof rLat === 'number' && typeof rLon === 'number'
  ) {
    const km = haversineKm(lLat, lLon, rLat, rLon)
    if (km >= 1) out.push(`Coordinates — ${Math.round(km).toLocaleString()} km apart.`)
  }

  const lAttrs = left?.attrs ?? {}
  const rAttrs = right?.attrs ?? {}
  for (const key of Object.keys(lAttrs)) {
    if (ATTR_NOT_A_DIFFERENCE.has(key) || !(key in rAttrs)) continue
    const a = scalarAttr(lAttrs[key])
    const b = scalarAttr(rAttrs[key])
    if (a != null && b != null && a !== b) out.push(`${humanizeToken(key)} — ${a} vs ${b}.`)
  }

  for (const [key, score] of Object.entries(breakdown)) {
    if (score !== 0) continue
    out.push(MERGE_SIGNAL_ABSENT[key] ?? `No ${humanizeToken(key)} signal.`)
  }
  return out
}

export function viewToReviewQueue(view: GraphView): LiveReviewItem[] {
  const items: LiveReviewItem[] = []
  const nodeIndex = new Map(view.nodes.map((n) => [n.id, n]))
  const nodeLabel = (id: string): string => nodeIndex.get(id)?.name ?? id
  const edgeIndex = new Map(view.edges.map((e) => [e.id, e]))

  // How many real (assertional) edges hang off each node — "what reconnects if you merge".
  // Identity/version links are excluded: merging does not re-point a same-as onto anything.
  const degree = new Map<string, number>()
  for (const edge of view.edges) {
    if (isStatuslessEdge(edge)) continue
    degree.set(edge.source, (degree.get(edge.source) ?? 0) + 1)
    degree.set(edge.target, (degree.get(edge.target) ?? 0) + 1)
  }

  // 1. Identity merges — a same-as edge is a live "are these one record or two?". The row
  //    names both candidates; the card carries the resolver's own per-signal case.
  for (const edge of view.edges) {
    if (edge.type !== 'same-as') continue
    const leftNode = nodeIndex.get(edge.source)
    const rightNode = nodeIndex.get(edge.target)
    const left = reviewSide(edge.source, leftNode)
    const right = reviewSide(edge.target, rightNode)
    const breakdown = attrsBreakdown(edge)
    const dots = edge.merge_confidence != null ? credibilityToDots(edge.merge_confidence) : undefined
    const band = dots != null ? (MERGE_BAND[dots] ?? 'Close call') : 'Confidence not recorded'

    const matchedOn: MergeSignalRow[] = Object.entries(breakdown)
      .filter(([, score]) => score > 0)
      .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
      .map(([key, score]) => ({
        key,
        label: MERGE_SIGNAL_LABEL[key] ?? humanizeToken(key),
        score,
        dots: credibilityToDots(score),
      }))
    const differsOn = mergeDiffersOn(leftNode, rightNode, breakdown)

    const joinedClaims = new Set([...(leftNode?.claim_ids ?? []), ...(rightNode?.claim_ids ?? [])]).size
    const reconnects = (degree.get(edge.source) ?? 0) + (degree.get(edge.target) ?? 0)
    const consequence = [
      `Joins ${joinedClaims} sourced claim${joinedClaims === 1 ? '' : 's'} onto one record (${left.label} ${left.claimCount}, ${right.label} ${right.claimCount}).`,
      `${reconnects} graph edge${reconnects === 1 ? ' re-points' : 's re-point'} at the merged record.`,
    ]
    if (left.chokepoint || right.chokepoint) {
      const which = left.chokepoint && right.chokepoint ? 'Both records are' : `${(left.chokepoint ? left : right).label} is a`
      consequence.push(`${which} candidate chokepoint — merging changes what the chokepoint set contains.`)
    }
    // NEVER a predicted status. Statuses are recomputed by rebuild() from the joined claim set;
    // printing a number here would be exactly the fabricated consequence the brief disqualifies.
    const unknowns = [
      `Status is recomputed at rebuild from the joined claims — this card does not predict what ${left.label} and ${right.label} become.`,
    ]

    items.push({
      itemId: `merge:${edge.id}`,
      reviewType: 'merge',
      hitlVerb: 'merge',
      subject: edge.id,
      kicker: left.type === right.type ? `Merge · ${humanizeToken(left.type)}` : `Merge · ${humanizeToken(left.type)} ↔ ${humanizeToken(right.type)}`,
      title: `${left.label} ↔ ${right.label}`,
      question: 'Same system, or two?',
      note:
        edge.merge_confidence != null
          ? `identity match ${edge.merge_confidence.toFixed(2)} · ${matchedOn.length} of ${Object.keys(breakdown).length || 4} signals`
          : 'identity match not recorded',
      badge: band,
      badges: [band, ...(left.chokepoint || right.chokepoint ? ['Touches a chokepoint'] : [])],
      material: left.chokepoint || right.chokepoint,
      confidence: edge.merge_confidence ?? null,
      options: MERGE_OPTIONS,
      context: {
        summary: `${left.label} and ${right.label} may be one record.`,
        left: { id: edge.source, label: left.label },
        right: { id: edge.target, label: right.label },
        dots,
        merge: { confidence: edge.merge_confidence ?? null, matchedOn, differsOn, consequence, unknowns, left, right },
      },
    })
  }

  // 2. Status overrides — an assessment carrying opposing claims or a contradicted status.
  const assessed: Array<NodeView | EdgeView> = [...view.nodes, ...view.edges]
  for (const el of assessed) {
    const opposing = el.opposing_claims ?? []
    const contradicted = el.status === 'contradicted'
    if (opposing.length === 0 && !contradicted) continue
    const isNode = 'name' in el
    const label = isNode ? ((el as NodeView).name ?? el.id) : displayNameOf(view, el.id)
    const type = isNode ? (el as NodeView).type : (el as EdgeView).type
    const material = isNode ? isChokepoint(el as NodeView) : false
    const badge = contradicted ? 'Contradiction' : 'Close call'
    items.push({
      itemId: `ovr:${el.id}`,
      reviewType: 'status-override',
      hitlVerb: 'status',
      subject: el.id,
      kicker: `Status override · ${humanizeToken(type)}`,
      title: label,
      question: 'Is this really confirmed?',
      note: contradicted
        ? `reads contradicted — credible sources disagree`
        : `reads ${el.status ?? 'unset'} · ${opposing.length} opposing claim${opposing.length === 1 ? '' : 's'}`,
      badge,
      badges: [badge, ...(material ? ['Touches a chokepoint'] : [])],
      material,
      confidence: el.confidence?.assertion_confidence ?? null,
      options: OVERRIDE_OPTIONS,
      context: {
        summary: `${label} reads ${el.status ?? 'unset'} — ${
          opposing.length ? `${opposing.length} opposing claim${opposing.length === 1 ? '' : 's'} on file` : 'a contradiction routed it to you'
        }.`,
        detail: opposing,
        consequence: [
          `Overriding sets ${label}'s status by hand and propagates it — every answer that walks through ${label} is re-answered from the new status.`,
        ],
        unknowns: [
          'How many downstream answers change is not counted here — it depends on which questions get asked.',
        ],
      },
    })
  }

  // 3. Alert dispositions — a tripwire fired and hasn't been adjudicated yet. The card
  //    carries the firing's own provenance so "is it real?" is answerable from evidence
  //    rather than from the assertion that something changed.
  for (const alert of view.alerts) {
    if (alert.disposition != null) continue
    const subject = alert.subject ?? alert.observable_id
    const firing = alertToFiring(alert, edgeIndex)
    const observable = humanizeObservableId(alert.observable_id)
    const subjectName = alert.subject ? nodeLabel(alert.subject) : null
    const material = alert.subject ? isChokepoint(nodeIndex.get(alert.subject)) : false
    items.push({
      itemId: `alrt:${firing.key}`,
      reviewType: 'alert-disposition',
      hitlVerb: 'alert',
      subject,
      kicker: `Alert · ${observable.toLowerCase()}`,
      title: subjectName ? `${observable} · ${subjectName}` : observable,
      question: 'A tripwire fired. Is it real?',
      note: firing.changed
        ? `${firing.changed.from || '—'} → ${firing.changed.to || '—'}`
        : firing.firedTs
          ? `fired ${firing.firedTs}`
          : 'fired · no before/after recorded',
      badge: 'First seen',
      badges: ['First seen', ...(alert.severity ? [alert.severity] : []), ...(material ? ['Touches a chokepoint'] : [])],
      material,
      confidence: firing.provenance?.assertionConfidence ?? null,
      options: ALERT_OPTIONS,
      context: {
        // named, not keyed: "Basing relocation fired on HQ-9B battery", not "obs-basing-relocation
        // fired on unit_hq9b". nodeLabel falls back to the id when the graph has no name for it.
        summary: `Tripwire ${observable} fired${subjectName ? ` on ${subjectName}` : ''}.`,
        changed: firing.changed ?? undefined,
        severity: alert.severity,
        provenance: firing.provenance,
        holdReasons: firing.holdReasons,
        consequence: [
          'Accepting records the change as real; dismissing marks it noise. Either way the disposition is written back and feeds tripwire tuning.',
        ],
        unknowns: firing.provenance
          ? []
          : ['No evidence was recorded for this firing — there is nothing to open behind it.'],
      },
    })
  }

  return items
}

// ───────────────── queue triage: deterministic order + identity clustering ─────────────────
// A wall of near-identical proposals defeats attention-triage as thoroughly as no queue at all.
// Two moves, neither of which removes or auto-decides ANYTHING (spine/05: escalation recall
// stays ≈ 1.0 — the job is to make the escalation legible, not smaller):
//
//   1. ORDER — the ★ control points lead in the backend's own deterministic priority
//      (hitl/triage STAR_TYPES + star_priority), then materiality, then confidence. No LLM,
//      no clock: the same view always yields the same order (the demo must replay identically).
//   2. CLUSTER — merge proposals that share a record are one connected identity question, not
//      N unrelated ones. They are grouped under a header that STATES the shape of the cluster
//      (how many records, how many of the possible pairs are proposed); every member row is
//      still individually present and individually decidable underneath it.

/** Backend hitl/triage.TriageConfig.star_priority — mirrored so the client cannot drift from it. */
const STAR_PRIORITY: Record<LiveReviewType, number> = {
  'status-override': 0,
  merge: 1,
  'alert-disposition': 2,
}

/** Smallest cluster worth collapsing. Two proposals are a pair, not a blob. */
const CLUSTER_MIN_ITEMS = 3

export interface LiveReviewGroup {
  key: string
  kind: 'single' | 'cluster'
  kicker: string
  /** cluster only — what the cluster IS, counted: records involved, proposals, density */
  title: string
  note: string
  badges: string[]
  items: LiveReviewItem[]
  material: boolean
}

/** Deterministic analyst-presentation order: ★ priority, then materiality, then the most
 *  confident identity claim first (an unknown confidence sorts as urgent, never as safe). */
export function orderReviewQueue(items: LiveReviewItem[]): LiveReviewItem[] {
  return [...items].sort((a, b) => {
    const star = STAR_PRIORITY[a.reviewType] - STAR_PRIORITY[b.reviewType]
    if (star !== 0) return star
    if (a.material !== b.material) return a.material ? -1 : 1
    const ac = a.confidence ?? Number.POSITIVE_INFINITY
    const bc = b.confidence ?? Number.POSITIVE_INFINITY
    if (ac !== bc) return bc - ac
    return a.itemId.localeCompare(b.itemId)
  })
}

/** Union-find over the merge proposals' endpoints → connected identity clusters. */
function mergeComponents(items: LiveReviewItem[]): Map<string, string> {
  const parent = new Map<string, string>()
  const find = (x: string): string => {
    let root = parent.get(x) ?? x
    if (!parent.has(x)) parent.set(x, x)
    while (root !== (parent.get(root) ?? root)) root = parent.get(root) ?? root
    return root
  }
  const union = (a: string, b: string) => {
    const ra = find(a)
    const rb = find(b)
    if (ra !== rb) parent.set(ra, rb)
  }
  for (const item of items) {
    const l = item.context.left?.id
    const r = item.context.right?.id
    if (l && r) union(l, r)
  }
  const out = new Map<string, string>()
  for (const item of items) {
    const l = item.context.left?.id
    if (l) out.set(item.itemId, find(l))
  }
  return out
}

/** The queue as an analyst should meet it: ordered, with runs of connected identity proposals
 *  collapsed into one cluster each. Nothing is dropped — `groups.flatMap(g => g.items)` is a
 *  permutation of the input. */
export function groupReviewQueue(items: LiveReviewItem[]): LiveReviewGroup[] {
  const ordered = orderReviewQueue(items)
  const merges = ordered.filter((i) => i.reviewType === 'merge')
  const component = mergeComponents(merges)

  const clusters = new Map<string, LiveReviewItem[]>()
  for (const item of merges) {
    const key = component.get(item.itemId)
    if (!key) continue
    const bucket = clusters.get(key)
    if (bucket) bucket.push(item)
    else clusters.set(key, [item])
  }

  const groups: LiveReviewGroup[] = []
  const clustered = new Set<string>()
  for (const [key, members] of clusters) {
    if (members.length < CLUSTER_MIN_ITEMS) continue
    members.forEach((m) => clustered.add(m.itemId))
    const records = new Set<string>()
    for (const m of members) {
      if (m.context.left) records.add(m.context.left.id)
      if (m.context.right) records.add(m.context.right.id)
    }
    const n = records.size
    const possiblePairs = (n * (n - 1)) / 2
    const complete = members.length >= possiblePairs && possiblePairs > 0
    const names = members
      .flatMap((m) => [m.context.merge?.left, m.context.merge?.right])
      .filter((s): s is LiveReviewSide => s != null)
    const uniqueNames = [...new Map(names.map((s) => [s.id, s.label])).values()]
    const type = members[0].context.merge?.left.type
    // The density is the finding: when every possible pair is proposed, the proposals are not
    // independent evidence, and saying so is the difference between 28 decisions and one.
    const note = complete
      ? `every one of the ${possiblePairs} possible pairs is proposed — these are not independent proposals`
      : `${members.length} of ${possiblePairs} possible pairs proposed — ${uniqueNames.slice(0, 3).join(', ')}${uniqueNames.length > 3 ? `, +${uniqueNames.length - 3}` : ''}`
    const cluster = { size: members.length, records: n, complete, note }
    groups.push({
      key: `cluster:${key}`,
      kind: 'cluster',
      kicker: `Identity cluster${type ? ` · ${humanizeToken(type)}` : ''}`,
      title: `${n} records, ${members.length} merge proposals`,
      note,
      badges: members.some((m) => m.material) ? ['Touches a chokepoint'] : [],
      // members carry their cluster with them, so the card the analyst opens says the same
      // thing the group header said — the proposal is one of a connected run.
      items: members.map((m) => ({ ...m, cluster })),
      material: members.some((m) => m.material),
    })
  }

  for (const item of ordered) {
    if (clustered.has(item.itemId)) continue
    groups.push({
      key: item.itemId,
      kind: 'single',
      kicker: item.kicker,
      title: item.title,
      note: item.note,
      badges: item.badges,
      items: [item],
      material: item.material,
    })
  }

  // Group order: ★ priority of the lead item, materiality, then SMALL first — a crisp two-record
  // decision is answerable now; a large cluster is one systemic question that can be met as a
  // unit. Ties break on key so the order replays identically.
  return groups.sort((a, b) => {
    const star = STAR_PRIORITY[a.items[0].reviewType] - STAR_PRIORITY[b.items[0].reviewType]
    if (star !== 0) return star
    if (a.material !== b.material) return a.material ? -1 : 1
    if (a.items.length !== b.items.length) return a.items.length - b.items.length
    const ac = a.items[0].confidence ?? Number.POSITIVE_INFINITY
    const bc = b.items[0].confidence ?? Number.POSITIVE_INFINITY
    if (ac !== bc) return bc - ac
    return a.key.localeCompare(b.key)
  })
}
