import React from 'react';

export default function KpiHeader({ data }) {
  if (!data) return null;
  const cards = [
    { label: 'Occupation Globale', value: `${(data.occupancy_rate * 100).toFixed(1)}%`, icon: '📊' },
    { label: 'Slots Occupés', value: data.used_slots, icon: '📦' },
    { label: 'Capacité Totale', value: data.total_capacity, icon: '🏗️' },
    { label: 'Hauteur Moyenne', value: data.average_stack_height?.toFixed(1), icon: '📐' },
  ];

  return (
    <div className="kpi-header">
      {cards.map((c) => (
        <div className="kpi-card" key={c.label}>
          <span className="kpi-icon">{c.icon}</span>
          <div className="kpi-title">{c.label}</div>
          <div className="kpi-value">{c.value}</div>
        </div>
      ))}
    </div>
  );
}
