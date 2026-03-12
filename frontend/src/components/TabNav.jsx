import React from 'react';

const TABS = ['Vue Globale 3D', 'Vue Détail Bloc', 'Heatmap & Analytique'];

export default function TabNav({ active, onChange }) {
  return (
    <div className="tab-nav">
      {TABS.map((tab) => (
        <button
          key={tab}
          className={`tab-btn ${active === tab ? 'active' : ''}`}
          onClick={() => onChange(tab)}
        >
          {tab === 'Vue Globale 3D' && '🌐 '}
          {tab === 'Vue Détail Bloc' && '🔍 '}
          {tab === 'Heatmap & Analytique' && '📊 '}
          {tab}
        </button>
      ))}
    </div>
  );
}
