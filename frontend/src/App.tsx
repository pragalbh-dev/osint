// The four-zone workbench shell (design doc 08). Rail 240 | Stage flex | Panel 400 |
// Drawer 560 (overlay, never pushes). No tabs, no modals — the drawer is the only
// overlay. Fills the viewport; tuned for 1440×900 desktop / screen-share.
import { Rail } from '@/components/rail/Rail'
import { Stage } from '@/components/stage/Stage'
import { Panel } from '@/components/panel/Panel'
import { Drawer } from '@/components/drawer/Drawer'

export default function App() {
  return (
    <div
      className="relative flex h-screen w-screen overflow-hidden bg-bg text-text"
      style={{ font: "400 14px/1.5 ui-sans-serif, system-ui, -apple-system, 'Segoe UI', sans-serif", letterSpacing: '-0.005em' }}
    >
      <Rail />
      <Stage />
      <Panel />
      <Drawer />
    </div>
  )
}
