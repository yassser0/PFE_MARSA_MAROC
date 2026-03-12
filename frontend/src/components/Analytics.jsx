import React from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell, ResponsiveContainer, LabelList
} from 'recharts';

function getColor(value) {
  if (value >= 80) return '#d62728';
  if (value >= 50) return '#ff7f0e';
  return '#2ca02c';
}

const CustomTooltip = ({ active, payload }) => {
  if (active && payload?.length) {
    const val = payload[0].value;
    return (
      <div className="chart-tooltip">
        <p>{payload[0].payload.name}</p>
        <p style={{ color: getColor(val), fontWeight: 700 }}>{val.toFixed(1)}%</p>
      </div>
    );
  }
  return null;
};

export default function Analytics({ yardData }) {
  if (!yardData) return null;

  const data = yardData.blocks.map((b) => ({
    name: `Bloc ${b.block_id}`,
    value: parseFloat((b.occupancy * 100).toFixed(1)),
  }));

  const total = yardData.blocks.length;
  const high = data.filter((d) => d.value >= 80).length;
  const medium = data.filter((d) => d.value >= 50 && d.value < 80).length;
  const low = data.filter((d) => d.value < 50).length;

  return (
    <div className="analytics-panel">
      <h3>📊 Distribution de la Charge par Bloc</h3>

      <div className="analytics-legend">
        <span className="legend-item" style={{ color: '#2ca02c' }}>● Faible (&lt;50%) — {low}</span>
        <span className="legend-item" style={{ color: '#ff7f0e' }}>● Modéré (50-80%) — {medium}</span>
        <span className="legend-item" style={{ color: '#d62728' }}>● Élevé (≥80%) — {high}</span>
      </div>

      <ResponsiveContainer width="100%" height={340}>
        <BarChart data={data} margin={{ top: 20, right: 30, left: 0, bottom: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e2a1e" />
          <XAxis dataKey="name" stroke="#8b949e" tick={{ fill: '#c9d1d9' }} />
          <YAxis domain={[0, 100]} stroke="#8b949e" tick={{ fill: '#c9d1d9' }} unit="%" />
          <Tooltip content={<CustomTooltip />} />
          <Bar dataKey="value" radius={[4, 4, 0, 0]}>
            {data.map((entry, index) => (
              <Cell key={index} fill={getColor(entry.value)} />
            ))}
            <LabelList dataKey="value" position="top" formatter={(v) => `${v}%`} style={{ fill: '#c9d1d9', fontSize: 12 }} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      <div className="analytics-table">
        <table>
          <thead>
            <tr>
              <th>Bloc</th>
              <th>Taux d'Occupation</th>
              <th>Statut</th>
            </tr>
          </thead>
          <tbody>
            {data.map((row) => (
              <tr key={row.name}>
                <td>{row.name}</td>
                <td>
                  <div className="progress-bar-wrap">
                    <div
                      className="progress-bar-fill"
                      style={{ width: `${row.value}%`, background: getColor(row.value) }}
                    />
                    <span>{row.value}%</span>
                  </div>
                </td>
                <td>
                  <span className="badge" style={{ background: getColor(row.value) + '33', color: getColor(row.value) }}>
                    {row.value >= 80 ? 'Critique' : row.value >= 50 ? 'Modéré' : 'Normal'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
