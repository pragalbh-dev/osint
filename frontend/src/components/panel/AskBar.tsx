// Persistent panel footer. The search bar just says "Ask" — never "AI", "search",
// "query" (07-copy-deck voice rules). Placeholder is the hero target query.
import { useWorkbench } from '@/store/workbench'
import { TARGET_QUERIES } from '@/demo/scenario'

export function AskBar() {
  const askHero = useWorkbench((s) => s.askHero)
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
