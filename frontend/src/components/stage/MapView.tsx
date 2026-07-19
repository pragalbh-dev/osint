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
import { AOI, PINS } from '@/demo/scenario'
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

const pinById = (id: string) => PINS.find((p) => p.id === id)!

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

function pinHtml(id: string): string {
  const pin = pinById(id)
  const ui = PIN_UI[id]
  const dot = ui.dot === 'history' ? 'var(--history)' : 'var(--live)'

  if (ui.rect) {
    // TEL count — hollow, dashed Known-Gap rectangle, no fill (mockup 201-206)
    return `
      <div style="position:relative;width:34px;height:26px;display:flex;align-items:center;justify-content:center;">
        <span data-ring style="width:30px;height:22px;border:var(--gap-border-probable-max);background:var(--fill-none);box-shadow:none;transition:box-shadow 200ms ease;"></span>
      </div>
      ${labelHtml(ui.labelPos, pin.label, pin.caption, ui.dimTitle, 32)}`
  }

  const border = statusBorder(pin.status)
  return `
    <div style="position:relative;width:34px;height:34px;display:flex;align-items:center;justify-content:center;">
      <span data-ring style="position:absolute;inset:0;border:1px solid rgba(138,148,156,0.32);box-shadow:none;transition:box-shadow 200ms ease;"></span>
      ${CORNERS}
      <span data-core style="width:16px;height:16px;border-radius:50%;border:${border};background:var(--fill-fresh);display:flex;align-items:center;justify-content:center;transition:border-color 400ms ease, background-color 400ms ease;">
        <span style="width:2.5px;height:2.5px;border-radius:50%;background:${dot};"></span>
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

  const selected = useWorkbench((s) => s.selected)
  const moved = useWorkbench(selMoved)
  const confirmed = useWorkbench(selRahwaliConfirmed)
  const select = useWorkbench((s) => s.select)

  // mount — create the map, tiles, and the (stable) pin markers once
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

    PINS.forEach((pin) => {
      const ui = PIN_UI[pin.id]
      const rect = !!ui.rect
      const icon = L.divIcon({
        html: pinHtml(pin.id),
        className: '', // '' → drop the default .leaflet-div-icon white box
        iconSize: rect ? [34, 26] : [34, 34],
        iconAnchor: rect ? [17, 13] : [17, 17],
      })
      const marker = L.marker([pin.lat, pin.lon], { icon, riseOnHover: true }).addTo(map)
      marker.on('click', () => select(pin.id))
      const el = marker.getElement()
      if (el) el.style.transition = 'opacity 400ms ease'
      markersRef.current[pin.id] = marker
    })

    return () => {
      map.remove()
      mapRef.current = null
      markersRef.current = {}
      reticleRef.current = null
      movedLineRef.current = null
      movedLabelRef.current = null
    }
  }, [select])

  // apply state — relocation choreography + selection reticle/ring, mutating in place
  useEffect(() => {
    const map = mapRef.current
    if (!map) return

    PINS.forEach((pin) => {
      const marker = markersRef.current[pin.id]
      const el = marker?.getElement()
      if (!el) return
      const ring = el.querySelector('[data-ring]') as HTMLElement | null
      const core = el.querySelector('[data-core]') as HTMLElement | null
      const caption = el.querySelector('[data-caption]') as HTMLElement | null

      // selection accent ring (interactive highlight — never status)
      if (ring) ring.style.boxShadow = selected === pin.id ? '0 0 0 1.5px var(--accent-primary)' : 'none'

      if (pin.id === 'rawalpindi') {
        // selMoved → grey to STALE, superseded caption, ~0.55 opacity
        if (core) {
          core.style.border = moved ? 'var(--border-stale)' : 'var(--border-confirmed)'
          core.style.background = moved ? 'var(--fill-stale)' : 'var(--fill-fresh)'
        }
        el.style.opacity = moved ? '0.55' : '1'
        if (caption) caption.textContent = moved ? 'superseded · 2021' : 'as of 2021'
      }
      if (pin.id === 'rahwali') {
        // selRahwaliConfirmed → border goes SOLID confirmed, confirmed caption
        if (core) core.style.border = confirmed ? 'var(--border-confirmed)' : 'var(--border-probable)'
        if (caption) caption.textContent = confirmed ? 'confirmed · 2025' : 'single pass · 2025'
      }
    })

    // dashed grey "moved →" link, Rawalpindi → Rahwali
    if (moved) {
      if (!movedLineRef.current) {
        const a = pinById('rawalpindi')
        const b = pinById('rahwali')
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

    // coordinate reticle on the selected pin (only real map pins have a coord)
    const selPin = PINS.find((p) => p.id === selected)
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
  }, [selected, moved, confirmed])

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
