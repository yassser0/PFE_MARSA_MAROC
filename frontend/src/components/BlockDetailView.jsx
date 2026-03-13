import { useMemo } from 'react'
import Plot from 'react-plotly.js'

function buildCubeTraces(xCoords, yCoords, zCoords, color, name, hoverTexts, perfMode = false) {
  if (!xCoords.length) return null

  if (perfMode) {
    return {
      type: 'scatter3d',
      mode: 'markers',
      x: xCoords.map(x => x + 0.4),
      y: yCoords.map(y => y + 0.4),
      z: zCoords.map(z => z + 0.45),
      marker: { symbol: 'square', size: 10, color, opacity: 0.9 },
      name,
      text: hoverTexts,
      hoverinfo: hoverTexts.length ? 'text' : 'name',
    }
  }

  const dx = 0.8, dy = 1.3, dz = 0.9
  const X = [], Y = [], Z = [], I = [], J = [], K = [], textExpanded = []

  xCoords.forEach((x, idx) => {
    const y = yCoords[idx], z = zCoords[idx]
    const base = idx * 8

    X.push(x, x+dx, x+dx, x, x, x+dx, x+dx, x)
    Y.push(y, y, y+dy, y+dy, y, y, y+dy, y+dy)
    Z.push(z, z, z, z, z+dz, z+dz, z+dz, z+dz)

    const i = [7,0,0,0,4,4,6,6,4,0,3,2]
    const j = [3,4,1,2,5,6,5,2,0,1,6,3]
    const k = [0,7,2,3,6,7,1,1,5,5,7,6]
    I.push(...i.map(v => v + base))
    J.push(...j.map(v => v + base))
    K.push(...k.map(v => v + base))

    const txt = hoverTexts[idx] || ''
    for (let q = 0; q < 8; q++) textExpanded.push(txt)
  })

  return {
    type: 'mesh3d',
    x: X, y: Y, z: Z,
    i: I, j: J, k: K,
    color, opacity: 0.9,
    flatshading: true,
    name,
    showscale: false,
    text: textExpanded,
    hoverinfo: hoverTexts.length ? 'text' : 'name',
  }
}

export default function BlockDetailView({ yardData, selectedBlock, onBlockChange, searchQuery, perfMode }) {
  const blockIds = yardData.blocks.map(b => b.block_id)
  const blockData = yardData.blocks.find(b => b.block_id === selectedBlock)

  const traces = useMemo(() => {
    if (!blockData) return []
    const result = []

    const xNorm = [], yNorm = [], zNorm = [], tNorm = []
    const xSearch = [], ySearch = [], zSearch = [], tSearch = []

    for (const stack of blockData.stacks) {
      for (const slot of (stack.slots || [])) {
        if (slot.is_free) continue

        const tierIdx = slot.tier - 1
        const rowX = (stack.row - 1) * 2.5
        const bayY = (stack.bay - 1) * 1.5

        const details = slot.container_details
        let hover = `<b>${slot.container_id}</b>`
        if (details) {
          hover += `<br>Type: ${details.type}<br>Taille: ${details.size}ft<br>Poids: ${details.weight}t<br>Départ: ${details.departure_time}<br>Localisation: ${details.location}`
        }

        const locStr = details?.location || ''
        const isMatch = searchQuery && (searchQuery === slot.container_id || searchQuery === locStr)

        if (isMatch) {
          xSearch.push(rowX); ySearch.push(bayY); zSearch.push(tierIdx); tSearch.push(hover)
        } else {
          xNorm.push(rowX); yNorm.push(bayY); zNorm.push(tierIdx); tNorm.push(hover)
        }
      }
    }

    const normTrace = buildCubeTraces(xNorm, yNorm, zNorm, '#2ca02c', 'Piles', tNorm, perfMode)
    if (normTrace) result.push(normTrace)

    const searchTrace = buildCubeTraces(xSearch, ySearch, zSearch, '#00fdff', 'Résultat', tSearch, perfMode)
    if (searchTrace) result.push(searchTrace)

    return result
  }, [blockData, searchQuery, perfMode])

  const maxB = yardData.n_bays
  const maxR = yardData.n_rows

  const layout = useMemo(() => ({
    scene: {
      xaxis: { title: 'Rangée (X)', range: [-1, maxR * 2.5], backgroundcolor: 'rgba(0,0,0,0)', gridcolor: '#333', showbackground: false },
      yaxis: { title: 'Bay (Y)', range: [-1, maxB * 1.5], backgroundcolor: 'rgba(0,0,0,0)', gridcolor: '#333', showbackground: false },
      zaxis: { title: 'Niveau (Z)', range: [0, yardData.max_height + 1], backgroundcolor: 'rgba(0,0,0,0)', gridcolor: '#333', showbackground: false },
      aspectmode: 'manual',
      aspectratio: { x: 1.5, y: 2, z: 1 },
      bgcolor: 'rgba(0,0,0,0)',
    },
    margin: { l: 0, r: 0, b: 0, t: 0 },
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    legend: { bgcolor: 'rgba(0,0,0,0.5)', font: { color: 'white' } },
    font: { color: '#8B949E', family: 'Inter, sans-serif' },
  }), [maxB, maxR, yardData.max_height])

  // Stats for currently selected block
  const occupancyPct = blockData ? (blockData.occupancy * 100).toFixed(1) : 0

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0, gap: '10px' }}>
      <div className="detail-select-row">
        <label>Choisir le bloc à inspecter :</label>
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
          config={{ responsive: true, displayModeBar: true }}
          style={{ width: '100%', height: '100%' }}
          useResizeHandler
        />
      </div>
    </div>
  )
}
