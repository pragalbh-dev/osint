// Typed fetch client for the Chanakya backend. Same-origin in production; in dev
// the Vite proxy forwards these paths to :8000. Only GET /health and GET /view are
// implemented today; the rest are frozen contracts whose routes land later. The app
// defaults to deterministic DEMO mode (see src/store) and calls these only in LIVE mode.

import type {
  AskAnswer,
  AskRequest,
  ConfigWrite,
  ConfigWriteResult,
  GraphView,
  HealthResponse,
  HitlDecision,
  IngestRequest,
  IngestResult,
  ProvenanceDrawer,
} from './types'

const BASE = import.meta.env.VITE_API_BASE ?? '' // '' = same-origin

export class ApiError extends Error {
  constructor(
    public status: number,
    public body: unknown,
    message?: string,
  ) {
    super(message ?? `API ${status}`)
    this.name = 'ApiError'
  }
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'content-type': 'application/json', ...(init?.headers ?? {}) },
    ...init,
  })
  const text = await res.text()
  const body = text ? JSON.parse(text) : null
  if (!res.ok) throw new ApiError(res.status, body, `${init?.method ?? 'GET'} ${path} → ${res.status}`)
  return body as T
}

const post = <T>(path: string, data: unknown) =>
  req<T>(path, { method: 'POST', body: JSON.stringify(data) })

export const api = {
  // ── live today ──
  health: () => req<HealthResponse>('/health'),
  view: (subject?: string) =>
    req<GraphView>(`/view${subject ? `?subject=${encodeURIComponent(subject)}` : ''}`),

  // ── frozen contracts; routes land later ──
  evidence: (id: string) => req<ProvenanceDrawer>(`/evidence/${encodeURIComponent(id)}`),
  node: (id: string) => req<unknown>(`/node/${encodeURIComponent(id)}`),
  ask: (body: AskRequest) => post<AskAnswer>('/ask', body),
  ingest: (body: IngestRequest) => post<IngestResult>('/ingest', body),
  hitl: (verb: 'merge' | 'status' | 'alert', body: HitlDecision) =>
    post<unknown>(`/hitl/${verb}`, body),
  config: (section: string, body: ConfigWrite) => post<ConfigWriteResult>(`/config/${section}`, body),
} as const
