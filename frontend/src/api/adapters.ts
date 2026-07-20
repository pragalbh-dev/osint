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
    case 'contradicted':
      return 'gap'
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
 *  5. `contradicted` is its own thing — sources disagree, which is a problem, not a gap. */
export function edgeToKind(edge: EdgeView): EdgeKind {
  if (edge.type === 'supersedes') return 'e-supersede'
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

/** Nodes without a resolved location live only in the graph, not on the map. */
export function viewToPins(view: GraphView): PinDef[] {
  const pins: PinDef[] = []
  for (const node of view.nodes) {
    const lat = node.location?.wgs84_lat
    const lon = node.location?.wgs84_lon
    if (typeof lat !== 'number' || !Number.isFinite(lat)) continue
    if (typeof lon !== 'number' || !Number.isFinite(lon)) continue

    const surface = node.location?.surface_format
    const coord = typeof surface === 'string' && surface.length > 0 ? surface : formatCoord(lat, lon)
    const year = yearOf(node.freshness?.last_support_time)

    pins.push({
      id: node.id,
      label: node.name ?? node.id,
      lat,
      lon,
      coord,
      status: node.status ?? 'insufficient',
      caption: year !== null ? `as of ${year}` : '',
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
        docRefs: docRefsOf(claim.doc_ref),
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
  return edge.replace(/[-_]/g, ' ').trim()
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
}

export interface LiveReviewItem {
  itemId: string // stable per-item key (de-dup + decided tracking)
  reviewType: LiveReviewType // HitlDecision.type
  hitlVerb: 'merge' | 'status' | 'alert' // which /hitl/* route
  subject: string // the element's own id → HitlDecision.subject
  kicker: string // small type label in the rail
  title: string // one-line question
  badge: string // priority-ish chip
  options: LiveReviewOption[]
  context: LiveReviewContext
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

export function viewToReviewQueue(view: GraphView): LiveReviewItem[] {
  const items: LiveReviewItem[] = []
  const nodeLabel = (id: string): string => view.nodes.find((n) => n.id === id)?.name ?? id
  const edgeIndex = new Map(view.edges.map((e) => [e.id, e]))

  // 1. Identity merges — a same-as edge is a live "are these one record or two?".
  for (const edge of view.edges) {
    if (edge.type !== 'same-as') continue
    items.push({
      itemId: `merge:${edge.id}`,
      reviewType: 'merge',
      hitlVerb: 'merge',
      subject: edge.id,
      kicker: 'Merge',
      title: 'Same system, or two?',
      badge: 'Close call',
      options: MERGE_OPTIONS,
      context: {
        summary: `${nodeLabel(edge.source)} and ${nodeLabel(edge.target)} may be one record.`,
        left: { id: edge.source, label: nodeLabel(edge.source) },
        right: { id: edge.target, label: nodeLabel(edge.target) },
        dots: edge.merge_confidence != null ? credibilityToDots(edge.merge_confidence) : undefined,
      },
    })
  }

  // 2. Status overrides — an assessment carrying opposing claims or a contradicted status.
  const assessed: Array<NodeView | EdgeView> = [...view.nodes, ...view.edges]
  for (const el of assessed) {
    const opposing = el.opposing_claims ?? []
    const contradicted = el.status === 'contradicted'
    if (opposing.length === 0 && !contradicted) continue
    const label = 'name' in el ? (el.name ?? el.id) : el.id
    items.push({
      itemId: `ovr:${el.id}`,
      reviewType: 'status-override',
      hitlVerb: 'status',
      subject: el.id,
      kicker: 'Status override',
      title: 'Is this really confirmed?',
      badge: contradicted ? 'Contradiction' : 'Close call',
      options: OVERRIDE_OPTIONS,
      context: {
        summary: `${label} reads ${el.status ?? 'unset'} — ${
          opposing.length ? `${opposing.length} opposing claim${opposing.length === 1 ? '' : 's'} on file` : 'a contradiction routed it to you'
        }.`,
        detail: opposing,
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
    items.push({
      itemId: `alrt:${firing.key}`,
      reviewType: 'alert-disposition',
      hitlVerb: 'alert',
      subject,
      kicker: 'Alert',
      title: 'A tripwire fired. Is it real?',
      badge: 'First seen',
      options: ALERT_OPTIONS,
      context: {
        summary: `Tripwire ${alert.observable_id} fired${alert.subject ? ` on ${alert.subject}` : ''}.`,
        changed: firing.changed ?? undefined,
        severity: alert.severity,
        provenance: firing.provenance,
        holdReasons: firing.holdReasons,
      },
    })
  }

  return items
}
