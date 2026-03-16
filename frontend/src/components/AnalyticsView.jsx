import { useMemo } from 'react'
import Plot from 'react-plotly.js'

export default function AnalyticsView({ yardData }) {
  // Bar Chart - Occupancy per block
  const occupancyBarData = useMemo(() => {
    const labels = yardData.blocks.map(b => `Bloc ${b.block_id}`)
    const values = yardData.blocks.map(b => b.occupancy * 100)
    const colors = values.map(v => v > 90 ? '#f85149' : v > 70 ? '#d29922' : '#3fb950')

    return [{
      x: labels,
      y: values,
      type: 'bar',
      marker: {
        color: colors,
        line: { color: 'rgba(255,255,255,0.1)', width: 1 }
      },
      hovertemplate: '<b>%{x}</b><br>Occupation: %{y:.1f}%<extra></extra>',
    }]
  }, [yardData])

  const barLayout = useMemo(() => ({
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(255,255,255,0.02)',
    margin: { t: 30, b: 40, l: 40, r: 20 },
    xaxis: {
      color: '#8B949E',
      gridcolor: 'rgba(255,255,255,0.05)',
      tickfont: { size: 10, weight: 'bold' }
    },
    yaxis: {
      color: '#8B949E',
      gridcolor: 'rgba(255,255,255,0.05)',
      range: [0, 100],
      ticksuffix: '%'
    },
    font: { color: '#8B949E', family: 'Inter, sans-serif' },
    showlegend: false
  }), [])

  // Heatmap - Block occupancy matrix
  const heatmapData = useMemo(() => {
    const blocks = yardData.blocks
    // Simulate a 2x2 grid for the heatmap visualization
    const z = [
      [blocks[0]?.occupancy * 100 || 0, blocks[1]?.occupancy * 100 || 0],
      [blocks[2]?.occupancy * 100 || 0, blocks[3]?.occupancy * 100 || 0]
    ]

    return [{
      z: z,
      x: ['Col 1', 'Col 2'],
      y: ['Rangée A', 'Rangée B'],
      type: 'heatmap',
      colorscale: [
        [0, '#111'],
        [0.4, '#3fb950'],
        [0.7, '#d29922'],
        [1, '#f85149']
      ],
      showscale: true,
      hovertemplate: 'Zone %{y}, %{x}<br>Densité: %{z}%<extra></extra>',
    }]
  }, [yardData])

  const heatmapLayout = useMemo(() => ({
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    margin: { t: 20, b: 30, l: 80, r: 10 },
    xaxis: { color: '#8B949E', side: 'top' },
    yaxis: { color: '#8B949E' },
    font: { color: '#8B949E', family: 'Inter, sans-serif' },
  }), [])

  // Pie chart - container type distribution from blocks data
  const pieData = useMemo(() => {
    const typeCounts = {}
    yardData.blocks.forEach(b => {
      b.stacks.forEach(stack => {
        (stack.slots || []).forEach(slot => {
          if (!slot.is_free && slot.container_details) {
            const type = slot.container_details.type || 'unknown'
            typeCounts[type] = (typeCounts[type] || 0) + 1
          }
        })
      })
    })

    const labels = Object.keys(typeCounts).map(l => l.toUpperCase())
    const values = Object.values(typeCounts)

    if (!labels.length) return [{ type: 'pie', labels: ['Aucun conteneur'], values: [1], marker: { colors: ['#333'] } }]

    return [{
      type: 'pie',
      labels,
      values,
      hole: 0.4,
      marker: { colors: ['#3fb950', '#58a6ff', '#d29922', '#f85149', '#8b949e'] },
      textinfo: 'label+percent',
      textfont: { color: '#fff', size: 10 },
      hovertemplate: '<b>%{label}</b><br>%{value} unités<extra></extra>',
    }]
  }, [yardData])

  const pieLayout = useMemo(() => ({
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    margin: { t: 10, b: 10, l: 10, r: 10 },
    showlegend: false,
    font: { color: '#8B949E', family: 'Inter, sans-serif' },
  }), [])

  const plotConfig = { responsive: true, displayModeBar: false }

  return (
    <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '1.2fr 1fr', gridTemplateRows: '1.2fr 1fr', gap: '20px', minHeight: 0 }}>
      {/* Occupancy Bar Chart Case */}
      <div className="analytics-panel glass" style={{ gridRow: 'span 2', display: 'flex', flexDirection: 'column' }}>
        <div className="analytics-panel-title">📊 RÉPARTITION DE LA CHARGE PAR BLOC</div>
        <div className="chart-inner" style={{ flex: 1, minHeight: 0, padding: '10px' }}>
          <Plot
            data={occupancyBarData}
            layout={barLayout}
            config={plotConfig}
            style={{ width: '100%', height: '100%' }}
            useResizeHandler
          />
        </div>
        <div className="analytics-panel-footer" style={{ padding: '15px', borderTop: '1px solid var(--border)', fontSize: '0.7rem', color: 'var(--text-secondary)' }}>

        </div>
      </div>

      {/* Heatmap */}
      <div className="analytics-panel glass">
        <div className="analytics-panel-title">🌡️ HEATMAP DE DENSITÉ PAR ZONE</div>
        <div className="chart-inner" style={{ flex: 1, minHeight: 0 }}>
          <Plot
            data={heatmapData}
            layout={heatmapLayout}
            config={plotConfig}
            style={{ width: '100%', height: '100%' }}
            useResizeHandler
          />
        </div>
      </div>

      {/* Pie chart */}
      <div className="analytics-panel glass">
        <div className="analytics-panel-title">📦 MIX PRODUIT (TYPES)</div>
        <div className="chart-inner" style={{ flex: 1, minHeight: 0 }}>
          <Plot
            data={pieData}
            layout={pieLayout}
            config={plotConfig}
            style={{ width: '100%', height: '100%' }}
            useResizeHandler
          />
        </div>
      </div>
    </div>
  )
}
