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

/** "500 m" / "15 km" — the uncertainty envelope, in the unit a reader thinks in. */
export function formatRadius(metres: number): string {
  return metres >= 1000 ? `${Math.round(metres / 1000)} km` : `${Math.round(metres)} m`
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
  /** gazetteer precision class — pad | site | terminal | district | city | province */
  precision?: string | null
  /** radius of the honest uncertainty envelope around the drawn point, in metres */
  uncertaintyRadiusM?: number | null
  /** 'stated-coordinate' (the source gave a position) | 'gazetteer-anchor' (we looked the
   *  place up). Two very different claims; the map must not draw them identically. */
  locationSource?: string | null
  /** node ids folded into this marker when several entities share one area anchor */
  members?: string[]
}

export type StagePin = PinDef & StagePinExtras

// Which precision classes denote a POINT and which denote an AREA. This is the whole
// honesty rule of the map in one table: a pad/site/terminal is a thing you could put a
// reticle on, so it gets a pin; a district/city/province is a region a source vaguely
// gestured at, so it gets an envelope and a deliberately unpinned centroid marker.
// Drawing "somewhere in Punjab" as a sharp dot would assert ~150 km of precision nobody
// ever claimed — the exact class of fabrication this system is not allowed to commit.
export const AREA_PRECISIONS = new Set(['district', 'city', 'province'])

/** Does this pin denote a region rather than a point? Unknown precision is treated as a
 *  point only when the coordinate was stated by a source; an anchor-derived point with no
 *  precision class is an area, because we cannot say how big it is. */
export function isAreaPin(pin: StagePin): boolean {
  if (pin.precision) return AREA_PRECISIONS.has(pin.precision)
  return pin.locationSource === 'gazetteer-anchor'
}

// Node attrs the backend stamps alongside the location (view/pipeline.py). Read by name
// rather than typed into GraphView, matching how place_match_* is already carried.
const ATTR_LOCATION_SOURCE = 'location_source'
const ATTR_UNCERTAINTY_RADIUS = 'location_uncertainty_radius_m'

function numAttr(node: NodeView, key: string): number | null {
  const v = node.attrs?.[key]
  return typeof v === 'number' && Number.isFinite(v) ? v : null
}

function strAttr(node: NodeView, key: string): string | null {
  const v = node.attrs?.[key]
  return typeof v === 'string' && v.length > 0 ? v : null
}

/** A node the graph KNOWS has a location, and that we cannot honestly draw.
 *  "Insufficient evidence to place" is a legitimate output — but only if it is
 *  visible. Silently omitting these would let the map imply the graph is smaller
 *  than it is, which is the same lie as a fabricated pin, told the other way. */
export interface UnplacedLocation {
  id: string
  label: string
  /** what the source actually said — the reason it cannot be resolved to a point */
  stated: string
  type: string
}

/** Located-but-unplottable nodes: a location was asserted, no coordinate survives it. */
export function unplacedLocations(view: GraphView): UnplacedLocation[] {
  const out: UnplacedLocation[] = []
  for (const node of view.nodes) {
    const loc = node.location
    if (!loc) continue
    if (typeof loc.wgs84_lat === 'number' && typeof loc.wgs84_lon === 'number') continue
    const raw = loc.raw
    const stated = typeof raw === 'string' ? raw : Array.isArray(raw) ? raw.join('; ') : ''
    if (!stated) continue
    out.push({ id: node.id, label: node.name ?? node.id, stated, type: node.type })
  }
  return out.sort((a, b) => a.label.localeCompare(b.label))
}

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

    // The reticle readout states the point AND how well we know it. Showing the surface
    // format alone (the old behaviour) hid the coordinate; showing the coordinate alone
    // hides that it may be a 150 km province centroid. Both, always, when both are known.
    const surface = node.location?.surface_format
    const radiusM = numAttr(node, ATTR_UNCERTAINTY_RADIUS)
    const coord =
      formatCoord(lat, lon) +
      (typeof surface === 'string' && surface.length > 0 ? `  ${surface}` : '') +
      (radiusM !== null ? `  ±${formatRadius(radiusM)}` : '')
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
      precision: node.location?.precision_class ?? null,
      uncertaintyRadiusM: numAttr(node, ATTR_UNCERTAINTY_RADIUS),
      locationSource: strAttr(node, ATTR_LOCATION_SOURCE),
    })
  }
  return pins
}

/** Fold AREA pins that share one anchor into a single marker (a "clutter cluster").
 *
 *  Three different entities all reported as being "in Punjab" resolve to the same province
 *  centroid, and there are only two ways to draw that. Fanning them out around the centroid
 *  invents three positions nobody stated. Stacking them hides two of the three. So they are
 *  drawn as what they are: ONE area, with a count — the marker says "we know of 3 things here
 *  and cannot separate them", which is exactly the state of the evidence.
 *
 *  Point pins (pad/site/terminal) are never clustered: those ARE distinguishable positions.
 *  Deterministic — members sort by id, the survivor is the first, and the key is the exact
 *  coordinate pair, so two anchors that merely sit near each other stay separate.
 */
export function clusterAreaPins(pins: StagePin[]): StagePin[] {
  const groups = new Map<string, StagePin[]>()
  const out: StagePin[] = []
  for (const pin of pins) {
    if (!isAreaPin(pin)) {
      out.push(pin)
      continue
    }
    const key = `${pin.lat},${pin.lon},${pin.uncertaintyRadiusM ?? ''}`
    groups.set(key, [...(groups.get(key) ?? []), pin])
  }
  for (const group of groups.values()) {
    const members = [...group].sort((a, b) => a.id.localeCompare(b.id))
    const head = members[0]
    if (members.length === 1) {
      out.push({ ...head, members: [head.id] })
      continue
    }
    out.push({
      ...head,
      label: `${members.length} entities`,
      caption: 'located to this area only',
      members: members.map((m) => m.id),
    })
  }
  return out
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
        // named, not keyed: "Basing relocation fired on HQ-9B battery", not "obs-basing-relocation
        // fired on unit_hq9b". nodeLabel falls back to the id when the graph has no name for it.
        summary: `Tripwire ${humanizeObservableId(alert.observable_id)} fired${
          alert.subject ? ` on ${nodeLabel(alert.subject)}` : ''
        }.`,
        changed: firing.changed ?? undefined,
        severity: alert.severity,
        provenance: firing.provenance,
        holdReasons: firing.holdReasons,
      },
    })
  }

  return items
}
