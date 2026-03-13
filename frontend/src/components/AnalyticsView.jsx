import { useMemo } from 'react'
import Plot from 'react-plotly.js'

export default function AnalyticsView({ yardData }) {
  // Optimization Alerts Logic
  const alerts = useMemo(() => {
    const list = []
    yardData.blocks.forEach(b => {
      if (b.occupancy > 0.8) {
        list.push({ type: 'danger', message: `BLOC ${b.block_id}: Densité critique (${Math.round(b.occupancy * 100)}%). Risque de congestion élevé.` })
      } else if (b.occupancy > 0.6) {
        list.push({ type: 'warning', message: `BLOC ${b.block_id}: Volume important. Envisager un rééquilibrage vers zones moins denses.` })
      }
    })
    
    // Check for height consistency (optimization alert)
    const unevenStacks = yardData.blocks.some(b => {
      const heights = b.stacks.map(s => s.slots.filter(sl => !sl.is_free).length)
      const max = Math.max(...heights)
      const min = Math.min(...heights)
      return (max - min) > 3
    })
    
    if (unevenStacks) {
      list.push({ type: 'info', message: "OPTI: Piles hétérogènes détectées. Un lissage des hauteurs améliorerait la productivité RTG." })
    }

    return list
  }, [yardData])

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
      {/* Optimization Alerts */}
      <div className="analytics-panel glass" style={{ gridRow: 'span 2', display: 'flex', flexDirection: 'column' }}>
        <div className="analytics-panel-title">⚠️ ALERTES D'OPTIMISATION & TOS</div>
        <div style={{ flex: 1, overflowY: 'auto', padding: '10px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {alerts.length === 0 ? (
            <div style={{ padding: '20px', textAlign: 'center', color: 'var(--accent-green)', opacity: 0.6 }}>
               Tous les indicateurs sont au vert. Yard optimisé.
            </div>
          ) : (
            alerts.map((alert, i) => (
              <div key={i} className={`alert-item ${alert.type}`} style={{
                padding: '12px 15px',
                borderRadius: '8px',
                fontSize: '0.8rem',
                borderLeft: `4px solid ${alert.type === 'danger' ? 'var(--accent-red)' : alert.type === 'warning' ? 'var(--accent-orange)' : 'var(--accent-blue)'}`,
                background: 'rgba(255,255,255,0.03)'
              }}>
                {alert.message}
              </div>
            ))
          )}
        </div>
        <div className="analytics-panel-footer" style={{ padding: '15px', borderTop: '1px solid var(--border)', fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
          Mise à jour temps réel via Engine TOS v2.1
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
