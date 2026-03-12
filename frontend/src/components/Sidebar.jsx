import React, { useState } from 'react';
import { initYard } from '../api';

export default function Sidebar({ onRefresh, lastUpdate, searchQuery, onSearchChange, onBlockSelect }) {
  const [blocks, setBlocks] = useState(4);
  const [bays, setBays] = useState(10);
  const [rows, setRows] = useState(3);
  const [height, setHeight] = useState(4);
  const [msg, setMsg] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleInit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMsg(null);
    try {
      const data = await initYard({ blocks, bays, rows, max_height: height });
      setMsg({ type: 'success', text: `✅ ${data.message} (Capacité: ${data.total_capacity})` });
      onRefresh();
    } catch {
      setMsg({ type: 'error', text: '🚨 Erreur lors de l\'initialisation.' });
    } finally {
      setLoading(false);
    }
  };

  const handleClear = async () => {
    setLoading(true);
    try {
      await initYard({ blocks: 4, bays: 10, rows: 3, max_height: 4 });
      setMsg({ type: 'success', text: '✅ Yard vidé avec succès.' });
      onRefresh();
    } catch {
      setMsg({ type: 'error', text: '🚨 Impossible de se connecter à l\'API.' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <span className="logo-icon">⚓</span>
        <span className="logo-text">Marsa Maroc</span>
      </div>

      <div className="sidebar-section">
        <h3>Configuration du Yard</h3>
        <form onSubmit={handleInit} className="config-form">
          {[
            { label: 'Blocs', value: blocks, set: setBlocks, min: 1, max: 20 },
            { label: 'Bays / bloc', value: bays, set: setBays, min: 1, max: 50 },
            { label: 'Rangées / bloc', value: rows, set: setRows, min: 1, max: 50 },
            { label: 'Hauteur max', value: height, set: setHeight, min: 1, max: 8 },
          ].map(({ label, value, set, min, max }) => (
            <div className="form-row" key={label}>
              <label>{label}</label>
              <input
                type="number"
                min={min}
                max={max}
                value={value}
                onChange={(e) => set(parseInt(e.target.value, 10))}
              />
            </div>
          ))}
          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? 'Initialisation…' : '🔄 Initialiser le Yard'}
          </button>
        </form>

        <button className="btn btn-danger" onClick={handleClear} disabled={loading}>
          🗑️ Vider le Yard &amp; Actualiser
        </button>

        {msg && (
          <div className={`sidebar-msg ${msg.type}`}>{msg.text}</div>
        )}

        <p className="last-refresh">
          Actualisation: {lastUpdate ? lastUpdate.toLocaleTimeString('fr-FR') : '—'}
        </p>
      </div>

      <div className="sidebar-section">
        <h3>🔍 Recherche de Conteneur</h3>
        <input
          type="text"
          className="search-input"
          placeholder="ID ou Localisation (ex: A-B01-R1-T1)"
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value.toUpperCase())}
        />
      </div>
    </aside>
  );
}
