import { useMemo } from 'react'
import Plot from 'react-plotly.js'

// ── Composant interne pour le Rapport de Performance ──
function PerformanceReport({ goldKpis, silverReport }) {
  if (!goldKpis) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', minHeight: '300px', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
       Chargement des rapports Medallion...
    </div>
  )

  // Destructuration sécurisée
  const { 
    dwell_analytics = {}, 
    advanced_analytics = {}, 
    type_distribution = {}, 
    size_distribution = {}, 
    weight_stats = {} 
  } = goldKpis

  return (
    <div style={{ padding: '15px', color: '#fff', fontSize: '0.85rem', display: 'flex', flexDirection: 'column', gap: '25px' }}>
      
      {/* 0. Audit de Qualité (Silver Layer) */}
      {silverReport && (
        <section style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <div style={{ color: '#a8b2c0', fontWeight: 800, fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '1px' }}>
              🧹 AUDIT DE QUALITÉ (SILVER LAYER)
            </div>
            <div style={{ fontSize: '0.75rem', fontWeight: 900, color: '#a8b2c0' }}>
              SCORE : {silverReport.quality_score || 0}%
            </div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '10px' }}>
            {[
              { label: 'BRUTES', value: silverReport.total_raw || 0, color: '#fff' },
              { label: 'DOUBLONS', value: silverReport.duplicates_removed || 0, color: '#f85149' },
              { label: 'VAL. NULLES', value: silverReport.invalid_nulls_removed || 0, color: '#f85149' },
              { label: 'HORS DOMAINE', value: silverReport.invalid_domain_removed || 0, color: '#f85149' },
              { label: 'VALIDÉES', value: silverReport.total_cleaned || 0, color: '#3fb950' }
            ].map(s => (
              <div key={s.label} style={{ background: 'rgba(255,255,255,0.02)', padding: '8px', borderRadius: '4px', textAlign: 'center' }}>
                <div style={{ fontSize: '0.5rem', color: 'var(--text-muted)', fontWeight: 800, whiteSpace: 'nowrap' }}>{s.label}</div>
                <div style={{ fontSize: '0.9rem', fontWeight: 900, color: s.color }}>{s.value}</div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* 1. Distributions (Type & Taille) */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '20px' }}>
        <section>
          <div style={{ color: '#d4a017', fontWeight: 800, fontSize: '0.7rem', marginBottom: '10px', textTransform: 'uppercase', letterSpacing: '1px' }}>
            📦 DISTRIBUTION PAR TYPE
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {Object.entries(type_distribution || {}).map(([type, info]) => (
              <div key={type} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 10px', background: 'rgba(255,255,255,0.02)', borderRadius: '4px' }}>
                <span style={{ fontWeight: 700, textTransform: 'uppercase' }}>{type}</span>
                <span style={{ color: 'var(--text-secondary)' }}>{info.count} <small>({info.percentage}%)</small></span>
              </div>
            ))}
          </div>
        </section>

        <section>
          <div style={{ color: '#d4a017', fontWeight: 800, fontSize: '0.7rem', marginBottom: '10px', textTransform: 'uppercase', letterSpacing: '1px' }}>
            📏 PAR TAILLE
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {Object.entries(size_distribution || {}).map(([size, info]) => (
              <div key={size} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 10px', background: 'rgba(255,255,255,0.02)', borderRadius: '4px' }}>
                <span style={{ fontWeight: 700 }}>{size}</span>
                <span style={{ color: 'var(--text-secondary)' }}>{info.count} <small>({info.percentage}%)</small></span>
              </div>
            ))}
          </div>
        </section>
      </div>

      {/* 2. Statistiques Poids */}
      <section>
        <div style={{ color: '#d4a017', fontWeight: 800, fontSize: '0.7rem', marginBottom: '10px', textTransform: 'uppercase', letterSpacing: '1px' }}>
          ⚖️ STATISTIQUES POIDS (TONNES)
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '10px' }}>
          {[
            { label: 'MOYENNE', value: weight_stats?.avg_t, unit: 't' },
            { label: 'ÉCART-TYPE', value: weight_stats?.stddev_t, unit: 't' },
            { label: 'MINIMUM', value: weight_stats?.min_t, unit: 't' },
            { label: 'MAXIMUM', value: weight_stats?.max_t, unit: 't' }
          ].map(s => (
            <div key={s.label} style={{ background: 'rgba(255,255,255,0.03)', padding: '8px 12px', borderRadius: '6px', textAlign: 'center' }}>
              <div style={{ fontSize: '0.55rem', color: 'var(--text-muted)', fontWeight: 800 }}>{s.label}</div>
              <div style={{ fontSize: '1rem', fontWeight: 900, color: '#fff' }}>{s.value}{s.unit}</div>
            </div>
          ))}
        </div>
      </section>

      {/* 3. Section Dwell Time */}
      <section>
        <div style={{ color: '#d4a017', fontWeight: 800, fontSize: '0.7rem', marginBottom: '10px', textTransform: 'uppercase', letterSpacing: '1px' }}>
          ⏱️ TEMPS DE SÉJOUR MOYEN
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '10px' }}>
          {Object.entries(dwell_analytics || {}).map(([type, days]) => (
            <div key={type} style={{ background: 'rgba(255,255,255,0.03)', padding: '10px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)' }}>
              <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)', fontWeight: 800, marginBottom: '4px' }}>{type.toUpperCase()}</div>
              <div style={{ fontSize: '1.1rem', fontWeight: 900 }}>{days} <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>jours</span></div>
            </div>
          ))}
        </div>
      </section>

      {/* 4. Section Efficacité de Gerbage */}
      <section>
        <div style={{ color: '#d4a017', fontWeight: 800, fontSize: '0.7rem', marginBottom: '10px', textTransform: 'uppercase', letterSpacing: '1px' }}>
          🏗️ AUDIT DE GERBAGE (STACKING)
        </div>
        <div style={{ display: 'flex', gap: '15px' }}>
          <div style={{ flex: 1, background: 'rgba(255,255,255,0.03)', padding: '12px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)' }}>
             <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)', fontWeight: 800, marginBottom: '6px' }}>SCORE D'EFFICACITÉ</div>
             <div style={{ fontSize: '1.4rem', fontWeight: 900, color: (advanced_analytics?.efficiency_score || 0) > 90 ? '#3fb950' : '#d29922' }}>
                {advanced_analytics?.efficiency_score || 100}%
             </div>
             <div style={{ width: '100%', height: '4px', background: 'rgba(255,255,255,0.1)', borderRadius: '2px', marginTop: '8px' }}>
                <div style={{ width: `${advanced_analytics?.efficiency_score || 100}%`, height: '100%', background: (advanced_analytics?.efficiency_score || 0) > 90 ? '#3fb950' : '#d29922', borderRadius: '2px' }} />
             </div>
          </div>
          <div style={{ flex: 1, background: 'rgba(255,255,255,0.03)', padding: '12px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)' }}>
             <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)', fontWeight: 800, marginBottom: '6px' }}>RISQUES DE REHANDLE</div>
             <div style={{ fontSize: '1.4rem', fontWeight: 900, color: (advanced_analytics?.rehandle_risk_count || 0) > 0 ? '#f85149' : '#3fb950' }}>
                {advanced_analytics?.rehandle_risk_count || 0}
             </div>
             <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginTop: '4px' }}>Unités bloquées détectées</div>
          </div>
        </div>
      </section>

    </div>
  )
}

export default function AnalyticsView({ yardData, goldKpis, silverReport }) {
  // ── KPI 1 : Occupancy Bar Chart (Existing) ────────────────────────────────
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

  // ── KPI 2 : Heatmap d'Efficacité (Operational Risk) ────────────────────────
  const heatmapData = useMemo(() => {
    const blocks = yardData.blocks
    const risks = goldKpis?.advanced_analytics?.details_per_block || {}
    
    // On crée une matrice basée sur les blocs réels
    // Pour une visualisation heatmap, on peut faire une grille (ex: 2 colonnes)
    const z = []
    const xLabels = ['Cols 1-2', 'Cols 3-4']
    const yLabels = ['Rangées A-B', 'Rangées C-D']
    
    // On mappe les risques des blocs (A, B, C, D...) sur la grille
    const getRisk = (id) => risks[id] || 0
    
    z.push([getRisk('A'), getRisk('B')])
    z.push([getRisk('C'), getRisk('D')])

    return [{
      z: z,
      x: xLabels,
      y: yLabels,
      type: 'heatmap',
      colorscale: [
        [0, '#1a1f2e'],    // Fond sombre
        [0.1, '#3fb950'],  // Vert (Peu de risques)
        [0.5, '#d29922'],  // Orange
        [1, '#f85149']     // Rouge (Haute alerte)
      ],
      showscale: true,
      hovertemplate: 'Zone %{y}, %{x}<br>Risques détectés: %{z}<extra></extra>',
    }]
  }, [yardData, goldKpis])

  // ── KPI 3 : Temps de Séjour Moyen (Dwell Time) ──────────────────────────────
  const dwellTimeData = useMemo(() => {
    if (!goldKpis?.dwell_analytics) {
      return [{ x: ['Data Pending'], y: [0], type: 'bar', marker: { color: '#333' } }]
    }

    const labels = Object.keys(goldKpis.dwell_analytics).map(l => l.toUpperCase())
    const values = Object.values(goldKpis.dwell_analytics)

    return [{
      x: labels,
      y: values,
      type: 'bar',
      marker: {
        color: 'var(--accent-cyan)',
        opacity: 0.8
      },
      hovertemplate: '<b>%{x}</b><br>Séjour moy: %{y} jours<extra></extra>',
    }]
  }, [goldKpis])

  // ── KPI 4 : Pie chart - container type distribution ────────────────────────
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

    if (!labels.length) return [{ type: 'pie', labels: ['Aucun'], values: [1], marker: { colors: ['#333'] } }]

    return [{
      type: 'pie',
      labels,
      values,
      hole: 0.5,
      marker: { colors: ['#58a6ff', '#3fb950', '#d29922', '#f85149', '#8b949e'] },
      textinfo: 'label+percent',
      textfont: { color: '#fff', size: 10 },
      hovertemplate: '<b>%{label}</b><br>%{value} unités<extra></extra>',
    }]
  }, [yardData])

  // ── Layouts ────────────────────────────────────────────────────────────────
  const commonLayout = {
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(255,255,255,0.02)',
    font: { color: '#8B949E', family: 'Inter, sans-serif' },
    margin: { t: 30, b: 40, l: 40, r: 20 },
    xaxis: { color: '#8B949E', gridcolor: 'rgba(255,255,255,0.05)' },
    yaxis: { color: '#8B949E', gridcolor: 'rgba(255,255,255,0.05)' }
  }

  const plotConfig = { responsive: true, displayModeBar: false }

  return (
    <div style={{ 
      flex: 1, 
      display: 'grid', 
      gridTemplateColumns: '1fr 1fr', 
      gridTemplateRows: '1fr 1fr', 
      gap: '20px', 
      padding: '10px 0',
      minHeight: 0 
    }}>
      {/* CASE 1: Occupancy Bar Chart */}
      <div className="analytics-panel glass">
        <div className="analytics-panel-title">📊 TAUX D'OCCUPATION PAR BLOC</div>
        <div className="chart-inner" style={{ flex: 1, minHeight: 0 }}>
          <Plot data={occupancyBarData} layout={{...commonLayout, yaxis: { ...commonLayout.yaxis, ticksuffix: '%' }}} config={plotConfig} style={{ width: '100%', height: '100%' }} useResizeHandler />
        </div>
      </div>

      {/* CASE 2: Rapport Détaillé Gold (Remplacement de la Heatmap) */}
      <div className="analytics-panel glass">
        <div className="analytics-panel-title">🛡️ RAPPORT D'AUDIT OPÉRATIONNEL (DATA LAKE)</div>
        <div className="chart-inner" style={{ flex: 1, minHeight: 0, overflowY: 'auto' }}>
          <PerformanceReport goldKpis={goldKpis} silverReport={silverReport} />
        </div>
      </div>

      {/* CASE 3: Dwell Time Chart */}
      <div className="analytics-panel glass">
        <div className="analytics-panel-title">⏱️ TEMPS DE SÉJOUR MOYEN (JOURS)</div>
        <div className="chart-inner" style={{ flex: 1, minHeight: 0 }}>
          <Plot data={dwellTimeData} layout={commonLayout} config={plotConfig} style={{ width: '100%', height: '100%' }} useResizeHandler />
        </div>
      </div>

      {/* CASE 4: Mix Type Pie */}
      <div className="analytics-panel glass">
        <div className="analytics-panel-title">📦 RÉPARTITION DU MIX PRODUIT</div>
        <div className="chart-inner" style={{ flex: 1, minHeight: 0 }}>
          <Plot data={pieData} layout={{...commonLayout, showlegend: false, margin: {t:10, b:10, l:10, r:10}}} config={plotConfig} style={{ width: '100%', height: '100%' }} useResizeHandler />
        </div>
      </div>
    </div>
  )
}
