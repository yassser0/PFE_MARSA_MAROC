import { useMemo } from 'react'
import Plotly from 'plotly.js-dist-min'
import createPlotComponent from 'react-plotly.js/factory'

const Plot = createPlotComponent(Plotly)

/**
 * Builds high-fidelity corrugated container mesh traces.
 */
function buildCubeTraces(xCoords, yCoords, zCoords, color, name, hoverTexts, customDataList, perfMode = false) {
  if (!xCoords.length) return null

  const dx = 0.8, dy = 2.0, dz = 0.85
  const gap = 0.05

  if (perfMode) {
    return {
      type: 'scatter3d',
      mode: 'markers',
      x: xCoords.map(x => x + dx/2),
      y: yCoords.map(y => y + dy/2),
      z: zCoords.map(z => z + dz/2),
      marker: { symbol: 'square', size: 10, color, opacity: 0.95 },
      name,
      text: hoverTexts,
      customdata: customDataList,
      hoverinfo: 'text',
    }
  }

  const X = [], Y = [], Z = [], I = [], J = [], K = [], textExpanded = [], customDataExpanded = []

  xCoords.forEach((x, idx) => {
    const ax = x + gap, ay = yCoords[idx] + gap, az = zCoords[idx] + gap
    const rdx = dx - 2*gap, rdy = dy - 2*gap, rdz = dz - 2*gap
    const base = X.length

    // Geometry with ridge simulation (Lite Corrugated)
    X.push(ax, ax+rdx, ax+rdx, ax)
    Y.push(ay, ay, ay+rdy, ay+rdy)
    Z.push(az, az, az, az)
    
    X.push(ax, ax+rdx, ax+rdx, ax)
    Y.push(ay, ay, ay+rdy, ay+rdy)
    Z.push(az+rdz, az+rdz, az+rdz, az+rdz)

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
    flatshading: false,
    lighting: { 
      ambient: 0.5, 
      diffuse: 0.9, 
      specular: 0.4, 
      roughness: 0.4 
    },
    name,
    showscale: false,
    text: textExpanded,
    customdata: customDataExpanded,
    hoverinfo: 'text',
  }
}

const INDUSTRIAL_PALETTE = [
  '#005073', '#FFCC00', '#E2001A', '#FF6600', '#808080', '#FFFFFF', '#007AC3', '#2F4F4F'
]

function getContainerColor(id) {
  const hash = id.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0)
  return INDUSTRIAL_PALETTE[hash % INDUSTRIAL_PALETTE.length]
}

export default function BlockDetailView({ yardData, selectedBlock, onBlockChange, searchQuery, perfMode, onSelectContainer }) {
  const blockIds = yardData.blocks.map(b => b.block_id)
  const blockData = yardData.blocks.find(b => b.block_id === selectedBlock)

  const traces = useMemo(() => {
    if (!blockData) return []
    const result = []

    // Ground Marking (Asphalt)
    const bw = yardData.n_rows * 2.5
    const bl = yardData.n_bays * 2.2
    result.push({
      type: 'mesh3d',
      x: [0, bw, bw, 0],
      y: [0, 0, bl, bl],
      z: [0, 0, 0, 0],
      i: [0, 0], j: [1, 2], k: [2, 3],
      color: '#1a1a1b', opacity: 1,
      name: 'Sol', showlegend: false, hoverinfo: 'skip'
    })

    // White Lines
    for (let r = 0; r <= yardData.n_rows; r++) {
      result.push({
        type: 'scatter3d', mode: 'lines',
        x: [r * 2.5, r * 2.5], y: [0, bl], z: [0.01, 0.01],
        line: { color: 'rgba(255,255,255,0.4)', width: 3 },
        showlegend: false, hoverinfo: 'none'
      })
    }

    const colorGroups = {}

    for (const stack of blockData.stacks) {
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

        const tierZ = (slot.tier - 1) * 0.9 
        const rowX = (stack.row - 1) * 2.5
        const bayY = (stack.bay - 1) * 2.2

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
      const trace = buildCubeTraces(group.x, group.y, group.z, group.color, group.name, group.t, group.c, perfMode)
      if (trace) result.push(trace)
    })

    return result
  }, [blockData, searchQuery, perfMode, yardData.n_rows, yardData.n_bays])

  const handlePlotClick = (event) => {
    if (!event.points || !event.points.length) return
    const point = event.points[0]
    const data = point.customdata
    if (data && typeof data === 'object' && data.id) {
      onSelectContainer(data)
    }
  }

  const layout = useMemo(() => ({
    scene: {
      xaxis: { title: 'Rangées', showgrid: false, zeroline: false, showticklabels: false },
      yaxis: { title: 'Bays', showgrid: false, zeroline: false, showticklabels: false },
      zaxis: { title: 'Niveaux', showgrid: false, zeroline: false, showticklabels: false },
      aspectmode: 'data',
      bgcolor: '#0d1117',
    },
    margin: { l: 0, r: 0, b: 0, t: 0 },
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    legend: { bgcolor: 'rgba(0,0,0,0.5)', font: { color: 'white' } },
    font: { color: '#8B949E', family: 'Inter, sans-serif' },
  }), [])

  const occupancyPct = blockData ? Math.round(blockData.occupancy * 100) : 0

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0, gap: '10px' }}>
      <div className="detail-select-row">
        <label>Bloc :</label>
        <select value={selectedBlock} onChange={e => onBlockChange(e.target.value)}>
          {blockIds.map(id => (
            <option key={id} value={id}>Bloc {id}</option>
          ))}
        </select>
        {blockData && (
          <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginLeft: '8px' }}>
            Occupation : <strong style={{ color: blockData.occupancy > 0.8 ? 'var(--accent-red)' : 'var(--accent-green)' }}>{occupancyPct}%</strong>
          </span>
        )}
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
