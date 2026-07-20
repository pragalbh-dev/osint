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
  /** the id of the `supersedes` edge itself, so the connector is one click from its evidence */
  supersedeEdgeId?: string | null
  /** WHAT moved — the subject of the underlying `based-at` assertion, named. NEVER the site: a
   *  site does not get "replaced", an occupant relocates. Null when the graph does not record one. */
  supersedeSubject?: string | null
}

export type StagePin = PinDef & StagePinExtras

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

    const surface = node.location?.surface_format
    const coord = typeof surface === 'string' && surface.length > 0 ? surface : formatCoord(lat, lon)
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
      }
    }
    return { ref, kind: 'edge', headline: `${src} — ${typeLabel} → ${dst}`, typeLabel, statusless }
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
