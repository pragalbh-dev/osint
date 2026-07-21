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
  SourceCard,
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
  /** the id of the `supersedes` edge itself, so the connector is one click from its evidence */
  supersedeEdgeId?: string | null
  /** WHAT moved — the subject of the underlying `based-at` assertion, named. NEVER the site: a
   *  site does not get "replaced", an occupant relocates. Null when the graph does not record one. */
  supersedeSubject?: string | null
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

/** `Location.raw` is `str | list[str]` on the backend (`schemas/values.py`) — a node may carry several
 *  surface statements of where it is. Flattened to one human string here so every reader agrees; joining
 *  rather than picking the first, because dropping the others would hide evidence the node actually has. */
export function locationRawText(raw: string | string[] | null | undefined): string {
  if (typeof raw === 'string') return raw
  if (Array.isArray(raw)) return raw.filter((r) => typeof r === 'string' && r.length > 0).join('; ')
  return ''
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
    const stated = locationRawText(loc.raw)
    if (!stated) continue
    out.push({ id: node.id, label: node.name ?? node.id, stated, type: node.type })
  }
  return out.sort((a, b) => a.label.localeCompare(b.label))
}

/** What a settled `supersedes` edge actually says, resolved into names.
 *
 *  The link the backend draws runs *site → site* (`credibility/supersession.py::_drawn_edge`), but it
 *  is a PROJECTION of a supersession that lives on a `based-at` edge: what was overtaken is the
 *  **occupant's basing**, not the site. Rendering the projection without naming the occupant asserts
 *  "PAF Base Nur Khan was replaced by Rahwali airfield", which is false — Nur Khan did not stop
 *  existing. So every consumer of this edge gets the subject with it, and the copy says what moved. */
export interface SupersessionFact {
  edgeId: string
  fromRef: string // the site left behind
  toRef: string // the site moved to
  subjectRef: string | null // the occupant that moved (attrs.subject on the drawn edge)
  olderEdgeId: string | null // the retired `based-at` assertion
  newerEdgeId: string | null // the assertion that replaced it
}

/** Every settled supersession in the view, keyed by the site that was left behind. */
export function supersessions(view: GraphView): Map<string, SupersessionFact> {
  const out = new Map<string, SupersessionFact>()
  for (const edge of view.edges) {
    if (edge.type !== 'supersedes') continue
    if (edgeToKind(edge) !== 'e-supersede') continue // candidate/pending/held → not settled
    const attrs = edge.attrs ?? {}
    out.set(edge.target, {
      edgeId: edge.id,
      fromRef: edge.target,
      toRef: edge.source,
      subjectRef: typeof attrs.subject === 'string' ? attrs.subject : null,
      olderEdgeId: typeof attrs.older_edge === 'string' ? attrs.older_edge : null,
      newerEdgeId: typeof attrs.newer_edge === 'string' ? attrs.newer_edge : null,
    })
  }
  return out
}

/** target-of-a-settled-`supersedes`-edge → the successor's node id. */
export function supersededSites(view: GraphView): Map<string, string> {
  return new Map([...supersessions(view)].map(([from, fact]) => [from, fact.toRef]))
}

/** Nodes without a resolved location live only in the graph, not on the map. */
export function viewToPins(view: GraphView): StagePin[] {
  const pins: StagePin[] = []
  const superseded = supersessions(view)
  const name = nameResolver(view)
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
    const fact = superseded.get(node.id)
    // The caption of a site that was left behind must be about the OCCUPANCY, not the site: the
    // site is still there. A bare "superseded" read as "this place was replaced", which is false.
    const subject = fact?.subjectRef ? name(fact.subjectRef) : null
    const vacated = subject ? `former ${subject} basing` : 'former basing on record'

    pins.push({
      id: node.id,
      label: node.name ?? node.id,
      lat,
      lon,
      coord,
      status: node.status ?? 'insufficient',
      caption: fact
        ? year !== null
          ? `${vacated} · ${year}`
          : vacated
        : year !== null
          ? `as of ${year}`
          : '',
      superseded: fact != null,
      supersededBy: fact?.toRef ?? null,
      supersedeEdgeId: fact?.edgeId ?? null,
      supersedeSubject: subject,
      precision: node.location?.precision_class ?? null,
      uncertaintyRadiusM: radiusM,
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
    // ontology type + bare name carried alongside the status `kind`: the graph stage
    // separates the knowledge layer from the evidence layer (`source` nodes) and lays
    // nodes out by supply-chain role, neither of which is derivable from `kind`.
    type: node.type,
    name: node.name ?? node.id,
  }))
}

export function viewToGraphEdges(view: GraphView): GraphEdgeDef[] {
  return view.edges.map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    kind: edgeToKind(edge),
    // ontology type kept alongside the status `kind`: `e-link` collapses `same-as` and
    // `distinct-from` into one treatment, but the graph stage has to tell a merge from a
    // hard veto, and domain relationships from resolution bookkeeping.
    type: edge.type,
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
  /** WHAT this claim asserts, in words, read straight off its payload (never a paraphrase, never
   *  generated). This is the proposition the status is a verdict on — a row that only said
   *  "observation · entity" told the analyst the claim's FILING CATEGORY and hid its content. */
  proposition: string
  /** the extra attributes the claim carries, as "label — value" lines. Same rule: verbatim values. */
  attrLines: string[]
  kindLabel: string // 'Observed' | 'Inferred' | 'Retracted' — kind, in analyst English
  detail: string // kindLabel + the claim form, e.g. "Observed · about an entity"
  /** short, per-claim locator suffix (e.g. "L22") so two claims from ONE document are told apart
   *  on the chip itself, not only in the expanded box. '' when the doc_ref carries no line/page/row. */
  locatorShort: string
  dates: { event?: string; reported?: string; ingested?: string }
  docRefs: DocRef[] // ALWAYS an array (normalize DocRef | DocRef[] → DocRef[]); the jump-to-source targets
  /** the VERBATIM text at each docRef, same order/length as `docRefs`. '' = unreadable span —
   *  the row then shows the locator alone. Never a paraphrase: this is the evidence itself. */
  quotes: string[]
  dots: number // 1..4 credibility tier
}

export interface LiveDrawerSource {
  sourceId: string
  /** the source's CLASS in analyst English ("Commercial satellite imagery"), from the registry's
   *  `source_type`. Never a publisher name: the registry does not carry one, so we do not invent one. */
  label: string
  grade?: string | null // STANAG reliability grade
  bias?: string | null
  reportDate?: string | null
  flags: string[] // registry gates worth surfacing (coordinated inauthenticity, adversary denial, …)
  known: boolean // false = this id is not in the source registry; show the bare id, claim nothing
}

export interface LiveDrawerCluster {
  groupId: string
  axis?: { origin?: string; discipline?: string; interest?: string }
  rows: LiveClaimRow[]
  /** the sources inside this look — the header attribution, so a per-claim chip no longer has to
   *  repeat (and thereby over-count) the document it came from. */
  sources: LiveDrawerSource[]
  /** true for the residual bucket: claims the response carried that NO independence group contains.
   *  They are cited evidence but were not counted as a look — saying so is the honest rendering;
   *  dropping them (the previous behaviour) silently hid every claim on a status-less edge. */
  ungrouped?: boolean
}

/** What the drawer is a verdict ABOUT, stated as a proposition. A status over a bare node name
 *  ("PAF Base Nur Khan is Probable") names no claim, so it cannot be judged. */
export interface LiveDrawerSubject {
  ref: string
  kind: 'node' | 'edge' | 'unknown'
  headline: string // the proposition, e.g. '"Rahwali airfield" exists, as a basing site'
  typeLabel: string // 'basing site' / 'based at' — the ontology type in analyst English
  /** true for edge types that carry NO status by design (`supersedes`, `same-as`, `distinct-from`).
   *  Rendering their null status as "insufficient evidence" claimed an evidence gap that does not
   *  exist — the link is simply not the kind of thing that gets scored. */
  statusless: boolean
  /** T10 — the raw ontology edge type, when this subject is an edge. The status-less family is not one
   *  thing: a `supersedes` records a change of state, a `same-as` is an unsettled identity question,
   *  and the drawer has to say which — one sentence cannot be true of both. */
  edgeType?: string
}

/** A relocation, told the way an analyst narrates it: what moved, from where, to where, and which
 *  two assertions the move is made of. Present only when the drawer's element IS the version link. */
export interface LiveDrawerSupersession {
  /** which side of the relocation the OPEN element is: the version link itself, the assertion that
   *  was overtaken, or the one that replaced it. The same three facts read differently from each. */
  role: 'link' | 'older' | 'newer'
  subjectName: string | null
  fromName: string
  toName: string
  olderEdgeId: string | null
  newerEdgeId: string | null
}

export interface LiveDrawerModel {
  subjectRef: string
  subject?: LiveDrawerSubject
  supersession?: LiveDrawerSupersession
  status: Status
  sources: number // count of DISTINCT source_id across claims
  looks: number // clusters.length (independent looks)
  claimCount: number // rows actually rendered — so the header arithmetic matches the body
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

// ── analyst English for the internal vocabulary ────────────────────────────────────────────────
// `observation · entity` names the claim's FILING CATEGORY, not its content. These maps translate
// the internal enums; anything unrecognised falls through to a humanised form of the raw token, so
// a new ontology type degrades to something readable instead of disappearing.

const KIND_LABEL: Record<ClaimKind, string> = {
  observation: 'Observed',
  inference: 'Inferred',
  retraction: 'Retracted',
}

const FORM_LABEL: Record<string, string> = {
  entity: 'about a thing',
  relationship: 'about a connection',
  event: 'about an event',
}

/** `source_type` → the source CLASS in analyst English. Not a publisher name — the registry has
 *  none, and inventing a masthead would be exactly the fabrication the non-negotiable forbids. */
const SOURCE_CLASS_LABEL: Record<string, string> = {
  satellite: 'Commercial satellite imagery',
  official: 'Official government statement',
  'trade-media': 'Trade press / defence media',
  'think-tank': 'Think-tank / analytic report',
  'curated-register': 'Curated reference register',
  'customs-tender': 'Customs / tender record',
  'exporter-state-media': 'Exporter-state media',
  'named-social': 'Named social-media account',
  'anon-social': 'Anonymous social-media post',
}

const REGISTRY_FLAG_LABEL: Record<string, string> = {
  coordinated_inauthenticity_flag: 'coordinated inauthenticity',
  adversary_denial_flag: 'adversary denial',
}

/** `basing_site` / `supplies-component` → `basing site` / `supplies component`. */
export function humanizeToken(token: string): string {
  return token.replace(/[-_]/g, ' ').trim()
}

export function claimKindLabel(kind: ClaimKind): string {
  return KIND_LABEL[kind] ?? humanizeToken(kind)
}

/** One doc_ref → the shortest handle that tells two claims from the same document apart. */
export function shortLocator(ref: DocRef | undefined): string {
  if (!ref) return ''
  if (ref.line != null) return `L${ref.line}`
  if (ref.page != null) return `p.${ref.page}`
  if (ref.row != null) return `row ${ref.row}`
  if (ref.frame != null) return `frame ${ref.frame}`
  if (ref.region) return ref.region
  if (ref.span) return `${ref.span[0]}–${ref.span[1]}`
  return ''
}

function scalarString(v: unknown): string | null {
  if (typeof v === 'string') return v.trim() || null
  if (typeof v === 'number' || typeof v === 'boolean') return String(v)
  return null
}

/** The claim's payload → the sentence it asserts. Every word comes from the payload or from the
 *  fixed vocabulary above; nothing is summarised, inferred or generated. Unknown payload shapes
 *  return '' and the caller shows the verbatim quote instead of a guess. */
export function claimProposition(claim: ClaimRecord, resolve: (id: string) => string = (i) => i): string {
  const p = claim.payload as Record<string, unknown> | undefined
  if (!p || typeof p !== 'object') return ''
  const negated = claim.polarity === 'negative'
  if (p.form === 'triple') {
    const subject = resolve(String(p.subject ?? ''))
    const object = resolve(String(p.object ?? ''))
    const predicate = humanizeToken(String(p.predicate ?? ''))
    if (!subject || !object) return ''
    return `${subject} ${negated ? 'is not' : 'is'} ${predicate} ${object}`.replace(/\s+/g, ' ')
  }
  if (p.form === 'entity') {
    const name = scalarString(p.name)
    const type = humanizeToken(String(p.entity_type ?? 'entity'))
    if (!name) return ''
    return negated ? `“${name}” is not a ${type}` : `“${name}” is a ${type}`
  }
  if (p.form === 'event') {
    const type = humanizeToken(String(p.event_type ?? 'event'))
    const parts = Array.isArray(p.participants) ? p.participants.map((x) => resolve(String(x))) : []
    return parts.length ? `${type} involving ${parts.join(', ')}` : type
  }
  return ''
}

/** The payload's own attributes as "label — value" lines. Scalars only: a nested object (a
 *  coordinate block, a geocode candidate list) is structure the drawer renders elsewhere, and
 *  flattening it here would produce noise that reads like content. */
export function claimAttrLines(claim: ClaimRecord): string[] {
  const p = claim.payload as Record<string, unknown> | undefined
  const attrs = p && typeof p === 'object' ? (p.attrs as Record<string, unknown> | undefined) : undefined
  if (!attrs || typeof attrs !== 'object') return []
  return Object.entries(attrs).reduce<string[]>((lines, [k, v]) => {
    const value = scalarString(v)
    if (value) lines.push(`${humanizeToken(k)} — ${value}`)
    return lines
  }, [])
}

/** A registry entry → the attribution the drawer shows. `known: false` means the id was not in the
 *  registry, and the UI must then say only the id: describing an unknown source is a fabrication. */
export function sourceCardToDisplay(sourceId: string, card: SourceCard | undefined): LiveDrawerSource {
  if (!card) return { sourceId, label: sourceId, flags: [], known: false }
  const flags = Object.entries(REGISTRY_FLAG_LABEL).reduce<string[]>((out, [key, label]) => {
    if ((card as unknown as Record<string, unknown>)[key] === true) out.push(label)
    return out
  }, [])
  return {
    sourceId,
    label: SOURCE_CLASS_LABEL[card.source_type] ?? humanizeToken(card.source_type),
    grade: card.reliability_grade ?? null,
    bias: card.bias_vector ? humanizeToken(card.bias_vector) : null,
    reportDate: card.report_date ?? null,
    flags,
    known: true,
  }
}

/** What the drawer's element actually asserts, resolved against the live view. Falls back to the
 *  bare ref when the view does not know the id — never to an invented description. */
export function drawerSubject(view: GraphView | null | undefined, ref: string): LiveDrawerSubject {
  const resolve = nameResolver(view)
  const node = view?.nodes.find((n) => n.id === ref)
  if (node) {
    const typeLabel = humanizeToken(node.type)
    return {
      ref,
      kind: 'node',
      headline: `“${node.name ?? node.id}” exists, as a ${typeLabel}`,
      typeLabel,
      statusless: false,
    }
  }
  const edge = view?.edges.find((e) => e.id === ref)
  if (edge) {
    const typeLabel = humanizeToken(edge.type)
    const statusless = isStatuslessEdge(edge)
    const src = resolve(edge.source)
    const dst = resolve(edge.target)
    if (edge.type === 'supersedes') {
      const subject = typeof edge.attrs?.subject === 'string' ? resolve(edge.attrs.subject) : null
      // The link runs site→site, but what was overtaken is the OCCUPANCY. Say so, or the arrow
      // reads "this base was replaced by that base", which is false.
      return {
        ref,
        kind: 'edge',
        headline: subject
          ? `${subject} moved from ${dst} to ${src} — the earlier basing is now history`
          : `The recorded basing moved from ${dst} to ${src} — the earlier one is now history`,
        typeLabel: 'replaced by',
        statusless,
        edgeType: edge.type,
      }
    }
    return { ref, kind: 'edge', headline: `${src} — ${typeLabel} → ${dst}`, typeLabel, statusless, edgeType: edge.type }
  }
  return { ref, kind: 'unknown', headline: ref, typeLabel: '', statusless: false }
}

/** The relocation behind a `supersedes` edge, named end to end — reachable from any of its three
 *  elements. Selecting the retired `based-at` assertion has to explain itself too: "stale" with no
 *  successor named is the same failure as "replaced by" with no subject named. */
export function drawerSupersession(
  view: GraphView | null | undefined,
  ref: string,
): LiveDrawerSupersession | undefined {
  const link = view?.edges.find((e) => {
    if (e.type !== 'supersedes') return false
    return e.id === ref || e.attrs?.older_edge === ref || e.attrs?.newer_edge === ref
  })
  if (!link) return undefined
  const resolve = nameResolver(view)
  const subject = typeof link.attrs?.subject === 'string' ? link.attrs.subject : null
  const olderEdgeId = typeof link.attrs?.older_edge === 'string' ? link.attrs.older_edge : null
  const newerEdgeId = typeof link.attrs?.newer_edge === 'string' ? link.attrs.newer_edge : null
  return {
    role: ref === olderEdgeId ? 'older' : ref === newerEdgeId ? 'newer' : 'link',
    subjectName: subject ? resolve(subject) : null,
    fromName: resolve(link.target), // target = the site the occupant left
    toName: resolve(link.source),
    olderEdgeId,
    newerEdgeId,
  }
}

/** Structured /evidence/{id} response → display model for the live provenance drawer.
 *
 *  `view` is optional: with it the drawer can state the PROPOSITION under assessment (and, for a
 *  `supersedes` link, what moved where); without it the model still renders, headed by the ref. */
export function evidenceToDrawerModel(data: ProvenanceDrawer, view?: GraphView | null): LiveDrawerModel {
  const claims = data.claims ?? []
  const claimsById = new Map<string, ClaimRecord>(claims.map((c) => [c.claim_id, c]))
  const clusters = data.clusters ?? []
  const resolve = nameResolver(view)
  const cards = data.sources ?? {}

  const sourceIds = new Set(claims.map((c) => c.source_id))

  const rowFor = (claim: ClaimRecord): LiveClaimRow => {
    const refs = docRefsOf(claim.doc_ref)
    const quotes = data.quotes?.[claim.claim_id] ?? []
    const kindLabel = claimKindLabel(claim.kind)
    return {
      claimId: claim.claim_id,
      sourceId: claim.source_id,
      kind: claim.kind,
      proposition: claimProposition(claim, resolve),
      attrLines: claimAttrLines(claim),
      kindLabel,
      detail: [kindLabel, FORM_LABEL[claim.asserts] ?? humanizeToken(claim.asserts)]
        .filter(Boolean)
        .join(' · '),
      locatorShort: shortLocator(refs[0]),
      dates: {
        event: dateValueToString(claim.event_time),
        reported: dateValueToString(claim.report_time),
        ingested: dateValueToString(claim.ingest_time),
      },
      docRefs: refs,
      // pad/trim to docRefs length so index i always answers "what does ref i say?"
      quotes: refs.map((_, i) => quotes[i] ?? ''),
      dots: credibilityToDots(data.confidence?.per_claim_credibility?.[claim.claim_id]),
    }
  }

  /** Two claims lifted from the SAME line of the same document collide on `L22`. Fall through to
   *  the character span for exactly those, so no two chips in one look ever read identically —
   *  the defect this replaces was three indistinguishable chips over three different claims. */
  const disambiguate = (rows: LiveClaimRow[]): LiveClaimRow[] => {
    const seen = new Map<string, number>()
    for (const r of rows) {
      const key = `${r.sourceId}|${r.locatorShort}`
      seen.set(key, (seen.get(key) ?? 0) + 1)
    }
    return rows.map((r) => {
      if ((seen.get(`${r.sourceId}|${r.locatorShort}`) ?? 0) < 2) return r
      const span = r.docRefs[0]?.span
      return span ? { ...r, locatorShort: `${r.locatorShort} · ${span[0]}–${span[1]}` } : r
    })
  }

  const sourcesOf = (rows: LiveClaimRow[]): LiveDrawerSource[] =>
    [...new Set(rows.map((r) => r.sourceId))].map((id) => sourceCardToDisplay(id, cards[id]))

  const grouped = new Set<string>()
  const liveClusters: LiveDrawerCluster[] = clusters.map((group) => {
    const rows = disambiguate(
      group.claim_ids.reduce<LiveClaimRow[]>((acc, claimId) => {
        const claim = claimsById.get(claimId)
        if (!claim) return acc
        grouped.add(claimId)
        acc.push(rowFor(claim))
        return acc
      }, []),
    )
    return {
      groupId: group.group_id,
      axis: group.axis_key
        ? {
            origin: group.axis_key.origin,
            discipline: group.axis_key.discipline,
            interest: group.axis_key.interest,
          }
        : undefined,
      rows,
      sources: sourcesOf(rows),
    }
  })

  // Residual bucket: claims the response cited that no independence group contains. On a status-less
  // edge (a `supersedes` version link) EVERY claim lands here, and the previous model dropped them —
  // the drawer showed an element with three citations as if it had none.
  const loose = disambiguate(claims.filter((c) => !grouped.has(c.claim_id)).map(rowFor))
  if (loose.length) {
    liveClusters.push({ groupId: 'ungrouped', rows: loose, sources: sourcesOf(loose), ungrouped: true })
  }

  const subject = drawerSubject(view, data.subject_ref)
  return {
    subjectRef: data.subject_ref,
    subject,
    supersession: drawerSupersession(view, data.subject_ref),
    status: data.status ?? 'insufficient',
    sources: sourceIds.size,
    looks: clusters.length,
    claimCount: liveClusters.reduce((n, c) => n + c.rows.length, 0),
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

/** Turn one answer hop into the graph element whose provenance backs it — the EDGE the hop crossed,
 *  chosen so its claim set contains the hop's own citations. Endpoints match in EITHER direction (the
 *  walk can cross an edge against its stored source→target orientation); when several edges of that
 *  type join the pair, the one that actually carries a cited claim wins. Falls back to the destination
 *  node (a real provenance target in its own right) when no edge resolves, and null when even that is
 *  unknown — a null MUST leave the chip inert, never open a drawer that would 404 into a false
 *  "insufficient evidence". */
export function resolveHopElement(
  view: GraphView | null | undefined,
  hop: { src: string; dst: string; edge: string; citations?: string[] },
): string | null {
  if (!view) return null
  const cited = new Set(hop.citations ?? [])
  const matches = view.edges.filter(
    (e) =>
      e.type === hop.edge &&
      ((e.source === hop.src && e.target === hop.dst) ||
        (e.source === hop.dst && e.target === hop.src)),
  )
  if (matches.length) {
    const byClaim = matches.find((e) => (e.claim_ids ?? []).some((c) => cited.has(c)))
    return (byClaim ?? matches[0]).id
  }
  return view.nodes.some((n) => n.id === hop.dst) ? hop.dst : null
}

/** claim_id → the element (edge preferred over node) whose provenance drawer holds it. Lets a loose
 *  citation that is not attached to a hop still open on its exact claim. A claim backs a relationship
 *  more often than a bare entity, so an edge binding overrides a node one for the same id. */
export function claimElementIndex(view: GraphView | null | undefined): Map<string, string> {
  const idx = new Map<string, string>()
  if (!view) return idx
  for (const n of view.nodes) for (const c of n.claim_ids ?? []) if (!idx.has(c)) idx.set(c, n.id)
  for (const e of view.edges) for (const c of e.claim_ids ?? []) idx.set(c, e.id)
  return idx
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
  /** T10 — the element whose provenance drawer IS this signal's evidence. Set only for
   *  `source_asserted`, and only when the candidate `same-as` edge actually cites claims: three of the
   *  four signals are the resolver's own computation over the two records and have no source to open.
   *  Absent ⇒ the card renders the row as plain text (never a dead link). */
  evidenceId?: string
  /** how many claims that drawer will hold — the count is the handle, so the chip says what it opens */
  evidenceCount?: number
}

/** T10 — one line of the case AGAINST, with where it came from.
 *
 *  The card states differences an analyst is about to act on, so each line has to declare its own
 *  standing. `sides` names the record(s) whose *stated* values the line reads (each opens that record's
 *  evidence); `computed` is set instead when the line is the machine's own arithmetic or the resolver's
 *  own signal, and carries the sentence that says so. Never both — a computation dressed as a citation
 *  is the failure mode this whole card exists to avoid. */
export interface MergeDiffRow {
  text: string
  sides: ('left' | 'right')[]
  computed?: string
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
  /** T10 — the same lines as `differsOn`, each carrying its provenance (see MergeDiffRow).
   *  `differsOn` is kept as the plain-text projection so every existing reader is untouched. */
  differs: MergeDiffRow[]
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
  /** T10 — the id `GET /evidence/{id}` resolves for this record. Set only when the record is really a
   *  node in the view we are reading; absent ⇒ the card shows the panel as text, never as a dead link. */
  evidenceId?: string
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

/** The one merge signal that is a SOURCE's assertion rather than the resolver's own computation over
 *  the two records — and therefore the only one with evidence to open (resolve/rconfig SOURCE_ASSERTED). */
const MERGE_SIGNAL_SOURCE_ASSERTED = 'source_asserted'

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

// `humanizeToken` is defined once above (T6). T3a independently wrote a byte-identical helper and the
// merge kept both; the duplicate is dropped rather than renamed, since the implementations agree.

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
    evidenceId: node ? id : undefined,
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

/** T10 — how a computed line explains itself. The two records' *stated* values are attributable (to the
 *  record, which is as far as the view can honestly go: node attrs are merged from a node's claims and
 *  the view does not record which claim supplied which key). Everything else says out loud that it is
 *  arithmetic or a resolver signal, so no line on this card can be mistaken for a quotation. */
const DIFF_COMPUTED_DISTANCE = 'computed from both records’ stated coordinates — not a quoted claim'
const DIFF_COMPUTED_SIGNAL = 'the resolver’s own signal, scored at zero — an absence, not a quoted claim'

/** The case AGAINST, computed: what the two records actually disagree about, plus every
 *  merge signal the resolver scored at exactly zero. Returns [] when nothing separates them —
 *  the card then says so rather than manufacturing a doubt.
 *
 *  T10: each line now also carries **where it came from** — which record(s) state it, or the sentence
 *  admitting it was computed. `mergeDiffersOn` is the unchanged plain-text projection of this. */
export function mergeDifferences(
  left: NodeView | undefined,
  right: NodeView | undefined,
  breakdown: Record<string, number>,
): MergeDiffRow[] {
  const out: MergeDiffRow[] = []
  const both: ('left' | 'right')[] = ['left', 'right']
  if (left && right && left.type !== right.type) {
    out.push({ text: `Type — ${humanizeToken(left.type)} vs ${humanizeToken(right.type)}.`, sides: both })
  }

  const lRaw = locationRawText(left?.location?.raw)
  const rRaw = locationRawText(right?.location?.raw)
  if (lRaw && rRaw && lRaw.trim().toLowerCase() !== rRaw.trim().toLowerCase()) {
    out.push({ text: `Stated location — “${lRaw}” vs “${rRaw}”.`, sides: both })
  } else if (lRaw && !rRaw) {
    out.push({ text: `Stated location — “${lRaw}” on one side, none recorded on the other.`, sides: ['left'] })
  } else if (rRaw && !lRaw) {
    out.push({ text: `Stated location — “${rRaw}” on one side, none recorded on the other.`, sides: ['right'] })
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
    if (km >= 1) {
      out.push({
        text: `Coordinates — ${Math.round(km).toLocaleString()} km apart.`,
        sides: both,
        computed: DIFF_COMPUTED_DISTANCE,
      })
    }
  }

  const lAttrs = left?.attrs ?? {}
  const rAttrs = right?.attrs ?? {}
  for (const key of Object.keys(lAttrs)) {
    if (ATTR_NOT_A_DIFFERENCE.has(key) || !(key in rAttrs)) continue
    const a = scalarAttr(lAttrs[key])
    const b = scalarAttr(rAttrs[key])
    if (a != null && b != null && a !== b) out.push({ text: `${humanizeToken(key)} — ${a} vs ${b}.`, sides: both })
  }

  for (const [key, score] of Object.entries(breakdown)) {
    if (score !== 0) continue
    out.push({
      text: MERGE_SIGNAL_ABSENT[key] ?? `No ${humanizeToken(key)} signal.`,
      sides: [],
      computed: DIFF_COMPUTED_SIGNAL,
    })
  }
  return out
}

/** Plain-text projection of {@link mergeDifferences} — the shape every pre-T10 reader expects. */
export function mergeDiffersOn(
  left: NodeView | undefined,
  right: NodeView | undefined,
  breakdown: Record<string, number>,
): string[] {
  return mergeDifferences(left, right, breakdown).map((row) => row.text)
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

    // T10 — the ONE signal on this card that is somebody's assertion rather than the resolver's own
    // arithmetic is `source_asserted`, and the candidate edge now cites the claims that make it
    // (view/pipeline._resolution_edges). So that row, and only that row, gets an evidence handle: the
    // edge's own id, which `GET /evidence/{id}` already serves. No handle when no source spoke — the
    // absence is then the case AGAINST, printed by mergeDifferences, not a link that opens nothing.
    const identityClaims = edge.claim_ids ?? []
    const matchedOn: MergeSignalRow[] = Object.entries(breakdown)
      .filter(([, score]) => score > 0)
      .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
      .map(([key, score]) => ({
        key,
        label: MERGE_SIGNAL_LABEL[key] ?? humanizeToken(key),
        score,
        dots: credibilityToDots(score),
        ...(key === MERGE_SIGNAL_SOURCE_ASSERTED && identityClaims.length > 0
          ? { evidenceId: edge.id, evidenceCount: identityClaims.length }
          : {}),
      }))
    const differs = mergeDifferences(leftNode, rightNode, breakdown)
    const differsOn = differs.map((row) => row.text)

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
        merge: { confidence: edge.merge_confidence ?? null, matchedOn, differsOn, differs, consequence, unknowns, left, right },
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
