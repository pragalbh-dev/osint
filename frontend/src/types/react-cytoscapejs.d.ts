// Minimal type shim — react-cytoscapejs ships no types.
declare module 'react-cytoscapejs' {
  import type { Core, ElementDefinition } from 'cytoscape'
  import type { CSSProperties } from 'react'
  interface CytoscapeComponentProps {
    elements: ElementDefinition[]
    stylesheet?: unknown
    style?: CSSProperties
    className?: string
    layout?: unknown
    cy?: (cy: Core) => void
    zoom?: number
    pan?: { x: number; y: number }
    minZoom?: number
    maxZoom?: number
    zoomingEnabled?: boolean
    userZoomingEnabled?: boolean
    panningEnabled?: boolean
    userPanningEnabled?: boolean
    boxSelectionEnabled?: boolean
    autoungrabify?: boolean
    autounselectify?: boolean
    wheelSensitivity?: number
  }
  const CytoscapeComponent: (props: CytoscapeComponentProps) => JSX.Element
  export default CytoscapeComponent
}
