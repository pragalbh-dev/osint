// Persistent panel footer. The search bar just says "Ask" — never "AI", "search",
// "query" (07-copy-deck voice rules). Placeholder is the hero target query.
//
// DEMO mode (default) is byte-identical: a static readout of the hero query + an Ask
// button that fires the scripted walk. LIVE mode swaps in a real editable input that
// POSTs the typed question to the agent (POST /ask, via store.runAsk). The demo path
// early-returns unchanged so the graded call is never affected.
import { useState } from 'react'
import { useWorkbench } from '@/store/workbench'
import { TARGET_QUERIES } from '@/demo/scenario'

export function AskBar() {
  const mode = useWorkbench((s) => s.mode)
  const askHero = useWorkbench((s) => s.askHero)

  if (mode !== 'live') {
    return (
      <div className="border-t border-hairline bg-surface px-[18px] py-4">
        <div className="flex items-center gap-[10px]">
          <div className="flex h-10 flex-1 items-center overflow-hidden text-ellipsis whitespace-nowrap rounded border border-hairline-strong bg-surface-raised px-[14px] text-[13px] text-text-faint">
            {TARGET_QUERIES.hero}
          </div>
          <button
            onClick={askHero}
            className="h-10 cursor-pointer rounded border border-accent bg-transparent px-[18px] text-[13.5px] text-accent hover:bg-[rgba(74,158,255,0.10)]"
          >
            Ask
          </button>
        </div>
      </div>
    )
  }

  return <LiveAskBar />
}

function LiveAskBar() {
  const runAsk = useWorkbench((s) => s.runAsk)
  const pending = useWorkbench((s) => s.askPending)
  const [text, setText] = useState('')

  const submit = () => {
    if (!text.trim() || pending) return
    void runAsk(text)
    // Clear for the next question — each ask appends a turn to the thread rather than
    // replacing one answer, so the input returns to empty ready for the follow-up.
    setText('')
  }

  return (
    <div className="border-t border-hairline bg-surface px-[18px] py-4">
      <div className="flex items-center gap-[10px]">
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') submit()
          }}
          placeholder={TARGET_QUERIES.hero}
          className="h-10 flex-1 rounded border border-hairline-strong bg-surface-raised px-[14px] text-[13px] text-text placeholder:text-text-faint focus:border-accent focus:outline-none"
        />
        <button
          onClick={submit}
          disabled={pending || !text.trim()}
          className="h-10 cursor-pointer rounded border border-accent bg-transparent px-[18px] text-[13.5px] text-accent hover:bg-[rgba(74,158,255,0.10)] disabled:cursor-default disabled:opacity-45"
        >
          {pending ? 'Asking…' : 'Ask'}
        </button>
      </div>
    </div>
  )
}
