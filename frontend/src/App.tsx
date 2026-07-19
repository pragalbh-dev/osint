// The four-zone workbench shell (design doc 08). Rail 240 | Stage flex | Panel 400 |
// Drawer 560 (overlay, never pushes). No tabs, no modals — the drawer is the only
// overlay. Fills the viewport; tuned for 1440×900 desktop / screen-share.
import { Rail } from '@/components/rail/Rail'
import { Stage } from '@/components/stage/Stage'
import { Panel } from '@/components/panel/Panel'
import { DrawerHost } from '@/components/drawer/DrawerHost'
import { ModeToggle } from '@/components/dev/ModeToggle'
import { useLiveSync } from '@/api/hooks'

export default function App() {
  // LIVE mode: mirror GET /view into the store so the stage can render real data.
  // A genuine no-op in DEMO mode (no fetch, liveView stays null) — demo untouched.
  useLiveSync()
  return (
    <div
      className="relative flex h-screen w-screen overflow-hidden bg-bg text-text"
      style={{ font: "400 14px/1.5 ui-sans-serif, system-ui, -apple-system, 'Segoe UI', sans-serif", letterSpacing: '-0.005em' }}
    >
      <Rail />
      <Stage />
      <Panel />
      <DrawerHost />
      {import.meta.env.DEV && <ModeToggle />}
    </div>
  )
}
