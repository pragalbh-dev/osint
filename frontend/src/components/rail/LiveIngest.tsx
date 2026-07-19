// LIVE ingest surface — two honest paths into the graph:
//   • KEYLESS bundle: drop a .json array of pre-extracted claims → POST /ingest {bundle}.
//   • KEYED document: paste/drop document text, name the source + pick its type → POST
//     /ingest {raw_text, source_id, source_type}; the server runs extraction and appends.
// The keyed path is guarded server-side (CHANAKYA_ENABLE_EXTRACTION, off by default) so a
// public box can't be made to burn model quota — when it's off the store surfaces the 403
// honestly. Either way, a successful ingest refetches /view so new claims + any fired
// tripwire land, and fired tripwires show up in the review queue. Demo keeps its scripted
// drag-to-ingest trace; this mounts only in LIVE mode.

import { useRef, useState } from 'react'
import { useWorkbench } from '@/store/workbench'

// source_type vocabulary (== config/sources.yaml source_type == credibility source classes).
const SOURCE_TYPES = [
  'curated-register',
  'satellite',
  'official',
  'think-tank',
  'trade-media',
  'customs-tender',
  'exporter-state-media',
  'named-social',
  'anon-social',
] as const

function bundleFromText(text: string): Array<Record<string, unknown>> {
  const parsed = JSON.parse(text)
  if (Array.isArray(parsed)) return parsed
  if (parsed && Array.isArray((parsed as { bundle?: unknown }).bundle)) {
    return (parsed as { bundle: Array<Record<string, unknown>> }).bundle
  }
  return []
}

export function LiveIngest() {
  const ingestLive = useWorkbench((s) => s.ingestLive)
  const ingestDocLive = useWorkbench((s) => s.ingestDocLive)
  const busy = useWorkbench((s) => s.liveIngestBusy)
  const note = useWorkbench((s) => s.liveIngestNote)
  const [over, setOver] = useState(false)
  const [docText, setDocText] = useState('')
  const [sourceId, setSourceId] = useState('')
  const [sourceType, setSourceType] = useState<string>('')
  const inputRef = useRef<HTMLInputElement>(null)

  // A dropped/picked .json is a claim bundle (posted immediately); any other file is a raw
  // document — load its text into the form for the analyst to label and extract.
  const handleFile = async (file: File | undefined) => {
    if (!file || busy) return
    const text = await file.text()
    if (file.name.toLowerCase().endsWith('.json')) {
      try {
        await ingestLive(bundleFromText(text))
      } catch {
        await ingestLive([])
      }
    } else {
      setDocText(text)
      if (!sourceId) setSourceId(file.name)
    }
  }

  return (
    <div className="border-b border-hairline px-[18px] py-[14px]">
      <div className="mb-[9px] text-[10.5px] tracking-[0.06em] text-text-faint">Documents</div>

      {/* drop / pick — .json bundle posts straight away; a text doc loads into the form below */}
      <div
        onDragOver={(e) => {
          e.preventDefault()
          setOver(true)
          try {
            e.dataTransfer.dropEffect = 'copy'
          } catch {
            /* noop */
          }
        }}
        onDragLeave={() => setOver(false)}
        onDrop={(e) => {
          e.preventDefault()
          setOver(false)
          void handleFile(e.dataTransfer.files?.[0])
        }}
        onClick={() => inputRef.current?.click()}
        className={`cursor-pointer rounded border border-dashed px-[10px] py-[14px] text-center ${
          over ? 'border-accent' : 'border-hairline-strong'
        }`}
      >
        <div className="text-[11.5px] text-text-dim">{busy ? 'Ingesting…' : 'Drop a document or claim bundle'}</div>
        <div className="mt-[2px] text-[10px] text-text-faint">.json = bundle · text = extract · or click to pick</div>
        <input
          ref={inputRef}
          type="file"
          accept="application/json,.json,.txt,.md,text/plain"
          className="hidden"
          onChange={(e) => {
            void handleFile(e.target.files?.[0])
            e.target.value = ''
          }}
        />
      </div>

      {/* keyed raw-document form — paste text (or a dropped doc lands here), label, extract */}
      <div className="mt-[10px] flex flex-col gap-[7px]">
        <div className="text-[10px] tracking-[0.06em] text-text-faint">or extract a document</div>
        <textarea
          value={docText}
          onChange={(e) => setDocText(e.target.value)}
          placeholder="Paste document text…"
          rows={3}
          className="resize-none rounded border border-hairline-strong bg-surface-raised px-[9px] py-[7px] font-mono text-[10.5px] leading-[1.5] text-text placeholder:text-text-faint focus:border-accent focus:outline-none"
        />
        <input
          value={sourceId}
          onChange={(e) => setSourceId(e.target.value)}
          placeholder="source id (e.g. quwa-2025-06)"
          className="rounded border border-hairline-strong bg-surface-raised px-[9px] py-[6px] font-mono text-[10.5px] text-text placeholder:text-text-faint focus:border-accent focus:outline-none"
        />
        <select
          value={sourceType}
          onChange={(e) => setSourceType(e.target.value)}
          className="rounded border border-hairline-strong bg-surface-raised px-[9px] py-[6px] text-[11px] text-text focus:border-accent focus:outline-none"
        >
          <option value="">source type…</option>
          {SOURCE_TYPES.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
        <button
          type="button"
          disabled={busy || !docText.trim() || !sourceId.trim() || !sourceType}
          onClick={() => void ingestDocLive({ rawText: docText, sourceId, sourceType })}
          className="h-[32px] cursor-pointer rounded border border-accent bg-transparent text-[11.5px] text-accent hover:bg-[rgba(74,158,255,0.10)] disabled:cursor-default disabled:opacity-45"
        >
          {busy ? 'Extracting…' : 'Extract & ingest'}
        </button>
      </div>

      {note && <div className="mt-[10px] font-mono text-[10.5px] leading-[1.5] text-live">{note}</div>}
      <div className="mt-[9px] text-[10px] leading-[1.5] text-text-faint">
        Extraction runs a model server-side (keyed); it's off unless enabled. Bundles are always keyless.
      </div>
    </div>
  )
}
