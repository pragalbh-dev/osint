import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import 'leaflet/dist/leaflet.css'
import './styles/globals.css'
import App from './App'
import { useWorkbench } from './store/workbench'

// Optional deep-link into a demo state (QA + presentation aid). Examples:
//   ?panel=hero&merge=1 · ?panel=gaps · ?card=merge · ?stage=graph&ingest=d18,d19 · ?drawer=1
// Applied once before first render so screenshots/links land directly on a beat.
;(() => {
  const p = new URLSearchParams(window.location.search)
  if (![...p.keys()].length) return
  const s = useWorkbench.getState()
  const patch: Record<string, unknown> = {}
  const panel = p.get('panel')
  if (panel) patch.panelView = panel
  const card = p.get('card')
  if (card) {
    patch.panelView = 'card'
    patch.activeCard = card
  }
  const stage = p.get('stage')
  if (stage) patch.stage = stage
  if (p.get('drawer')) {
    patch.drawerOpen = true
    patch.selected = 'rahwali'
  }
  const ingest = p.get('ingest')
  if (ingest) {
    const ing = { ...s.ingested }
    ingest.split(',').forEach((d) => {
      if (d === 'd18' || d === 'd19' || d === 'd20') ing[d] = true
    })
    patch.ingested = ing
  }
  if (p.get('merge')) patch.decided = { ...s.decided, merge: 'Kept separate' }
  const exp = p.get('expanded')
  if (exp) patch.expanded = exp
  if (Object.keys(patch).length) useWorkbench.setState(patch)
})()

// No StrictMode: it double-invokes effects in dev, which double-inits the Leaflet
// map and the Cytoscape instance. The demo must render deterministically.
const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: Infinity, retry: false, refetchOnWindowFocus: false },
  },
})

createRoot(document.getElementById('root')!).render(
  <QueryClientProvider client={queryClient}>
    <App />
  </QueryClientProvider>,
)
