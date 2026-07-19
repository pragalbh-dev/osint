// Tripwires · Indicators & Warning — read-only (mockup 573-608). Each names the
// indicator it watches; when one fires it routes to Review (the alert-disposition
// card), never straight to the picture. No buttons here — nothing to decide.
import { useWorkbench } from '@/store/workbench'
import { TRIPWIRES, WATCH_INTRO } from '@/demo/scenario'

function BackButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      title="Back"
      className="flex h-[26px] w-[26px] flex-none cursor-pointer items-center justify-center rounded border border-hairline bg-transparent text-[14px] leading-none text-text-dim hover:border-hairline-strong hover:text-text"
    >
      ←
    </button>
  )
}

export function WatchView() {
  const backToZero = useWorkbench((s) => s.backToZero)

  return (
    <div>
      <div className="mb-[6px] flex items-center gap-[10px]">
        <BackButton onClick={backToZero} />
        <span className="text-[10.5px] tracking-[0.06em] text-text-faint">Indicators &amp; warning</span>
      </div>
      <div className="mb-[18px] text-[13px] leading-[1.55] text-text-dim">{WATCH_INTRO}</div>

      <div className="flex flex-col gap-[10px]">
        {TRIPWIRES.map((t) => (
          <div key={t.name} className="rounded border border-hairline px-[14px] py-[13px]">
            <div className="mb-[7px] flex items-center justify-between">
              <span className="text-[13px] text-text">{t.name}</span>
              <span className="rounded-[3px] border border-live px-[7px] py-[1px] font-mono text-[10px] text-live">
                armed
              </span>
            </div>
            <div className="text-[12.5px] leading-[1.5] text-text-dim">{t.desc}</div>
            <div className="mt-2 font-mono text-[10.5px] text-text-faint">indicator · {t.indicator}</div>
          </div>
        ))}
      </div>

      <div className="mt-4 text-[11px] leading-[1.5] text-text-faint">
        Read-only in this build · definitions are user-set, not hardcoded.
      </div>
    </div>
  )
}
