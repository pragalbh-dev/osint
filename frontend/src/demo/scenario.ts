// ============================================================================
// Frozen demo scenario — HQ-9/P (Pakistan). The deterministic content that makes
// the workbench a faithful recreation of the handoff mockup. Single source of
// truth for on-screen copy; every view renders from here.
//
// HARD RULE (design doc 13): the corpus is frozen — never invent an entity, date,
// source id or quote. All strings below are from the mockup / 07-copy-deck /
// 04-scenario-entities. Voice: sentence case, no first person, dates absolute,
// no percentages, never the words AI/model/agent in the chrome.
// ============================================================================

import type { Status } from '@/api/types'

export type Ceiling = 'confirmable' | 'probable-max' | 'never-observable'

// ─────────────────────────── map pins (geo = [lon, lat]) ───────────────────────────

export interface PinDef {
  id: string
  label: string
  lon: number
  lat: number
  coord: string // monospace readout on select
  status: Status | 'known-gap'
  caption: string
}

/** t=0 map. Karachi + Rawalpindi confirmed (solid); Rahwali + Sargodha probable
 *  (dashed); the TEL count is a hollow, dashed Known Gap. */
export const PINS: PinDef[] = [
  { id: 'karachi', label: 'Karachi', lon: 67.01, lat: 24.86, coord: '24.86°N  67.01°E', status: 'confirmed', caption: 'as of 2022' },
  { id: 'rawalpindi', label: 'Rawalpindi', lon: 73.07, lat: 33.6, coord: '33.60°N  73.07°E', status: 'confirmed', caption: 'as of 2021' },
  { id: 'rahwali', label: 'Rahwali', lon: 74.13, lat: 32.29, coord: '32.29°N  74.13°E', status: 'probable', caption: 'single pass · 2025' },
  { id: 'sargodha', label: 'Sargodha', lon: 72.85, lat: 32.05, coord: '32.05°N  72.85°E', status: 'probable', caption: 'Kirana Hills' },
  { id: 'tel', label: 'TEL count', lon: 67.55, lat: 25.4, coord: '25.40°N  67.55°E', status: 'known-gap', caption: 'never disclosed' },
]

/** Map area-of-interest — Pakistan. Leaflet fits/centres on this; extensible by
 *  editing the bounds (or adding pins with lon/lat, which auto-place). */
export const AOI = {
  bounds: [
    [23.5, 60.0],
    [37.8, 78.0],
  ] as [[number, number], [number, number]],
  center: [30.3, 69.3] as [number, number],
  zoom: 5,
}

// ─────────────────────────── graph (Cytoscape preset) ───────────────────────────

// `contradicted` is its OWN kind, never folded into `gap`: "credible sources disagree"
// (loud — solid coral) and "we do not know" (quiet — dashed grey, no fill) are opposite
// facts, and drawing one as the other is a lie about the evidence.
export type GraphKind = 'confirmed' | 'probable' | 'chokepoint' | 'stale' | 'gap' | 'contradicted'

export interface GraphNodeDef {
  id: string
  label: string // '\n' splits to two lines
  x: number
  y: number
  kind: GraphKind
}

// Positions + labels frozen (deterministic preset — layout never moves).
export const GRAPH_NODES: GraphNodeDef[] = [
  { id: 'rawalpindi', label: 'Rawalpindi\nHQ-9B fire-unit', x: 120, y: 70, kind: 'confirmed' },
  { id: 'rahwali', label: 'Rahwali\nsingle pass · 2025', x: 380, y: 70, kind: 'probable' },
  { id: 'karachi', label: 'Karachi\nHQ-9/P battery', x: 120, y: 300, kind: 'confirmed' },
  { id: 'paad', label: 'PA Air Defence\nHQ-9/P regiment', x: 370, y: 300, kind: 'confirmed' },
  { id: 'import', label: '2021 import\nChina→Pakistan', x: 620, y: 300, kind: 'confirmed' },
  { id: 'casic', label: 'CASIC\nvia CPMIEC', x: 700, y: 150, kind: 'confirmed' },
  { id: 'ht233', label: 'HT-233 radar\ncandidate chokepoint', x: 560, y: 470, kind: 'chokepoint' },
  { id: 'techdata', label: 'Tech-data authority\nheld at probable', x: 770, y: 470, kind: 'probable' },
  { id: 'tel', label: 'TEL count\nnever disclosed', x: 330, y: 470, kind: 'gap' },
]

/** Edge visual kinds — the shared vocabulary for BOTH the frozen demo fixtures and the
 *  live adapter (src/api/adapters.ts). The demo only ever uses the first three.
 *
 *  The trust distinction that matters: `e-stale` is HISTORY (solid grey — we know the
 *  assertion was overtaken) while `e-gap` is an EVIDENCE GAP (dashed grey — we do not
 *  know). Conflating them is a correctness bug in the visual language, not a style nit.
 *  `e-supersede` is the status-LESS "replaced by →" version link (never an alarm), and
 *  `e-link` the other status-less identity edges (same-as / distinct-from).
 *
 *  `e-supersede-candidate` is the same arrow, DASHED: an un-adjudicated supersession —
 *  "something moved, and we are not yet sure it is the same thing". THE ONE RULE decides
 *  it: promoted = settled = solid; pending/held = provisional = dashed. Like the dashed
 *  chokepoint halo, this makes "we're not sure" undrawable as certain. */
export type EdgeKind =
  | 'e-confirmed'
  | 'e-probable'
  | 'e-stale'
  | 'e-gap'
  | 'e-contradicted'
  | 'e-supersede'
  | 'e-supersede-candidate'
  | 'e-link'

export interface GraphEdgeDef {
  id: string
  source: string
  target: string
  kind: EdgeKind
}

export const GRAPH_EDGES: GraphEdgeDef[] = [
  { id: 'e1', source: 'karachi', target: 'paad', kind: 'e-confirmed' },
  { id: 'e2', source: 'paad', target: 'import', kind: 'e-confirmed' },
  { id: 'e3', source: 'import', target: 'casic', kind: 'e-confirmed' },
  { id: 'e4', source: 'casic', target: 'ht233', kind: 'e-confirmed' },
  { id: 'e5', source: 'ht233', target: 'paad', kind: 'e-probable' },
  { id: 'e6', source: 'techdata', target: 'ht233', kind: 'e-probable' },
  // the regiment's TEL count is a Known Gap — the edge into it is an evidence GAP (dashed
  // grey, "we do not know"), not history.
  { id: 'e7', source: 'paad', target: 'tel', kind: 'e-gap' },
  // the relocation is an adjudicated supersession — "replaced by →": solid grey + arrow.
  { id: 'e_moved', source: 'rawalpindi', target: 'rahwali', kind: 'e-supersede' }, // hidden until relocation
]

// ─────────────────────────── target queries (screen zero) ───────────────────────────

// `hero` is BOTH the label the Ask affordance shows and the exact payload it POSTs to /ask (one string,
// one source — a label/payload divergence is how the button silently fell off the hero path before).
// It must stay byte-identical to `config/subjects.yaml` → lens-hq9p-pk → target_queries[0]: the backend's
// primary hero matcher is an exact match on that string; the "trace…chokepoint" keyword rule is only the
// safety net. Change one, change the other.
export const TARGET_QUERIES = {
  hero: 'Trace the long-range SAM battery now based at Rahwali back to its fire-control component and name the chokepoint.',
  provenance: 'Is this node confirmed or probable — and on what evidence?',
  gaps: 'What do we not know here?',
} as const

// ─────────────────────────── hero answer (the walk) ───────────────────────────

export interface HeroHop {
  step: number
  question: string
  finding: string
  chips: string[] // 'd07 · imagery'
  gapChip?: string // renders as a dashed Known-Gap chip instead
  dim?: boolean // hop that returns nothing
}

export const HERO_HOPS: HeroHop[] = [
  { step: 1, question: 'Where is the battery based?', finding: 'Karachi — HQ-9/P pad signature, confirmed by imagery.', chips: ['d07 · imagery'] },
  {
    step: 2,
    question: 'Which unit holds it, and how did it arrive?',
    finding: 'Pakistan Army Air Defence — HQ-9/P regiment, inducted 14 Oct 2021, via the 2021 China→Pakistan transfer.',
    chips: ['d02 · official', 'd01 · register'],
  },
  { step: 3, question: 'Who supplied the system?', finding: 'CASIC — export agent CPMIEC. HT-233 radar sub-components shipped China→Pakistan.', chips: ['d05 · customs'] },
  {
    step: 4,
    question: 'Are there alternate suppliers?',
    finding: 'Unknown. No open source establishes this either way — and the walk came back empty.',
    chips: [],
    gapChip: 'Known Gap · substitutability unknown',
    dim: true,
  },
]

// Revision shown on hop 2 after the analyst decides the HQ-9/P ↔ HQ-9BE merge card.
export const HERO_REVISION =
  'HQ-9/P and HQ-9BE kept separate — one import, two service variants (Army ~125 km, PAF ~260 km).'

export const HERO_INFERENCE = {
  primary:
    'The HT-233 engagement radar is the candidate chokepoint — the only supplier visible in open sources. Whether it is truly sole-source is a Known Gap (substitutability unknown), not a confirmed single point of failure.',
  secondary:
    'A second candidate is invisible: the technical-data and software authority that keeps calibration control after the sale — held at probable.',
}

// ─────────────────────────── gaps / refusals (three tones) ───────────────────────────

export interface GapBlock {
  ceiling: Ceiling
  kicker: string // 'Coverage gap · launcher count, now'
  verdict: string // the headline
  standard?: string // the rule, stated before the failure
  lines: { label?: string; text: string; chip?: string }[]
  tail?: string
  action?: string // button label; absent = nothing to collect
  actionKind?: 'button' | 'none'
}

export const GAP_BLOCKS: GapBlock[] = [
  {
    ceiling: 'confirmable',
    kicker: 'Coverage gap · launcher count, now',
    verdict: 'Insufficient evidence to assess.',
    standard: 'Confirming a launcher count needs an unobscured overhead pass.',
    lines: [
      {
        label: 'Held',
        text: 'a 10 May pass at ~95% cloud. The HT-233 array is visible; the firing battery footprint is not. Prior reporting carried 6–8 launchers; that figure has not been re-verified against this pass.',
        chip: 'd10 · imagery',
      },
      { label: 'Missing', text: 'an unobscured pass. No SAR was tasked this cycle. No ELINT correlation available.' },
      { label: 'Next pass', text: '14 May, forecast permitting.' },
    ],
    action: 'Add to collection list',
    actionKind: 'button',
  },
  {
    ceiling: 'probable-max',
    kicker: 'Ceiling · battery establishment strength',
    verdict: 'Probable. No source will raise this.',
    lines: [
      { text: 'Estimated 4–8 launchers delivered. Combat-ready count unknown.' },
      { text: 'Pakistan has never disclosed battery composition. No open source establishes an exact count, and none is expected to.' },
    ],
    tail: "Collecting more won't change this.",
    actionKind: 'none',
  },
  {
    ceiling: 'never-observable',
    kicker: 'Boundary · interceptor stocks',
    verdict: 'No open source will show this.',
    lines: [
      { text: "Interceptor stocks inside a hardened shelter aren't observable from open sources." },
      { text: 'This is a boundary, not a gap. No imagery, no new pass, no additional source resolves it.' },
    ],
    tail: 'Nothing to collect.',
    actionKind: 'none',
  },
]

// ─────────────────────────── review queue + cards ───────────────────────────

export type CardId = 'merge' | 'override' | 'alert'

export interface QueueItem {
  id: CardId
  type: string // shown as the small kicker
  subject: string
  badge: string // priority badge
  /** WHICH records this row is about — a queue row must be readable without opening it.
   *  Taken from the card each row opens, so the rail and the card cannot disagree. */
  detail: string
}

export const QUEUE_ITEMS: QueueItem[] = [
  { id: 'merge', type: 'Merge · variant', subject: 'Same system, or two?', badge: 'Close call', detail: 'HQ-9/P ↔ HQ-9BE' },
  {
    id: 'override',
    type: 'Status override · basing site',
    subject: 'Is this really confirmed?',
    badge: 'Close call',
    detail: 'Karachi-East · 09 May 2025',
  },
  {
    id: 'alert',
    type: 'Alert · basing relocation',
    subject: 'A tripwire fired. Is it real?',
    badge: 'First seen',
    detail: 'occupied @ Rawalpindi → occupied @ Rahwali',
  },
]

// Merge card — HQ-9/P vs HQ-9BE. Matched-on is long & quiet; differs-on short & loud.
export const MERGE_CARD = {
  badges: ['Close call', 'Touches a chokepoint'],
  subject: 'Same system, or two?',
  left: { name: 'HQ-9/P', sub: 'Army · ~125 km' },
  right: { name: 'HQ-9BE', sub: 'PAF · ~260 km' },
  matchedOn: [
    { label: 'Name similarity', dots: 3 },
    { label: 'Both connect to the Nov 2020 import', dots: 3 },
    { label: 'Timeline consistent', dots: 2 },
    { label: 'One source calls them the same', dots: 1 },
  ],
  differsOn: ['Range — Army ~125 km vs PAF ~260 km.', 'Role — one import, two service variants.'],
  ifYou: 'Joins 4 claims, changes 2 node statuses. The answer to “trace this battery…” changes.',
  options: [
    { key: 'merged', label: 'Merge' },
    { key: 'keptSeparate', label: 'Keep separate' },
    { key: 'split', label: 'Split into two' },
  ],
  splitNote: 'Split separates one record that is really two.',
  footer: 'Flagged by the merge check · 2 hrs ago · reversible',
} as const

export const OVERRIDE_CARD = {
  badge: 'Close call',
  subject: 'Is this really confirmed?',
  intro: 'Karachi-East reads confirmed. Two credible sources describe 09 May 2025 differently — so it routed to you.',
  against: [
    'd08 · social — active convoy near Karachi, 09 May 2025.',
    'd09 · official — the same day, framed as routine training.',
  ],
  againstNote: 'Credible sources, disagreeing about the same moment.',
  ifYou: 'Karachi-East drops from confirmed to probable. The answer to “trace this battery…” changes.',
  options: [
    { key: 'promoted', label: 'Promote to confirmed' },
    { key: 'demoted', label: 'Demote to probable' },
    { key: 'rejected', label: 'Reject this claim' },
  ],
  footer: 'Routed by the contradiction check · 3 hrs ago · reversible',
} as const

export const ALERT_CARD = {
  badge: 'First seen',
  subject: 'A tripwire fired. Is it real?',
  changed: { from: 'occupied @ Rawalpindi', to: 'occupied @ Rahwali' },
  note: 'Rahwali — new imagery. A unit relocating within 2 hops of this subject.',
  options: [
    { key: 'accepted', label: 'Accept the move' },
    { key: 'dismissed', label: 'Dismiss as noise' },
    { key: 'held', label: 'Hold for a second look' },
  ],
  footer: 'Rahwali — new imagery · 2 hrs ago · reversible',
} as const

// past-tense result copy (button verb persists into its result)
export const DECISION_LABELS: Record<string, string> = {
  merged: 'Merged',
  keptSeparate: 'Kept separate',
  split: 'Split',
  promoted: 'Promoted',
  demoted: 'Demoted',
  rejected: 'Rejected',
  accepted: 'Accepted',
  dismissed: 'Dismissed',
  held: 'Held',
}

// ─────────────────────────── credibility rubric (live recompute) ───────────────────────────

export interface CredSource {
  key: 'd08' | 'd09'
  label: string
  kind: string
  asserts: string
  authority: number
  editorial: number
  directness: number
  track: number
}

// Karachi-East · 09 May 2025 — two credible sources, opposite claims. Weighted, not averaged.
export const CRED_SOURCES: CredSource[] = [
  { key: 'd08', label: 'd08 · social', kind: 'firsthand convoy imagery', asserts: 'active deployment', authority: 25, editorial: 15, directness: 92, track: 45 },
  { key: 'd09', label: 'd09 · official', kind: 'state channel statement', asserts: 'routine training', authority: 96, editorial: 88, directness: 38, track: 82 },
]

export const CRED_FACTORS = [
  { key: 'authority' as const, label: 'Authority', hint: 'standing of the originator' },
  { key: 'editorial' as const, label: 'Editorial process', hint: 'review before publication' },
  { key: 'directness' as const, label: 'Directness', hint: 'firsthand vs. relayed' },
  { key: 'track' as const, label: 'Track record', hint: 'past reliability' },
]

export const CRED_DEFAULT_WEIGHTS = { authority: 55, editorial: 15, directness: 20, track: 10 }

export const CRED_INTRO =
  'Credibility is your rubric, not ours. Adjust what a source’s authority is worth against how directly it saw the event — the claim below recomputes as you move them.'

// ─────────────────────────── tripwires (indicators & warning) ───────────────────────────

// `state` is data, not a hardcoded badge in the view: the demo asserts these three are
// armed and none has fired, and WatchView renders whatever state it is handed (the LIVE
// path derives real state from the alert feed on GET /view instead).
export const TRIPWIRES = [
  { name: 'Relocation', desc: 'A unit relocating within 2 hops of this subject.', indicator: 'movement in EO/SAR imagery', state: 'armed' },
  { name: 'New supplier link', desc: 'A new entity entering the supply path behind this system.', indicator: 'procurement / customs records', state: 'armed' },
  { name: 'Contradiction', desc: 'Two credible sources disagreeing on the same event.', indicator: 'source conflict on one claim', state: 'armed' },
]

export const WATCH_INTRO =
  'Three tripwires armed on this subject. Each names the indicator it watches; when one fires it routes to Review, never straight to the picture.'

// ─────────────────────────── ingest (keyless bundle / scripted trace) ───────────────────────────

export interface IngestDoc {
  id: 'd18' | 'd19' | 'd20'
  file: string
  kind: string
  claims: number
}

export const INGEST_DOCS: IngestDoc[] = [
  { id: 'd18', file: 'RAHWALI_0312_EO.tif', kind: 'EO imagery', claims: 2 },
  { id: 'd19', file: 'ELINT_RWP_0514.json', kind: 'ELINT report', claims: 1 },
  { id: 'd20', file: 'x_repost_0518.png', kind: 'social repost', claims: 1 },
]

export const INGEST_STEPS = (file: string, claims: number) => [
  `reading ${file}`,
  `extracting claims — ${claims} found`,
  'matching to subject graph',
  'picture updated',
]

// ─────────────────────────── provenance drawer (Rahwali, before d19) ───────────────────────────
// The richest state the drawer ever holds: lid + collapse + integrity flag + sufficiency,
// all live at once. After d19 it collapses to plain "confirmed".

export const DRAWER = {
  proving: 'HQ-9B fire-unit occupied at Rahwali',
  asOf: 'as of 2025',
  probable: {
    verdictWord: 'Probable',
    capLine: 'held at probable · the cap is liftable',
    why: "One overhead pass can't rule out a decoy.",
    whySecond: 'A second cap sits below it — the layout resembles a 2023 industry roundup, so the read may not be independent.',
    toRaise: 'A repeat pass, or an emission report. A decoy array can’t radiate.',
  },
  confirmed: {
    verdictWord: 'Confirmed',
    settled: 'A repeat pass and an emission report — two discipline-independent looks. The decoy read is closed.',
    look2Title: 'Look 2 — emission report',
    look2Meta: 'decisive',
    look2Chip: 'd19 · ELINT',
    look2Body:
      'An active HT-233-consistent emitter. A decoy array can’t radiate — one dot, and decisive: a discipline-independent look that shares no failure mode with the imagery.',
  },
  look1: {
    title: 'Look 1 — overhead imagery',
    meta: '1 pass',
    chip: 'd18 · imagery',
    chipDots: 3,
    dates: { event: 'Mar 2025 · overhead pass', reported: 'Mar 2025', ingested: 'Mar 2025' },
    dateNote: 'Same collection cycle — nothing aged between the event and the report.',
    quote: '“HT-233-consistent array present at Rahwali; single uncontested pass. Battery footprint partially obscured.”',
    body: 'A single pass, Mar 2025. A decoy can’t be ruled out on one look.',
  },
  social: {
    title: 'Social imagery',
    meta: 'adds no independent look',
    chip: 'd11 · social',
    chipDots: 1,
    reshareChips: ['d12 · reshare', 'd13 · reshare'],
    dates: { event: '2019 · Yaum-e-Pakistan parade', reported: '09 May 2025', ingested: '09 May 2025' },
    dateNote: 'Six years between event and report.',
    quote: '“HQ-9 battery now active at Rahwali” — image reposted 09 May 2025.',
    collapse: 'd12 and d13 repost d11. Same origin — they add no look.',
    integrity: "First seen 2019. This image predates the deployment it's captioned as. Held at probable.",
  },
  spoofNote:
    'A single low-credibility post claims the unit left Rahwali. It raises the source count — but adds no independent look. The verdict holds.',
} as const
