// TypeScript mirror of the F0-frozen backend contract
// (backend/chanakya/schemas/{api_models,view,claim,values,config_models}.py).
// The live OpenAPI spec at /openapi.json is generated from these same shapes, so
// the frontend cannot drift. Field NAMES may still move (per master §4.8); SHAPES
// are stable. Additive changes are logged in tmp/conv/API-to-FRONTEND-contract-log.md.
//
// Well-known top-level fields are typed precisely. Deep value objects (Location,
// DateValue, Quantity, Extraction, claim payloads) mirror the frozen schemas but
// are kept permissive; tighten when their routes land.

// ───────────────────────── enums / literals ─────────────────────────

export type Status =
  | 'confirmed'
  | 'probable'
  | 'possible'
  | 'contradicted'
  | 'stale'
  | 'insufficient'

export type ObservabilityCeiling = 'confirmable' | 'probable-max' | 'never-observable'

export type ChokepointStatus = 'confirmed' | 'candidate' | 'none'
export type SubstitutabilityState = 'known-sole-source' | 'known-alternates' | 'UNKNOWN'

export type ClaimKind = 'observation' | 'inference' | 'retraction'
export type Polarity = 'positive' | 'negative'
export type Asserts = 'entity' | 'relationship' | 'event'

export type ReviewType = 'merge' | 'status-override' | 'alert-disposition' | 'integrity-flag'
export type AlertDisposition = 'real' | 'noise' | 'needs-more'

// event / report / ingest dates: ExactDate | LabelDate | Period (values.py) — permissive.
export type DateValue =
  | string
  | { date?: string; label?: string; start?: string; end?: string; [k: string]: unknown }

// ───────────────────────── value objects ─────────────────────────

export interface Location {
  // values.py: `raw: str | list[str]` — a source may state one place several ways in one claim.
  raw?: string | string[] | null
  surface_format?: string | null
  wgs84_lat?: number | null
  wgs84_lon?: number | null
  precision_class?: string | null
  proposed_alias?: string | null
  resolved_place_ref?: string | null
  geocode_candidates?: Array<Record<string, unknown>>
}

export interface DocRef {
  file: string
  span?: [number, number] | null
  line?: number | null
  row?: number | null
  page?: number | null
  bbox?: [number, number, number, number] | null
  frame?: number | null
  region?: string | null
}

export interface Extraction {
  method?: string | null // 'parser' | 'LLM' | 'VLM'
  model?: string | null
  confidence?: number | null
  [k: string]: unknown
}

// ───────────────────────── confidence / freshness / sufficiency ─────────────────────────

export interface IndependenceGroup {
  group_id: string
  claim_ids: string[]
  axis_key?: Record<string, string> // {origin, discipline, interest}
  weight?: number
}

export interface ConfidenceBreakdown {
  per_claim_credibility?: Record<string, number>
  integrity_flags?: string[]
  independence_groups?: IndependenceGroup[]
  freshness_factor?: number | null
  assertion_confidence?: number | null // 1 − Π_g(1 − c_g) — truth score, never identity
}

export interface Freshness {
  last_support_time?: string | null
  half_life?: string | null
  half_life_days?: number | null
  decay_factor?: number | null // 2^(-age/half_life); 1.0 = fresh
}

export interface SufficiencyEval {
  satisfied: boolean
  missing_slots?: string[]
  next_coverage_due?: string | null
  ceiling?: ObservabilityCeiling | null
  template_id?: string | null
}

export interface MaterialityAttrs {
  chokepoint_count?: number | null
  chokepoint_status?: ChokepointStatus | null
  substitutability_state?: SubstitutabilityState | null
  contributing_refs?: string[]
}

// ───────────────────────── graph view ─────────────────────────

/** Shared assessment fields carried by nodes, edges and events (_Assessed). */
export interface Assessed {
  claim_ids?: string[]
  status?: Status | null
  confidence?: ConfidenceBreakdown | null
  freshness?: Freshness | null
  supporting_claims?: IndependenceGroup[]
  opposing_claims?: string[]
  sufficiency?: SufficiencyEval | null
}

export interface NodeView extends Assessed {
  id: string
  type: string // manufacturer, component, unit, basing_site, variant, ...
  name?: string | null
  attrs?: Record<string, unknown>
  location?: Location | null
  materiality?: MaterialityAttrs | null
}

/** NOTE — some edge types are status-LESS by design: `supersedes` (a version link between
 *  two already-scored edges — scoring it again would score one fact twice), `same-as` and
 *  `distinct-from` (identity, never truth). Their `status`/`confidence` are null; nothing
 *  may assume every edge carries a status badge. `attrs` on a `based-at` edge that is half
 *  of a supersession additionally carries `candidate_supersede`, `supersede_gate`
 *  ('pending' | 'promoted' | 'held'), `supersede_pending_newer` / `supersede_pending_older`
 *  and `supersede_hold_reason` (string list — why it was NOT auto-retired). */
export interface EdgeView extends Assessed {
  id: string
  type: string // supplies-component, based-at, same-as, supersedes, ...
  source: string
  target: string
  edge_instance?: string | null
  attrs?: Record<string, unknown>
  superseded_by?: string | null
  supersedes?: string | null
  merge_confidence?: number | null // identity only — never blended into assertion confidence
}

export interface EventView extends Assessed {
  id: string
  event_type: string
  time_interval?: DateValue | null
  location?: Location | null
  participants?: string[]
  attrs?: Record<string, unknown>
}

export interface KnownGap {
  id: string
  what_missing: string
  observability_ceiling: ObservabilityCeiling
  next_coverage_due?: string | null
  related_ref?: string | null
  missing_slots?: string[]
}

/** The evidence behind a fired Alert (schemas/view.py AlertProvenance; added 2026-07-20).
 *  An alert asserts something about the world, so it names the claims it rests on: the
 *  `before_*` claims asserted the prior state, the `after_*` claims assert the new one —
 *  the split is the point, because "what changed" is only auditable if both sides are
 *  separately traceable. `before_ref`/`after_ref` are the view element ids (edge/node)
 *  that carried each state, so they resolve straight into GET /evidence/{id}. `status` /
 *  `assertion_confidence` are COPIED off the after-element (MONITOR never scores). Every
 *  field is optional: an alert whose element carried no claims says so by being empty,
 *  never by inventing a citation. */
export interface AlertProvenance {
  before_ref?: string | null
  after_ref?: string | null
  before_claim_ids?: string[]
  after_claim_ids?: string[]
  claim_ids?: string[] // union (before-first, de-duplicated)
  status?: Status | null
  assertion_confidence?: number | null // truth confidence, never identity
}

export interface Alert {
  observable_id: string
  subject?: string | null
  before?: Record<string, unknown>
  after?: Record<string, unknown>
  severity?: string
  fired_ts?: string | null
  disposition?: AlertDisposition | null
  provenance?: AlertProvenance | null // null/absent = a pre-MON-4 alert with no recorded evidence
}

export interface GraphView {
  nodes: NodeView[]
  edges: EdgeView[]
  events: EventView[]
  known_gaps: KnownGap[]
  alerts: Alert[]
  meta?: Record<string, unknown>
}

// ───────────────────────── claim / evidence atom ─────────────────────────

export interface ClaimRecord {
  claim_id: string
  source_id: string
  doc_ref: DocRef | DocRef[]
  kind: ClaimKind
  polarity?: Polarity
  asserts: Asserts
  payload?: unknown // Triple | EntityDescriptor | EventDescriptor (discriminated on `form`)
  event_time?: DateValue | null
  report_time?: DateValue | null
  ingest_time?: DateValue | null
  resolved_ref?: unknown
  extraction?: Extraction
  premises?: string[]
  targets?: string | null
  attributes?: Record<string, unknown> | null
}

// ───────────────────────── ask / answer ─────────────────────────

export interface AnswerHop {
  step: number
  edge: string
  src: string
  dst: string
  claim_ids?: string[]
  observed_or_inferred?: 'observed' | 'inferred'
}

/** Which of the three refusals this is. `evidence` = we looked and the world is thin.
 *  `capability` = we could not look at all (no model key, no recorded trace, a dead tool).
 *  `withheld` = we looked and would not stand behind the wording (failed citation/entailment).
 *  Conflating them overstates a gap in the world that may not exist — see the backend's
 *  RefusalPayload docstring. Absent → 'evidence' (the pre-`kind` contract). */
export type RefusalKind = 'evidence' | 'capability' | 'withheld'

export interface RefusalPayload {
  kind?: RefusalKind
  missing?: string[]
  next_coverage_due?: string | null
  known_gap?: KnownGap | null
  reason?: string
}

export interface AskRequest {
  question: string
  subject?: string | null
}

export interface AskAnswer {
  question: string
  sub_questions?: string[]
  hops?: AnswerHop[]
  answer?: string | null // null when refusing
  citations?: string[]
  observed_claims?: string[]
  inferred_claims?: string[]
  refusal?: RefusalPayload | null
}

// ───────────────────────── provenance drawer ─────────────────────────

export interface ProvenanceDrawer {
  subject_ref: string
  status?: Status | null
  confidence?: ConfidenceBreakdown | null
  freshness?: Freshness | null
  clusters?: IndependenceGroup[] // "5 sources · 2 independent looks"
  opposing_claims?: string[]
  sufficiency?: SufficiencyEval | null
  claims?: ClaimRecord[] // added 2026-07-19 — resolved evidence atoms, index by claim_id for doc_ref deep-links
  // added 2026-07-20 — claim_id -> the VERBATIM text at each of that claim's doc_refs, in doc_ref
  // order. A file+offset is a pointer, not a source; this is what the analyst actually audits.
  // Absent claim / empty string = the span could not be read; render the locator alone, never a guess.
  quotes?: Record<string, string[]>
}

// ───────────────────────── review queue / HITL ─────────────────────────

export interface ReviewContext {
  summary?: string
  confidence?: number | null
  materiality?: number | null
  novelty?: number | null
  evidence?: Record<string, unknown>
}

export interface ReviewQueueItem {
  item_id: string
  type: ReviewType
  subject: string
  context?: ReviewContext
  options?: string[] // merge: accept/reject/split · override: promote/demote/reject · alert: real/noise/needs-more
  effects?: Record<string, unknown>
  payload?: Record<string, unknown>
  actor?: string
  ts?: string | null
  pinned?: boolean
}

export interface HitlDecision {
  item_id: string
  type: ReviewType
  subject: string
  decision: string
  rationale?: string | null
  actor?: string
}

// ───────────────────────── ingest ─────────────────────────

export interface IngestRequest {
  doc_path?: string | null // CLI/SHIP only — rejected on hosted read
  raw_text?: string | null
  source_id?: string | null
  source_type?: string | null // added 2026-07-19 — required with raw_text on the keyed path
  bundle?: Array<Record<string, unknown>> | null // pre-extracted ClaimRecord dicts (keyless)
}

export interface IngestResult {
  appended_claim_ids?: string[]
  rebuilt?: boolean
  alerts_fired?: string[]
}

// ───────────────────────── pending (withheld) documents ─────────────────────────
// Documents deliberately held OUT of the boot seed (config/sources.yaml → withheld_from_seed),
// so the graph stands up in the state that PRECEDES their arrival. Their frozen claim bundles
// ship with the app and are served here, so a reviewer can ingest one through the keyless lane
// and watch the tripwire fire — no repo checkout, no key, no network. Added 2026-07-20.

export interface PendingDocument {
  doc_id: string
  source_type?: string | null
  citation_url?: string | null
  bundles?: string[] // its own bundle + any derived enrichment bundles — released together
  claim_count?: number
  available?: boolean // false = declared withheld but no bundle on disk (say so, never pretend)
  ingested?: boolean // true once its claims are in the evidence log — server state, not a local guess
}

export interface PendingResponse {
  scenario?: string | null
  documents?: PendingDocument[]
}

export interface PendingBundle {
  doc_id: string
  bundles?: string[]
  bundle?: Array<Record<string, unknown>> // ready to POST /ingest as { bundle }
}

// ───────────────────────── config / observables ─────────────────────────

export interface ObservableDef {
  observable_id: string
  subject?: string | null
  watch_instances?: string[]
  trigger?: Record<string, unknown>
  severity?: string
  disposition?: string[]
}

export interface ConfigWrite {
  section: string // ontology | sources | credibility | resolution | templates | subjects | observables | places
  value: Record<string, unknown>
}

export interface ConfigWriteResult {
  section: string
  version: number
}

// ───────────────────────── health ─────────────────────────

export interface HealthResponse {
  status: 'ok' | 'starting'
  rebuilt?: boolean
  node_count?: number
  edge_count?: number
  config_version?: number
}
