// The workbench state machine (Zustand). Ports the handoff mockup's component
// logic: stage/panel/drawer/selection, the review queue + decisions, the scripted
// ingest trace, and the live credibility recompute. DEMO mode is deterministic and
// identical on every run (the graded non-negotiable); LIVE mode swaps in real API data.

import { create } from 'zustand'
import { api, ApiError } from '@/api/client'
import type { LiveReviewItem } from '@/api/adapters'
import type { AskAnswer, GraphView } from '@/api/types'
import {
  CRED_DEFAULT_WEIGHTS,
  DECISION_LABELS,
  INGEST_DOCS,
  QUEUE_ITEMS,
  TARGET_QUERIES,
  type CardId,
} from '@/demo/scenario'

export type Stage = 'map' | 'graph'
// 'answer' is the LIVE-only unified answer view (POST /ask → answer or refusal);
// demo keeps its two authored views 'hero' (the walk) and 'gaps' (the refusals).
export type PanelView = 'zero' | 'hero' | 'gaps' | 'card' | 'cred' | 'watch' | 'answer'
export type DocId = 'd18' | 'd19' | 'd20'
export type Mode = 'demo' | 'live'

interface IngestTrace {
  doc: DocId
  step: number
}

interface WorkbenchState {
  mode: Mode
  stage: Stage
  panelView: PanelView
  activeCard: CardId | null
  drawerOpen: boolean
  selected: string | null
  expanded: string | null // expanded citation chip id
  reviewOpen: boolean
  decided: Partial<Record<CardId, string>> // decision key
  lastResolved: string | null // past-tense label
  ingested: Record<DocId, boolean>
  ingestTrace: IngestTrace | null
  weights: typeof CRED_DEFAULT_WEIGHTS
  liveView: GraphView | null

  // live ask (POST /ask) — demo never touches these (askHero/askGaps stay scripted)
  askQuestion: string
  askResult: AskAnswer | null
  askPending: boolean
  askError: boolean

  // live review (queue derived from liveView; decisions POSTed to /hitl/*) — demo uses
  // the scripted QUEUE_ITEMS + `decided` path and never touches these.
  liveDecided: Record<string, string> // live review itemId → past-tense label
  activeLiveItem: LiveReviewItem | null

  // live ingest (POST /ingest keyless bundle path) — demo uses the scripted trace instead
  liveIngestBusy: boolean
  liveIngestNote: string | null

  // navigation
  setStage: (s: Stage) => void
  askHero: () => void
  askGaps: () => void
  backToZero: () => void
  openCred: () => void
  openWatch: () => void

  // live ask
  setAskQuestion: (q: string) => void
  runAsk: (question: string) => Promise<void>

  // review queue
  toggleReview: () => void
  openCard: (id: CardId) => void
  decide: (decisionKey: string) => void

  // live review queue
  openLiveCard: (item: LiveReviewItem) => void
  decideLive: (item: LiveReviewItem, decisionKey: string) => Promise<void>

  // selection / drawer
  select: (id: string | null) => void
  openDrawer: () => void
  closeDrawer: () => void
  toggleChip: (id: string) => void
  openProvenance: (elementId: string, claimId?: string | null) => void

  // ingest (scripted trace)
  startIngest: (doc: DocId) => void
  resetIngest: () => void

  // live ingest (keyless bundle)
  ingestLive: (bundle: Array<Record<string, unknown>>) => Promise<void>
  // live ingest (keyed raw document → extract → append)
  ingestDocLive: (args: { rawText: string; sourceId: string; sourceType: string }) => Promise<void>

  // credibility rubric
  setWeight: (key: keyof typeof CRED_DEFAULT_WEIGHTS, val: number) => void

  // live mode
  setMode: (m: Mode) => void
  setLiveView: (v: GraphView | null) => void
}

// Trace timers live in module scope (non-serializable, outside store state).
let ingestTimers: ReturnType<typeof setTimeout>[] = []
const clearIngestTimers = () => {
  ingestTimers.forEach(clearTimeout)
  ingestTimers = []
}

export const useWorkbench = create<WorkbenchState>((set, get) => ({
  mode: 'demo',
  stage: 'map',
  panelView: 'zero',
  activeCard: null,
  drawerOpen: false,
  selected: null,
  expanded: null,
  reviewOpen: false,
  decided: {},
  lastResolved: null,
  ingested: { d18: false, d19: false, d20: false },
  ingestTrace: null,
  weights: { ...CRED_DEFAULT_WEIGHTS },
  liveView: null,

  askQuestion: '',
  askResult: null,
  askPending: false,
  askError: false,

  liveDecided: {},
  activeLiveItem: null,

  liveIngestBusy: false,
  liveIngestNote: null,

  setStage: (s) => set({ stage: s }),
  // DEMO: the two authored views are scripted (byte-identical). LIVE: both target
  // queries are real natural-language questions — route them through the agent.
  askHero: () => {
    const s = get()
    if (s.mode === 'live') void s.runAsk(TARGET_QUERIES.hero)
    else set({ panelView: 'hero' })
  },
  askGaps: () => {
    const s = get()
    if (s.mode === 'live') void s.runAsk(TARGET_QUERIES.gaps)
    else set({ panelView: 'gaps' })
  },
  backToZero: () => set({ panelView: 'zero' }),
  openCred: () => set({ panelView: 'cred' }),
  openWatch: () => set({ panelView: 'watch' }),

  // LIVE only — POST /ask and show the structured answer (or refusal) in the panel.
  // Guarded to live mode so the demo never fetches; the forming answer IS the loading
  // state (no spinner in the answer grammar). A refusal is a normal result, not an error.
  setAskQuestion: (q) => set({ askQuestion: q }),
  runAsk: async (question) => {
    if (get().mode !== 'live') return
    const q = question.trim()
    if (!q) return
    set({ askQuestion: q, askPending: true, askError: false, askResult: null, panelView: 'answer' })
    try {
      const res = await api.ask({ question: q })
      // Ignore a stale response if the user navigated away or asked again meanwhile.
      if (get().askQuestion !== q) return
      set({ askResult: res, askPending: false })
    } catch {
      if (get().askQuestion !== q) return
      set({ askError: true, askPending: false })
    }
  },

  toggleReview: () => set((s) => ({ reviewOpen: !s.reviewOpen })),
  openCard: (id) => set({ panelView: 'card', activeCard: id, reviewOpen: true }),
  decide: (decisionKey) =>
    set((s) => {
      if (!s.activeCard) return {}
      const label = DECISION_LABELS[decisionKey] ?? decisionKey
      return {
        decided: { ...s.decided, [s.activeCard]: label },
        panelView: 'zero',
        lastResolved: label,
      }
    }),

  // LIVE review — open a derived queue item into the card slot, and write its decision
  // through the matching /hitl/* route. The response IS the full rebuilt graph, so we
  // mirror it into liveView; re-deriving the queue then drops the badge and re-answers
  // any open question. On error the item stays in the queue (nothing fake is shown).
  openLiveCard: (item) => set({ activeLiveItem: item, panelView: 'card', reviewOpen: true }),
  decideLive: async (item, decisionKey) => {
    if (get().mode !== 'live') return
    const opt = item.options.find((o) => o.key === decisionKey)
    const label = opt?.done ?? decisionKey
    try {
      const rebuilt = await api.hitl(item.hitlVerb, {
        item_id: item.itemId,
        type: item.reviewType,
        subject: item.subject,
        decision: decisionKey,
        actor: 'analyst',
      })
      set((s) => ({
        liveView: rebuilt,
        liveDecided: { ...s.liveDecided, [item.itemId]: label },
        panelView: 'zero',
        lastResolved: label,
        activeLiveItem: null,
      }))
    } catch {
      set({ activeLiveItem: null, panelView: 'zero' })
    }
  },

  // Selecting an element. DEMO: Rahwali is the scripted provenance entry point — only it
  // opens the drawer. LIVE: any node is traceable, so selecting one opens its provenance
  // drawer (and deselecting/background-tap closes it). The demo path is unchanged.
  select: (id) => {
    if (get().mode === 'live') {
      set({ selected: id, drawerOpen: id != null })
      return
    }
    set(id === 'rahwali' ? { selected: 'rahwali', drawerOpen: true } : { selected: id })
  },
  openDrawer: () => set({ drawerOpen: true }),
  closeDrawer: () => set({ drawerOpen: false }),
  toggleChip: (id) => set((s) => ({ expanded: s.expanded === id ? null : id })),

  // One-click traceability from anywhere that cites evidence (today: the alert feed, which
  // was the last derived artifact with nothing to click). It drives the SAME provenance
  // drawer selection/evidence uses — no second drill-down path — and optionally pre-expands
  // one claim row so the click lands on that claim's exact source locator, not just the
  // element. Element ids only: GET /evidence/{id} resolves nodes/edges/events, and a claim
  // id would 404 into an "insufficient evidence" panel that isn't true.
  openProvenance: (elementId, claimId) =>
    set({ selected: elementId, drawerOpen: true, expanded: claimId ?? null }),

  startIngest: (doc) => {
    const s = get()
    if (!INGEST_DOCS.some((d) => d.id === doc) || s.ingested[doc] || s.ingestTrace) return
    set({ ingestTrace: { doc, step: 0 } })
    ingestTimers.push(setTimeout(() => set({ ingestTrace: { doc, step: 1 } }), 600))
    ingestTimers.push(setTimeout(() => set({ ingestTrace: { doc, step: 2 } }), 1250))
    ingestTimers.push(
      setTimeout(
        () => set((st) => ({ ingested: { ...st.ingested, [doc]: true }, ingestTrace: { doc, step: 3 } })),
        1900,
      ),
    )
    ingestTimers.push(setTimeout(() => set({ ingestTrace: null }), 3300))
  },
  resetIngest: () => {
    clearIngestTimers()
    set({ ingested: { d18: false, d19: false, d20: false }, ingestTrace: null })
  },

  // LIVE ingest — the keyless bundle path (pre-extracted claim dicts). POST /ingest, then
  // refetch /view so the new claims land in the graph AND any tripwires that fired surface
  // into the derived review queue (their alerts ride along in the rebuilt view). The keyed
  // raw-doc path is 403-guarded server-side and is deliberately not offered here.
  ingestLive: async (bundle) => {
    if (get().mode !== 'live') return
    if (!Array.isArray(bundle) || bundle.length === 0) {
      set({ liveIngestNote: 'No claims found — expected a JSON array of pre-extracted claims.' })
      return
    }
    set({ liveIngestBusy: true, liveIngestNote: null })
    try {
      const res = await api.ingest({ bundle })
      const fresh = await api.view()
      const n = res.appended_claim_ids?.length ?? bundle.length
      const fired = res.alerts_fired?.length ?? 0
      set({
        liveView: fresh,
        liveIngestBusy: false,
        liveIngestNote: `${n} claim${n === 1 ? '' : 's'} appended${
          fired ? ` · ${fired} tripwire${fired === 1 ? '' : 's'} fired` : ''
        }.`,
      })
    } catch {
      set({ liveIngestBusy: false, liveIngestNote: 'Ingest failed — nothing was appended.' })
    }
  },

  // LIVE ingest — the KEYED raw-document path: the server runs extraction on the text and
  // appends the resulting claims. It's guarded by CHANAKYA_ENABLE_EXTRACTION (off by default,
  // so a public box can't be made to burn model quota) — when off the server 403s and we say
  // so honestly rather than pretending. On success we refetch /view so the new claims + any
  // fired tripwires land, same as the bundle path. (source_type ∈ the sources.yaml vocabulary.)
  ingestDocLive: async ({ rawText, sourceId, sourceType }) => {
    if (get().mode !== 'live') return
    if (!rawText.trim()) {
      set({ liveIngestNote: 'Paste or drop some document text first.' })
      return
    }
    if (!sourceId.trim() || !sourceType) {
      set({ liveIngestNote: 'Name the source and pick a source type first.' })
      return
    }
    set({ liveIngestBusy: true, liveIngestNote: null })
    try {
      const res = await api.ingest({ raw_text: rawText, source_id: sourceId.trim(), source_type: sourceType })
      const fresh = await api.view()
      const n = res.appended_claim_ids?.length ?? 0
      const fired = res.alerts_fired?.length ?? 0
      set({
        liveView: fresh,
        liveIngestBusy: false,
        liveIngestNote: `${n} claim${n === 1 ? '' : 's'} extracted & appended${
          fired ? ` · ${fired} tripwire${fired === 1 ? '' : 's'} fired` : ''
        }.`,
      })
    } catch (e) {
      let note = 'Extraction failed — nothing was appended.'
      if (e instanceof ApiError) {
        if (e.status === 403) {
          note = 'Raw-document extraction is switched off on this server (needs CHANAKYA_ENABLE_EXTRACTION + a model key) — drop a claim bundle instead.'
        } else {
          const detail =
            e.body && typeof e.body === 'object' && 'detail' in e.body
              ? String((e.body as { detail: unknown }).detail)
              : ''
          note = detail || `Ingest rejected (${e.status}).`
        }
      }
      set({ liveIngestBusy: false, liveIngestNote: note })
    }
  },

  setWeight: (key, val) => set((s) => ({ weights: { ...s.weights, [key]: val } })),

  setMode: (m) => set({ mode: m }),
  setLiveView: (v) => set({ liveView: v }),
}))

// ─────────────────────────── derived selectors ───────────────────────────

/** true once the relocation has landed (d18 or d19 ingested). */
export const selMoved = (s: WorkbenchState) => s.ingested.d18 || s.ingested.d19
/** true once the second, discipline-independent look (d19) lifts the cap. */
export const selRahwaliConfirmed = (s: WorkbenchState) => s.ingested.d19
/** review items not yet decided. */
export const selReviewItems = (s: WorkbenchState) => QUEUE_ITEMS.filter((i) => !s.decided[i.id])
export const selReviewCount = (s: WorkbenchState) => selReviewItems(s).length
/** 4 base sources + d19 + d20 (mockup counts documents). */
export const selSources = (s: WorkbenchState) => 4 + (s.ingested.d19 ? 1 : 0) + (s.ingested.d20 ? 1 : 0)
export const selLooks = (s: WorkbenchState) => 1 + (s.ingested.d19 ? 1 : 0)
/** the hop-2 merge decision has been made → show the revised line. */
export const selHeroRevised = (s: WorkbenchState) => !!s.decided.merge

/** credibility recompute — weighted, not averaged. */
export function scoreSource(
  weights: typeof CRED_DEFAULT_WEIGHTS,
  src: { authority: number; editorial: number; directness: number; track: number },
): number {
  const wsum = weights.authority + weights.editorial + weights.directness + weights.track || 1
  return Math.round(
    (weights.authority * src.authority +
      weights.editorial * src.editorial +
      weights.directness * src.directness +
      weights.track * src.track) /
      wsum,
  )
}
