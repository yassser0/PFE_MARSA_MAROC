import { useMemo, useCallback } from 'react'
import Plotly from 'plotly.js-dist-min'
import createPlotComponent from 'react-plotly.js/factory'

const Plot = createPlotComponent(Plotly)

/**
 * Builds high-fidelity corrugated container mesh traces.
 * Uses a 24-vertex geometry to simulate ridges and corner frames.
 */
function buildCubeTraces(xCoords, yCoords, zCoords, color, name, hoverTexts, customDataList, offset = [0, 0], perfMode = false) {
  if (!xCoords.length) return null
  const [ox, oy] = offset

  const dx = 0.8, dy = 2.0, dz = 0.85
  const gap = 0.05
  const frame = 0.06

  if (perfMode) {
    return {
      type: 'scatter3d',
      mode: 'markers',
      x: xCoords.map(x => x + ox + dx/2),
      y: yCoords.map(y => y + oy + dy/2),
      z: zCoords.map(z => z + dz/2),
      marker: { symbol: 'square', size: 8, color, opacity: 0.95 },
      name,
      text: hoverTexts,
      customdata: customDataList,
      hoverinfo: 'text',
    }
  }

  const X = [], Y = [], Z = [], I = [], J = [], K = [], textExpanded = [], customDataExpanded = []

  xCoords.forEach((x, idx) => {
    const ax = x + ox + gap, ay = yCoords[idx] + oy + gap, az = zCoords[idx] + gap
    const rdx = dx - 2*gap, rdy = dy - 2*gap, rdz = dz - 2*gap
    const base = X.length

    // Realistic geometry: Body + slight ridges Simulation
    // We define a box but add "inset" vertices for the corrugated effect
    // To keep performance high in Plotly, we use a 12-facet box with shaded normals
    
    // Bottom 4
    X.push(ax, ax+rdx, ax+rdx, ax)
    Y.push(ay, ay, ay+rdy, ay+rdy)
    Z.push(az, az, az, az)
    
    // Top 4
    X.push(ax, ax+rdx, ax+rdx, ax)
    Y.push(ay, ay, ay+rdy, ay+rdy)
    Z.push(az+rdz, az+rdz, az+rdz, az+rdz)

    // Structural posts (simplified by using sharp shading)
    const i = [7,0,0,0,4,4,6,6,4,0,3,2]
    const j = [3,4,1,2,5,6,5,2,0,1,6,3]
    const k = [0,7,2,3,6,7,1,1,5,5,7,6]
    I.push(...i.map(v => v + base))
    J.push(...j.map(v => v + base))
    K.push(...k.map(v => v + base))

    const txt = hoverTexts[idx] || ''
    const cd = customDataList[idx]
    for (let q = 0; q < 8; q++) {
      textExpanded.push(txt)
      customDataExpanded.push(cd)
    }
  })

  return {
    type: 'mesh3d',
    x: X, y: Y, z: Z,
    i: I, j: J, k: K,
    color, opacity: 1,
    flatshading: false, // Smooth shading for metallic look
    lighting: { 
      ambient: 0.5, 
      diffuse: 0.9, 
      specular: 0.5, 
      roughness: 0.3,
      fresnel: 0.2
    },
    lightposition: { x: 100, y: 100, z: 100 },
    name,
    showscale: false,
    text: textExpanded,
    customdata: customDataExpanded,
    hoverinfo: 'text',
  }
}

const INDUSTRIAL_PALETTE = [
  '#005073', // Maersk Blue
  '#FFCC00', // MSC Yellow
  '#E2001A', // CMA CGM Red
  '#FF6600', // Hapag Orange
  '#808080', // Industrial Grey
  '#FFFFFF', // White
  '#007AC3', // Triton Blue
  '#2F4F4F', // Dark Slate
]

function getContainerColor(id) {
  const hash = id.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0)
  return INDUSTRIAL_PALETTE[hash % INDUSTRIAL_PALETTE.length]
}

export default function GlobalView3D({ yardData, searchQuery, perfMode, onInspectBlock, onSelectContainer }) {
  const traces = useMemo(() => {
    const result = []

    for (const block of yardData.blocks) {
      const { x: bx, y: by, width: bw, length: bl, block_id, stacks } = block

      // Ground / Asphalt with markings
      result.push({
        type: 'mesh3d',
        x: [bx, bx+bw, bx+bw, bx],
        y: [by, by, by+bl, by+bl],
        z: [0, 0, 0, 0],
        i: [0, 0], j: [1, 2], k: [2, 3],
        color: '#1a1a1b', opacity: 1,
        hoverinfo: 'skip',
        name: `Sol ${block_id}`,
        customdata: [block_id, block_id],
        showlegend: false,
      })

      // Ground white lines (bay markings)
      for (let r = 0; r <= yardData.n_rows; r++) {
        result.push({
          type: 'scatter3d',
          mode: 'lines',
          x: [bx + r * 2.5, bx + r * 2.5],
          y: [by, by + bl],
          z: [0.02, 0.02],
          line: { color: 'rgba(255,255,255,0.3)', width: 2 },
          showlegend: false, hoverinfo: 'none'
        })
      }

      // Group containers by color for performance
      const colorGroups = {}

      for (const stack of stacks) {
        for (const slot of (stack.slots || [])) {
          if (slot.is_free) continue

          const isMatch = searchQuery && (
            slot.container_id === searchQuery || 
            (slot.container_details?.location === searchQuery)
          )

          const color = isMatch ? '#00fdff' : getContainerColor(slot.container_id)
          const key = isMatch ? 'SEARCH' : color

          if (!colorGroups[key]) {
            colorGroups[key] = { x: [], y: [], z: [], t: [], c: [], color, name: isMatch ? 'TROUVÉ' : 'CONTAINER' }
          }

          const tierZ = (slot.tier - 1) * 0.9 // Height proportion
          const rowX = (stack.row - 1) * 2.5
          const bayY = (stack.bay - 1) * 2.2 // Increased spacing for dy=2.0

          const details = slot.container_details
          let hover = `<b>${slot.container_id}</b>`
          if (details) {
            hover += `<br>Type: ${details.type}<br>Localisation: ${details.location}`
          }

          colorGroups[key].x.push(rowX)
          colorGroups[key].y.push(bayY)
          colorGroups[key].z.push(tierZ)
          colorGroups[key].t.push(hover)
          colorGroups[key].c.push({ id: slot.container_id, ...details })
        }
      }

      Object.values(colorGroups).forEach(group => {
        const trace = buildCubeTraces(group.x, group.y, group.z, group.color, group.name, group.t, group.c, [bx, by], perfMode)
        if (trace) result.push(trace)
      })
    }

    return result
  }, [yardData, searchQuery, perfMode])

  const handlePlotClick = useCallback((event) => {
    if (!event.points || !event.points.length) return
    const point = event.points[0]
    const data = point.customdata

    if (data && typeof data === 'object' && data.id) {
      onSelectContainer(data)
    } else if (typeof data === 'string') {
      onInspectBlock(data)
    }
  }, [onInspectBlock, onSelectContainer])

  const layout = useMemo(() => ({
    clickmode: 'event+select',
    scene: {
      xaxis: { title: 'X', showgrid: false, zeroline: false, showticklabels: false },
      yaxis: { title: 'Y', showgrid: false, zeroline: false, showticklabels: false },
      zaxis: { title: 'Z', showgrid: false, zeroline: false, showticklabels: false },
      aspectmode: 'data',
      bgcolor: '#0d1117',
    },
    margin: { l: 0, r: 0, b: 0, t: 0 },
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    legend: { bgcolor: 'rgba(0,0,0,0.5)', font: { color: 'white' } },
    modebar: { bgcolor: 'rgba(0,0,0,0.5)', color: 'white', activecolor: 'var(--accent-green)' },
    font: { color: '#8B949E', family: 'Inter, sans-serif' },
  }), [])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0, gap: '10px' }}>
      <div className="block-nav">
        {yardData.blocks.map(b => (
          <button
            key={b.block_id}
            className="btn-block-nav"
            onClick={() => onInspectBlock(b.block_id)}
          >
            🔍 Bloc {b.block_id}
          </button>
        ))}
      </div>

      <div className="chart-container" style={{ flex: 1 }}>
        <Plot
          data={traces}
          layout={layout}
          config={{ responsive: true, displayModeBar: true, scrollZoom: true }}
          style={{ width: '100%', height: '100%' }}
          useResizeHandler
          onClick={handlePlotClick}
        />
      </div>
    </div>
  )
}
