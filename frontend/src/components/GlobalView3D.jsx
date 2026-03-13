import { useMemo, useCallback } from 'react'
import Plot from 'react-plotly.js'

/**
 * Builds cube mesh traces for plotly (same algorithm as dashboard.py).
 * In perf mode, uses Scatter3d with square markers instead of full meshes.
 */
function buildCubeTraces(xCoords, yCoords, zCoords, color, name, hoverTexts, customDataList, offset = [0, 0], perfMode = false) {
  if (!xCoords.length) return null
  const [ox, oy] = offset

  if (perfMode) {
    return {
      type: 'scatter3d',
      mode: 'markers',
      x: xCoords.map(x => x + ox + 0.4),
      y: yCoords.map(y => y + oy + 0.4),
      z: zCoords.map(z => z + 0.45),
      marker: { symbol: 'square', size: 8, color, opacity: 0.9 },
      name,
      text: hoverTexts,
      customdata: customDataList,
      hoverinfo: hoverTexts.length ? 'text' : 'name',
    }
  }

  const dx = 0.8, dy = 1.3, dz = 0.9
  const X = [], Y = [], Z = [], I = [], J = [], K = [], textExpanded = [], customDataExpanded = []

  xCoords.forEach((x, idx) => {
    const ax = x + ox, ay = yCoords[idx] + oy
    const z = zCoords[idx]
    const base = idx * 8

    X.push(ax, ax+dx, ax+dx, ax, ax, ax+dx, ax+dx, ax)
    Y.push(ay, ay, ay+dy, ay+dy, ay, ay, ay+dy, ay+dy)
    Z.push(z, z, z, z, z+dz, z+dz, z+dz, z+dz)

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
    color, opacity: 0.9,
    flatshading: true,
    name,
    showscale: false,
    text: textExpanded,
    customdata: customDataExpanded,
    hoverinfo: hoverTexts.length ? 'text' : 'name',
  }
}

export default function GlobalView3D({ yardData, searchQuery, perfMode, onInspectBlock, onSelectContainer }) {
  const traces = useMemo(() => {
    const result = []

    for (const block of yardData.blocks) {
      const { x: bx, y: by, width: bw, length: bl, block_id, stacks } = block

      // Floor mesh for each block
      result.push({
        type: 'mesh3d',
        x: [bx, bx+bw, bx+bw, bx],
        y: [by, by, by+bl, by+bl],
        z: [0.01, 0.01, 0.01, 0.01],
        i: [0, 0], j: [1, 2], k: [2, 3],
        color: '#4a9eff', opacity: 0.06,
        hoverinfo: 'skip',
        name: `Sol ${block_id}`,
        customdata: [block_id, block_id], // For block click identification
        showlegend: false,
      })

      // Block label
      result.push({
        type: 'scatter3d',
        mode: 'text',
        x: [bx + bw / 2],
        y: [by + bl / 2],
        z: [yardData.max_height + 1.5],
        text: [`Bloc ${block_id}`],
        textfont: { color: 'white', size: 10 },
        showlegend: false,
        hoverinfo: 'none',
        name: `Label ${block_id}`,
      })

      // Containers
      const xNorm = [], yNorm = [], zNorm = [], tNorm = [], cNorm = []
      const xSearch = [], ySearch = [], zSearch = [], tSearch = [], cSearch = []

      for (const stack of stacks) {
        for (const slot of (stack.slots || [])) {
          if (slot.is_free) continue

          const tierIdx = slot.tier - 1
          const rowXOffset = (stack.row - 1) * 2.5
          const bayYOffset = (stack.bay - 1) * 1.5

          const details = slot.container_details
          let hover = `<b>${slot.container_id}</b>`
          if (details) {
            hover += `<br>Type: ${details.type}<br>Taille: ${details.size}ft<br>Poids: ${details.weight}t<br>Départ: ${details.departure_time}<br>Localisation: ${details.location}`
          }

          const locStr = details?.location || ''
          const isMatch = searchQuery && (searchQuery === slot.container_id || searchQuery === locStr)

          const containerData = {
            id: slot.container_id,
            ...details
          }

          if (isMatch) {
            xSearch.push(rowXOffset); ySearch.push(bayYOffset); zSearch.push(tierIdx); tSearch.push(hover); cSearch.push(containerData)
          } else {
            xNorm.push(rowXOffset); yNorm.push(bayYOffset); zNorm.push(tierIdx); tNorm.push(hover); cNorm.push(containerData)
          }
        }
      }

      const normTrace = buildCubeTraces(xNorm, yNorm, zNorm, '#2ca02c', `B-${block_id}`, tNorm, cNorm, [bx, by], perfMode)
      if (normTrace) result.push(normTrace)

      const searchTrace = buildCubeTraces(xSearch, ySearch, zSearch, '#00fdff', 'Trouvé', tSearch, cSearch, [bx, by], perfMode)
      if (searchTrace) result.push(searchTrace)
    }

    return result
  }, [yardData, searchQuery, perfMode])

  const handlePlotClick = useCallback((event) => {
    if (!event.points || !event.points.length) return
    const point = event.points[0]
    const data = point.customdata

    if (data && typeof data === 'object' && data.id) {
      // Container select
      onSelectContainer(data)
    } else if (typeof data === 'string') {
      // Block select (floor click)
      onInspectBlock(data)
    }
  }, [onInspectBlock, onSelectContainer])

  const layout = useMemo(() => ({
    clickmode: 'event+select',
    scene: {
      xaxis: { title: 'Axe Transversal (X: Rangées)', backgroundcolor: 'rgba(0,0,0,0)', gridcolor: '#333', showbackground: false },
      yaxis: { title: 'Axe Longitudinal (Y: Bays)', backgroundcolor: 'rgba(0,0,0,0)', gridcolor: '#333', showbackground: false },
      zaxis: { title: 'Élévation (Z: Niveaux)', range: [0, yardData.max_height + 2], backgroundcolor: 'rgba(0,0,0,0)', gridcolor: '#333', showbackground: false },
      aspectmode: 'data',
      bgcolor: 'rgba(0,0,0,0)',
    },
    margin: { l: 0, r: 0, b: 0, t: 0 },
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    legend: { bgcolor: 'rgba(0,0,0,0.5)', font: { color: 'white' } },
    modebar: { bgcolor: 'rgba(0,0,0,0.5)', color: 'white', activecolor: 'var(--accent-green)' },
    font: { color: '#8B949E', family: 'Inter, sans-serif' },
  }), [yardData.max_height])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0, gap: '10px' }}>
      <div className="block-nav">
        {yardData.blocks.map(b => (
          <button
            key={b.block_id}
            className="btn-block-nav"
            onClick={() => onInspectBlock(b.block_id)}
          >
            🔍 Inspecter Bloc {b.block_id}
          </button>
        ))}
      </div>

      <div className="chart-container" style={{ flex: 1 }}>
        <Plot
          data={traces}
          layout={layout}
          config={{ responsive: true, displayModeBar: true }}
          style={{ width: '100%', height: '100%' }}
          useResizeHandler
          onClick={handlePlotClick}
        />
      </div>
    </div>
  )
}
