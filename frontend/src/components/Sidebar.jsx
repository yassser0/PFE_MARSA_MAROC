import { useState } from 'react'
import logo from '../assets/logo.png'

export default function Sidebar({
  apiOnline, lastRefresh, onInit, onClear, onRefresh,
  searchQuery, onSearchChange
}) {
  const [blocks, setBlocks] = useState(4)
  const [bays, setBays] = useState(10)
  const [rows, setRows] = useState(3)
  const [height, setHeight] = useState(4)
  const [initLoading, setInitLoading] = useState(false)
  const [clearLoading, setClearLoading] = useState(false)
  const [feedback, setFeedback] = useState(null) // {type, message}

  const showFeedback = (type, message) => {
    setFeedback({ type, message })
    setTimeout(() => setFeedback(null), 4000)
  }

  const handleInit = async (e) => {
    e.preventDefault()
    setInitLoading(true)
    const result = await onInit({ blocks, bays, rows, max_height: height })
    setInitLoading(false)
    if (result.ok) {
      showFeedback('success', `✅ ${result.message} (Capacité: ${result.capacity})`)
    } else {
      showFeedback('error', `❌ ${result.message}`)
    }
  }

  const handleClear = async () => {
    setClearLoading(true)
    await onClear()
    setClearLoading(false)
    showFeedback('success', '🧹 Yard vidé et actualisé.')
  }

  return (
    <aside className="sidebar">
      {/* Logo */}
      <div className="sidebar-logo">
        <img src={logo} alt="Logo" style={{ height: '40px', objectFit: 'contain' }} />
        <div>
          <h2>Marsa Maroc</h2>
          <span>Yard Optimization</span>
        </div>
      </div>

      <div className="sidebar-divider" />

      {/* Configuration Form */}
      <div className="sidebar-section">
        <div className="sidebar-section-title">Configuration du Yard</div>
        <form onSubmit={handleInit} style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <div className="form-group">
            <label>Nombre de blocs</label>
            <input type="number" min={1} max={20} value={blocks} onChange={e => setBlocks(+e.target.value)} />
          </div>
          <div className="form-group">
            <label>Bays par bloc</label>
            <input type="number" min={1} max={50} value={bays} onChange={e => setBays(+e.target.value)} />
          </div>
          <div className="form-group">
            <label>Rangées par bloc</label>
            <input type="number" min={1} max={50} value={rows} onChange={e => setRows(+e.target.value)} />
          </div>
          <div className="form-group">
            <label>Hauteur maximum</label>
            <input type="number" min={1} max={8} value={height} onChange={e => setHeight(+e.target.value)} />
          </div>
          <button className="btn btn-primary" type="submit" disabled={initLoading}>
            {initLoading ? '⏳ Initialisation...' : '⚙️ Initialiser / Réinitialiser'}
          </button>
        </form>
      </div>

      {feedback && (
        <div className={`alert ${feedback.type === 'success' ? 'alert-success' : 'alert-error'}`}>
          {feedback.message}
        </div>
      )}

      {/* Actions */}
      <div className="sidebar-section">
        <button className="btn btn-danger" onClick={handleClear} disabled={clearLoading}>
          {clearLoading ? '⏳ Nettoyage...' : '🗑️ Vider le Yard & Actualiser'}
        </button>
        <button className="btn btn-secondary" onClick={onRefresh}>
          🔄 Actualiser les données
        </button>
      </div>

      <div className="sidebar-divider" />

      {/* Search */}
      <div className="sidebar-section">
        <div className="sidebar-section-title">🔍 Recherche de Conteneur</div>
        <div className="form-group">
          <label>ID ou Localisation (ex: A-B01-R1-T1)</label>
          <input
            type="text"
            value={searchQuery}
            onChange={e => onSearchChange(e.target.value.trim().toUpperCase())}
            placeholder="Rechercher..."
          />
        </div>
        {searchQuery && (
          <div className="search-result-tag">🔎 Recherche : {searchQuery}</div>
        )}
        {searchQuery && (
          <button className="btn btn-secondary" onClick={() => onSearchChange('')} style={{ padding: '5px 10px', fontSize: '0.75rem' }}>
            ✕ Effacer
          </button>
        )}
      </div>

      <div style={{ marginTop: 'auto' }}>
        <div className="sidebar-divider" style={{ marginBottom: '10px' }} />
        <div className="sidebar-time">
          <div style={{ color: apiOnline ? 'var(--accent-green)' : 'var(--accent-red)', marginBottom: '2px' }}>
            {apiOnline ? '● API en ligne' : '● API hors ligne'}
          </div>
          <div>Actualisé : {lastRefresh.toLocaleTimeString('fr-FR')}</div>
        </div>
      </div>
    </aside>
  )
}
