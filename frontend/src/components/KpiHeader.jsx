export default function KpiHeader({ data }) {
  const occupancy = (data.occupancy_rate * 100).toFixed(1)
  const avgHeight = data.average_stack_height.toFixed(2)

  const kpis = [
    {
      title: 'Occupation Globale',
      value: `${occupancy}%`,
      bar: true,
      barWidth: data.occupancy_rate,
    },
    {
      title: 'Slots Occupés',
      value: data.used_slots.toLocaleString('fr-FR'),
    },
    {
      title: 'Capacité Totale',
      value: data.total_capacity.toLocaleString('fr-FR'),
    },
    {
      title: 'Hauteur Moyenne',
      value: avgHeight,
      bar: true,
      barWidth: data.average_stack_height / data.max_height,
    },
  ]

  return (
    <div className="kpi-grid">
      {kpis.map((k) => (
        <div className="kpi-card" key={k.title}>
          <div className="kpi-title">{k.title}</div>
          <div className="kpi-value">{k.value}</div>
          {k.bar && (
            <div className="kpi-bar">
              <div className="kpi-bar-fill" style={{ width: `${Math.min(k.barWidth * 100, 100)}%` }} />
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
