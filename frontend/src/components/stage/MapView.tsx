// Map view — Leaflet, dark basemap, custom status-coded pins (mockup lines 138-218).
// The user chose Leaflet over the mockup's fixed d3-geo frame specifically for
// pan/zoom roam, so pan/zoom is ENABLED and we fit the AOI once on mount (the one
// deliberate deviation from doc-12's "the frame is fixed for the whole demo").
//
// Pins are L.divIcon (custom HTML) — never default markers, which dodges the
// leaflet marker-icon asset problem. Status is carried by BORDER + FILL, never hue;
// a pin NEVER shows a source tier (that would collapse 60 states to 15). Markers are
// created once and mutated in place so the relocation choreography can transition
// smoothly (~400ms) rather than pop.

import { useEffect, useRef } from 'react'
import L from 'leaflet'
import { AOI } from '@/demo/scenario'
import type { StagePin } from '@/api/adapters'
import { useStagePins } from '@/api/viewmodel'
import { useWorkbench, selMoved, selRahwaliConfirmed } from '@/store/workbench'
import { COLORS } from '@/design/tokens'
import { statusBorder } from '@/components/status/util'

// Vendored CARTO dark_matter tiles (public/tiles/dark), z3-z7 over the Pakistan AOI —
// fully offline, zero network dependency on the graded call. Re-vendor with
// scripts/vendor_tiles.py. BASE_URL keeps the path correct under any mount/subpath.
const TILE_URL = `${import.meta.env.BASE_URL}tiles/dark/{z}/{x}/{y}.png`
const TILE_ATTR = '© OpenStreetMap, © CARTO'

// Per-pin presentation the frozen scenario doesn't carry (label side, centre-dot
// family, the hollow-rect Known-Gap treatment). Deterministic; matches the mockup.
const PIN_UI: Record<
  string,
  { labelPos: 'below' | 'right' | 'left'; dot: 'live' | 'history'; rect?: boolean; dimTitle?: boolean }
> = {
  // label directions radiate outward from each cluster so captions don't collide
  karachi: { labelPos: 'below', dot: 'live' },
  rawalpindi: { labelPos: 'left', dot: 'history' },
  rahwali: { labelPos: 'right', dot: 'live' },
  sargodha: { labelPos: 'below', dot: 'live' },
  tel: { labelPos: 'right', dot: 'live', rect: true, dimTitle: true },
}

// Fallback presentation for LIVE pins the demo's PIN_UI doesn't describe (below-label,
// live centre-dot). Demo pins keep their hand-authored PIN_UI entries.
const DEFAULT_PIN_UI = { labelPos: 'below', dot: 'live' } as const

// four L-shaped corner ticks around the 34×34 frame (mockup 156-159)
const CORNERS = `
  <span style="position:absolute;left:-3px;top:-3px;width:6px;height:6px;border-left:1px solid var(--text-dim);border-top:1px solid var(--text-dim);"></span>
  <span style="position:absolute;right:-3px;top:-3px;width:6px;height:6px;border-right:1px solid var(--text-dim);border-top:1px solid var(--text-dim);"></span>
  <span style="position:absolute;left:-3px;bottom:-3px;width:6px;height:6px;border-left:1px solid var(--text-dim);border-bottom:1px solid var(--text-dim);"></span>
  <span style="position:absolute;right:-3px;bottom:-3px;width:6px;height:6px;border-right:1px solid var(--text-dim);border-bottom:1px solid var(--text-dim);"></span>`

function labelHtml(pos: 'below' | 'right' | 'left', title: string, caption: string, dimTitle?: boolean, below = 38) {
  const wrap =
    pos === 'right'
      ? 'position:absolute;left:40px;top:3px;text-align:left;white-space:nowrap;'
      : pos === 'left'
        ? 'position:absolute;right:40px;top:3px;text-align:right;white-space:nowrap;'
        : `position:absolute;left:50%;top:${below}px;transform:translateX(-50%);text-align:center;white-space:nowrap;`
  const titleColor = dimTitle ? 'var(--text-dim)' : 'var(--text)'
  return `<div style="${wrap}">
    <div style="font-size:11px;color:${titleColor};">${title}</div>
    <div data-caption style="font-size:9.5px;color:var(--text-faint);font-family:ui-monospace,Menlo,monospace;">${caption}</div>
  </div>`
}

// Fill PRESENCE carries knowledge-vs-absence, and the centre dot carries the family —
// so both must come off the pin's STATUS, not off a hand-authored default. A stale pin
// filled teal would draw history as live knowledge; an insufficient pin with a filled
// core would draw an absence of evidence as knowledge. Demo pins are unaffected: their
// hero statuses are confirmed/probable, which keep the fresh fill and the live dot.
function pinCore(pin: StagePin, ui: { dot: 'live' | 'history' }): {
  fill: string
  dot: string
  opacity: string
} {
  // A site whose occupancy was overtaken reads as SETTLED HISTORY — the same solid-grey,
  // reduced-opacity treatment `stale` gets. Deliberately NOT the dashed grey of a Known
  // Gap: "we know this moved" and "we don't know" are opposite claims. Supersession lives
  // on the edge, so the node's own status never carries it (see supersededSites).
  if (pin.superseded || pin.status === 'stale')
    return { fill: 'var(--fill-stale)', dot: 'var(--history)', opacity: 'var(--opacity-stale)' }
  // insufficient = a Known Gap: hollow core, grey dot. Nothing is asserted.
  if (pin.status === 'insufficient')
    return { fill: 'var(--fill-none)', dot: 'var(--history)', opacity: 'var(--opacity-fresh)' }
  // contradicted keeps a fill (evidence exists — it disagrees), but in the problem family,
  // so the pin reads the same way its graph node does rather than coral-on-teal.
  if (pin.status === 'contradicted')
    return { fill: 'var(--fill-problem)', dot: 'var(--problem)', opacity: 'var(--opacity-fresh)' }
  return {
    fill: 'var(--fill-fresh)',
    dot: ui.dot === 'history' ? 'var(--history)' : 'var(--live)',
    opacity: 'var(--opacity-fresh)',
  }
}

function pinHtml(pin: StagePin): string {
  const ui = PIN_UI[pin.id] ?? DEFAULT_PIN_UI
  const core = pinCore(pin, ui)

  if (ui.rect) {
    // TEL count — hollow, dashed Known-Gap rectangle, no fill (mockup 201-206)
    return `
      <div style="position:relative;width:34px;height:26px;display:flex;align-items:center;justify-content:center;">
        <span data-ring style="width:30px;height:22px;border:var(--gap-border-probable-max);background:var(--fill-none);box-shadow:none;transition:box-shadow 200ms ease;"></span>
      </div>
      ${labelHtml(ui.labelPos, pin.label, pin.caption, ui.dimTitle, 32)}`
  }

  const border = pin.superseded ? 'var(--border-stale)' : statusBorder(pin.status)
  return `
    <div style="position:relative;width:34px;height:34px;display:flex;align-items:center;justify-content:center;">
      <span data-ring style="position:absolute;inset:0;border:1px solid rgba(138,148,156,0.32);box-shadow:none;transition:box-shadow 200ms ease;"></span>
      ${CORNERS}
      <span data-core style="width:16px;height:16px;border-radius:50%;border:${border};background:${core.fill};opacity:${core.opacity};display:flex;align-items:center;justify-content:center;transition:border-color 400ms ease, background-color 400ms ease;">
        <span style="width:2.5px;height:2.5px;border-radius:50%;background:${core.dot};"></span>
      </span>
    </div>
    ${labelHtml(ui.labelPos, pin.label, pin.caption, ui.dimTitle)}`
}

function reticleHtml(): string {
  // crosshair + ring + coord readout box (mockup 208-216)
  return `
    <span style="position:absolute;left:0;top:0;width:64px;height:1px;background:rgba(var(--live-rgb),0.5);transform:translate(-50%,-50%);"></span>
    <span style="position:absolute;left:0;top:0;width:1px;height:64px;background:rgba(var(--live-rgb),0.5);transform:translate(-50%,-50%);"></span>
    <span style="position:absolute;left:0;top:0;width:42px;height:42px;border:1px solid rgba(var(--live-rgb),0.55);border-radius:50%;transform:translate(-50%,-50%);"></span>
    <div data-coord style="position:absolute;left:30px;top:-30px;white-space:nowrap;padding:3px 8px;background:var(--surface);border:1px solid var(--hairline-strong);border-radius:4px;font:10px/1.3 ui-monospace,Menlo,monospace;color:var(--live);letter-spacing:0.03em;"></div>`
}

export function MapView() {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const mapRef = useRef<L.Map | null>(null)
  const markersRef = useRef<Record<string, L.Marker>>({})
  const reticleRef = useRef<L.Marker | null>(null)
  const movedLineRef = useRef<L.Polyline | null>(null)
  const movedLabelRef = useRef<L.Marker | null>(null)
  // LIVE supersession connectors, keyed "<superseded>→<successor>" so they survive re-renders.
  const supersedeLayersRef = useRef<Record<string, L.LayerGroup>>({})

  const mode = useWorkbench((s) => s.mode)
  const pins = useStagePins()
  const selected = useWorkbench((s) => s.selected)
  const moved = useWorkbench(selMoved)
  const confirmed = useWorkbench(selRahwaliConfirmed)
  const select = useWorkbench((s) => s.select)

  // mount — create the map, tiles, and pin markers. Rebuilds if the pin set changes
  // (live data arriving); in demo the pin set is a stable reference, so this runs once.
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return
    const map = L.map(containerRef.current, {
      zoomControl: false,
      attributionControl: true,
      // pan/zoom roam — the reason we chose Leaflet
      dragging: true,
      scrollWheelZoom: true,
      doubleClickZoom: true,
      boxZoom: false,
      keyboard: false,
      minZoom: 3,
      maxZoom: 7, // vendored tile range (z3-z7); no un-vendored tile requests
    })
    L.tileLayer(TILE_URL, { attribution: TILE_ATTR, minZoom: 3, maxZoom: 7, maxNativeZoom: 7 }).addTo(map)
    map.fitBounds(AOI.bounds, { padding: [24, 24] })
    mapRef.current = map

    pins.forEach((pin) => {
      const ui = PIN_UI[pin.id] ?? DEFAULT_PIN_UI
      const rect = !!ui.rect
      const icon = L.divIcon({
        html: pinHtml(pin),
        className: '', // '' → drop the default .leaflet-div-icon white box
        iconSize: rect ? [34, 26] : [34, 34],
        iconAnchor: rect ? [17, 13] : [17, 17],
      })
      const marker = L.marker([pin.lat, pin.lon], { icon, riseOnHover: true }).addTo(map)
      marker.on('click', () => select(pin.id))
      const el = marker.getElement()
      if (el) {
        el.style.transition = 'opacity 400ms ease'
        // whole-pin dim (core AND label) for a superseded site, so it recedes as history
        // rather than competing with the live one. Demo pins never set this flag.
        // (numeric, not var(--opacity-stale): CSSOM var() substitution on `opacity` is not
        // reliable across engines. 0.55 IS --opacity-stale — same value the demo pin uses.)
        if (pin.superseded) el.style.opacity = '0.55'
      }
      markersRef.current[pin.id] = marker
    })

    return () => {
      map.remove()
      mapRef.current = null
      markersRef.current = {}
      reticleRef.current = null
      movedLineRef.current = null
      movedLabelRef.current = null
      supersedeLayersRef.current = {}
    }
  }, [pins, select])

  // apply state — relocation choreography + selection reticle/ring, mutating in place
  useEffect(() => {
    const map = mapRef.current
    if (!map) return

    pins.forEach((pin) => {
      const marker = markersRef.current[pin.id]
      const el = marker?.getElement()
      if (!el) return
      const ring = el.querySelector('[data-ring]') as HTMLElement | null
      const core = el.querySelector('[data-core]') as HTMLElement | null
      const caption = el.querySelector('[data-caption]') as HTMLElement | null

      // selection accent ring (interactive highlight — never status) — both modes
      if (ring) ring.style.boxShadow = selected === pin.id ? '0 0 0 1.5px var(--accent-primary)' : 'none'

      // DEMO-only relocation/confirmation choreography, keyed to the hero-thread pins.
      // LIVE pins carry their status/caption from the adapter and never animate here.
      if (mode === 'demo' && pin.id === 'rawalpindi') {
        // selMoved → grey to STALE, superseded caption, ~0.55 opacity
        if (core) {
          core.style.border = moved ? 'var(--border-stale)' : 'var(--border-confirmed)'
          core.style.background = moved ? 'var(--fill-stale)' : 'var(--fill-fresh)'
        }
        el.style.opacity = moved ? '0.55' : '1'
        if (caption) caption.textContent = moved ? 'superseded · 2021' : 'as of 2021'
      }
      if (mode === 'demo' && pin.id === 'rahwali') {
        // selRahwaliConfirmed → border goes SOLID confirmed, confirmed caption
        if (core) core.style.border = confirmed ? 'var(--border-confirmed)' : 'var(--border-probable)'
        if (caption) caption.textContent = confirmed ? 'confirmed · 2025' : 'single pass · 2025'
      }
    })

    // dashed grey "moved →" link, Rawalpindi → Rahwali (DEMO-only choreography)
    const a = pins.find((p) => p.id === 'rawalpindi')
    const b = pins.find((p) => p.id === 'rahwali')
    if (mode === 'demo' && moved && a && b) {
      if (!movedLineRef.current) {
        const line = L.polyline(
          [
            [a.lat, a.lon],
            [b.lat, b.lon],
          ],
          { color: COLORS.history, weight: 1, dashArray: '5 4', interactive: false, opacity: 0 },
        ).addTo(map)
        movedLineRef.current = line
        const path = line.getElement() as SVGElement | null
        if (path) {
          path.style.transition = 'opacity 500ms ease'
          requestAnimationFrame(() => {
            line.setStyle({ opacity: 0.75 })
          })
        }
        const mid: [number, number] = [(a.lat + b.lat) / 2, (a.lon + b.lon) / 2]
        const label = L.marker(mid, {
          interactive: false,
          icon: L.divIcon({
            html: `<span style="font:10px/1 ui-monospace,Menlo,monospace;color:var(--text-dim);white-space:nowrap;">moved →</span>`,
            className: '',
            iconSize: [0, 0],
            iconAnchor: [-6, 12],
          }),
        }).addTo(map)
        movedLabelRef.current = label
      }
    } else {
      if (movedLineRef.current) {
        map.removeLayer(movedLineRef.current)
        movedLineRef.current = null
      }
      if (movedLabelRef.current) {
        map.removeLayer(movedLabelRef.current)
        movedLabelRef.current = null
      }
    }

    // LIVE supersession — a solid grey "replaced by →" connector from the superseded site to
    // the one that replaced it. Same treatment the Graph stage gives a settled `supersedes`
    // edge (solid, --history, arrow, ~0.75) so one story reads the same on both stages. It is
    // deliberately quiet: the line IS the whole treatment — no flash, no pulse, no animation.
    // Solid (not the demo's dashed "moved →") because a settled supersession is history we
    // KNOW, and dashed grey is reserved for an evidence gap.
    {
      const byId = new Map(pins.map((p) => [p.id, p]))
      const wanted = new Map<string, [StagePin, StagePin]>()
      for (const pin of pins) {
        if (!pin.superseded || !pin.supersededBy) continue
        const successor = byId.get(pin.supersededBy)
        if (successor) wanted.set(`${pin.id}→${successor.id}`, [pin, successor])
      }
      for (const [key, layer] of Object.entries(supersedeLayersRef.current)) {
        if (wanted.has(key)) continue
        map.removeLayer(layer)
        delete supersedeLayersRef.current[key]
      }
      for (const [key, [from, to]] of wanted) {
        if (supersedeLayersRef.current[key]) continue
        const group = L.layerGroup([
          L.polyline(
            [
              [from.lat, from.lon],
              [to.lat, to.lon],
            ],
            { color: COLORS.history, weight: 1, interactive: false, opacity: 0.75 },
          ),
          L.marker([(from.lat + to.lat) / 2, (from.lon + to.lon) / 2], {
            interactive: false,
            icon: L.divIcon({
              html: `<span style="font:10px/1 ui-monospace,Menlo,monospace;color:var(--text-dim);white-space:nowrap;">replaced by →</span>`,
              className: '',
              iconSize: [0, 0],
              iconAnchor: [-6, 12],
            }),
          }),
        ]).addTo(map)
        supersedeLayersRef.current[key] = group
      }
    }

    // coordinate reticle on the selected pin (only real map pins have a coord)
    const selPin = pins.find((p) => p.id === selected)
    if (selPin) {
      if (!reticleRef.current) {
        reticleRef.current = L.marker([selPin.lat, selPin.lon], {
          interactive: false,
          zIndexOffset: 1000,
          icon: L.divIcon({ html: reticleHtml(), className: '', iconSize: [0, 0], iconAnchor: [0, 0] }),
        }).addTo(map)
        const rel = reticleRef.current.getElement()
        if (rel) rel.style.pointerEvents = 'none'
      } else {
        reticleRef.current.setLatLng([selPin.lat, selPin.lon])
      }
      const rel = reticleRef.current.getElement()
      const coord = rel?.querySelector('[data-coord]') as HTMLElement | null
      if (coord) coord.textContent = selPin.coord
    } else if (reticleRef.current) {
      map.removeLayer(reticleRef.current)
      reticleRef.current = null
    }
  }, [pins, selected, moved, confirmed, mode])

  return (
    <div className="absolute inset-0">
      {/* Leaflet basemap */}
      <div ref={containerRef} style={{ position: 'absolute', inset: 0, zIndex: 1 }} />

      {/* fixed frame chrome — instrument look, AOI descriptors (mockup 143-150) */}
      <div style={{ position: 'absolute', inset: 14, border: '1px solid var(--hairline)', zIndex: 2, pointerEvents: 'none' }} />
      <div style={{ position: 'absolute', left: 20, top: 56, font: '9.5px/1 ui-monospace,Menlo,monospace', color: 'var(--text-faint)', zIndex: 3, letterSpacing: '0.04em', pointerEvents: 'none' }}>
        AOI · PAKISTAN
      </div>
      <div style={{ position: 'absolute', right: 20, top: 44, font: '9.5px/1 ui-monospace,Menlo,monospace', color: 'var(--text-faint)', zIndex: 3, textAlign: 'right', pointerEvents: 'none' }}>
        WGS-84 · Mercator
      </div>

      {/* legend — mockup 218 */}
      <div
        style={{
          position: 'absolute',
          bottom: 26,
          right: 24,
          font: '10.5px/1.4 ui-monospace,Menlo,monospace',
          color: 'var(--text-faint)',
          textAlign: 'right',
          zIndex: 4,
          pointerEvents: 'none',
        }}
      >
        solid = settled · dashed = provisional
      </div>
    </div>
  )
}
