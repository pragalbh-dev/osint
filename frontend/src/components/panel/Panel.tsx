// The panel — "whatever I'm deciding about right now." One slot, swaps by view,
// NO tabs. Persistent Ask bar footer. Answer, review card, and node inspector never
// coexist. (design doc 08 · the panel principle)
import { useWorkbench } from '@/store/workbench'
import { AskBar } from './AskBar'
import { ZeroView } from './views/ZeroView'
import { HeroAnswer } from './views/HeroAnswer'
import { GapsView } from './views/GapsView'
import { MergeCard } from './views/MergeCard'
import { OverrideCard } from './views/OverrideCard'
import { AlertCard } from './views/AlertCard'
import { CredView } from './views/CredView'
import { WatchView } from './views/WatchView'

export function Panel() {
  const panelView = useWorkbench((s) => s.panelView)
  const activeCard = useWorkbench((s) => s.activeCard)

  return (
    <section className="flex w-[400px] flex-none flex-col border-l border-hairline bg-surface">
      <div className="flex-1 overflow-auto px-[22px] pb-3 pt-[22px]">
        {panelView === 'zero' && <ZeroView />}
        {panelView === 'hero' && <HeroAnswer />}
        {panelView === 'gaps' && <GapsView />}
        {panelView === 'cred' && <CredView />}
        {panelView === 'watch' && <WatchView />}
        {panelView === 'card' && activeCard === 'merge' && <MergeCard />}
        {panelView === 'card' && activeCard === 'override' && <OverrideCard />}
        {panelView === 'card' && activeCard === 'alert' && <AlertCard />}
      </div>
      <AskBar />
    </section>
  )
}
