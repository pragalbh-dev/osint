// The workbench state machine (Zustand). Ports the handoff mockup's component
// logic: stage/panel/drawer/selection, the review queue + decisions, the scripted
// ingest trace, and the live credibility recompute. DEMO mode is deterministic and
// identical on every run (the graded non-negotiable); LIVE mode swaps in real API data.

import { create } from 'zustand'
import type { GraphView } from '@/api/types'
import {
  CRED_DEFAULT_WEIGHTS,
  DECISION_LABELS,
  INGEST_DOCS,
  QUEUE_ITEMS,
  type CardId,
} from '@/demo/scenario'

export type Stage = 'map' | 'graph'
export type PanelView = 'zero' | 'hero' | 'gaps' | 'card' | 'cred' | 'watch'
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

  // navigation
  setStage: (s: Stage) => void
  askHero: () => void
  askGaps: () => void
  backToZero: () => void
  openCred: () => void
  openWatch: () => void

  // review queue
  toggleReview: () => void
  openCard: (id: CardId) => void
  decide: (decisionKey: string) => void

  // selection / drawer
  select: (id: string | null) => void
  openDrawer: () => void
  closeDrawer: () => void
  toggleChip: (id: string) => void

  // ingest (scripted trace)
  startIngest: (doc: DocId) => void
  resetIngest: () => void

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

  setStage: (s) => set({ stage: s }),
  askHero: () => set({ panelView: 'hero' }),
  askGaps: () => set({ panelView: 'gaps' }),
  backToZero: () => set({ panelView: 'zero' }),
  openCred: () => set({ panelView: 'cred' }),
  openWatch: () => set({ panelView: 'watch' }),

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

  // Rahwali is the demo's provenance entry point — selecting it opens the drawer.
  select: (id) =>
    set(id === 'rahwali' ? { selected: 'rahwali', drawerOpen: true } : { selected: id }),
  openDrawer: () => set({ drawerOpen: true }),
  closeDrawer: () => set({ drawerOpen: false }),
  toggleChip: (id) => set((s) => ({ expanded: s.expanded === id ? null : id })),

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
