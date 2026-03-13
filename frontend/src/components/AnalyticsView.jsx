import { useMemo } from 'react'
import Plot from 'react-plotly.js'

export default function AnalyticsView({ yardData }) {
  // Bar chart - occupancy per block
  const barData = useMemo(() => {
    const blocks = yardData.blocks
    const values = blocks.map(b => +(b.occupancy * 100).toFixed(1))
    const colorscale = values.map(v => {
      if (v < 40) return '#2ca02c'
      if (v < 70) return '#ffbf00'
      return '#d62728'
    })

    return [{
      type: 'bar',
      x: blocks.map(b => `Bloc ${b.block_id}`),
      y: values,
      marker: { color: colorscale },
      text: values.map(v => `${v}%`),
      textposition: 'outside',
      hovertemplate: '<b>%{x}</b><br>Occupation: %{y}%<extra></extra>',
    }]
  }, [yardData])

  const barLayout = useMemo(() => ({
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    margin: { t: 20, b: 60, l: 40, r: 20 },
    yaxis: {
      title: "Taux d'Occupation (%)",
      range: [0, 110],
      gridcolor: '#333',
      color: '#8B949E',
    },
    xaxis: { color: '#8B949E' },
    font: { color: '#8B949E', family: 'Inter, sans-serif', size: 11 },
    bargap: 0.3,
  }), [])

  // Stacked bar - total stacks per block by height level
  const stackedData = useMemo(() => {
    const blocks = yardData.blocks
    const maxH = yardData.max_height
    const series = []

    for (let tier = 1; tier <= maxH; tier++) {
      const counts = blocks.map(b => {
        return b.stacks.reduce((acc, stack) => {
          const slot = (stack.slots || []).find(s => s.tier === tier && !s.is_free)
          return acc + (slot ? 1 : 0)
        }, 0)
      })
      series.push({
        type: 'bar',
        name: `Tier ${tier}`,
        x: blocks.map(b => `Bloc ${b.block_id}`),
        y: counts,
        hovertemplate: `<b>%{x}</b> - Tier ${tier}<br>Conteneurs: %{y}<extra></extra>`,
      })
    }
    return series
  }, [yardData])

  const stackedLayout = useMemo(() => ({
    barmode: 'stack',
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    margin: { t: 20, b: 60, l: 40, r: 20 },
    yaxis: { title: 'Nombre de Conteneurs', gridcolor: '#333', color: '#8B949E' },
    xaxis: { color: '#8B949E' },
    legend: { bgcolor: 'rgba(0,0,0,0)', font: { color: '#8B949E' } },
    font: { color: '#8B949E', family: 'Inter, sans-serif', size: 11 },
    colorway: ['#2ca02c', '#4a9eff', '#ff7f0e', '#9467bd', '#8c564b'],
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

    const labels = Object.keys(typeCounts)
    const values = Object.values(typeCounts)

    if (!labels.length) return [{ type: 'pie', labels: ['Aucun conteneur'], values: [1], marker: { colors: ['#333'] } }]

    return [{
      type: 'pie',
      labels,
      values,
      marker: { colors: ['#4a9eff', '#2ca02c', '#ff7f0e', '#d62728', '#9467bd'] },
      textinfo: 'label+percent',
      textfont: { color: '#E6EDF3', size: 11 },
      hovertemplate: '<b>%{label}</b><br>%{value} conteneurs (%{percent})<extra></extra>',
    }]
  }, [yardData])

  const pieLayout = useMemo(() => ({
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    margin: { t: 10, b: 10, l: 10, r: 10 },
    showlegend: true,
    legend: { bgcolor: 'rgba(0,0,0,0)', font: { color: '#8B949E' } },
    font: { color: '#8B949E', family: 'Inter, sans-serif' },
  }), [])

  const plotConfig = { responsive: true, displayModeBar: false }

  return (
    <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '1fr 1fr', gridTemplateRows: '1fr 1fr', gap: '14px', minHeight: 0 }}>
      {/* Top Left: Occupation par bloc */}
      <div className="analytics-panel">
        <div className="analytics-panel-title">📊 Occupation par Bloc (%)</div>
        <div className="chart-inner" style={{ flex: 1, minHeight: 0 }}>
          <Plot
            data={barData}
            layout={barLayout}
            config={plotConfig}
            style={{ width: '100%', height: '100%' }}
            useResizeHandler
          />
        </div>
      </div>

      {/* Top Right: Types de conteneurs */}
      <div className="analytics-panel">
        <div className="analytics-panel-title">🥧 Répartition par Type</div>
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

      {/* Bottom: Stacked by tier */}
      <div className="analytics-panel" style={{ gridColumn: '1 / -1' }}>
        <div className="analytics-panel-title">📦 Distribution par Niveau (Tier) par Bloc</div>
        <div className="chart-inner" style={{ flex: 1, minHeight: 0 }}>
          <Plot
            data={stackedData}
            layout={stackedLayout}
            config={plotConfig}
            style={{ width: '100%', height: '100%' }}
            useResizeHandler
          />
        </div>
      </div>
    </div>
  )
}
