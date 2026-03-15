import React from 'react'

export default function ContainerInfoDrawer({ container, onClose }) {
  if (!container) return null

  return (
    <div className={`container-drawer ${container ? 'open' : ''}`}>
      <div className="drawer-header">
        <div>
          <span style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '2px', fontWeight: 600 }}>Détails de l'unité</span>
          <h3 style={{ marginTop: '4px', fontSize: '1.4rem' }}>Logistics Intelligence</h3>
        </div>
        <button className="btn-close" onClick={onClose}>&times;</button>
      </div>
      
      <div className="drawer-content">
        <div className="info-group main-info">
          <label style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', letterSpacing: '1px' }}>ID DU CONTENEUR</label>
          <div className="info-value highlight" style={{ color: 'var(--accent-cyan)', background: 'rgba(0, 253, 255, 0.04)', border: '1px solid var(--border-cyan)', padding: '15px', borderRadius: '12px', fontSize: '1.8rem', marginTop: '10px' }}>
            {container.id}
          </div>
        </div>

        <div className="drawer-divider" style={{ height: '1px', background: 'var(--border)', margin: '30px 0' }} />

        <div className="info-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '30px' }}>
          <div className="info-group">
            <label>TYPE OPÉRATIONNEL</label>
            <div className="info-value" style={{ 
              color: container.type === 'export' ? '#58a6ff' : 'var(--accent-green)',
              fontSize: '1.2rem',
              fontWeight: 700
            }}>
              {container.type === 'export' ? 'Export' : container.type}
            </div>
          </div>
          <div className="info-group">
            <label>TAILLE STANDARD</label>
            <div className="info-value" style={{ fontSize: '1.1rem', fontWeight: 600 }}>{container.size} ft (EVP)</div>
          </div>
          <div className="info-group">
            <label>POIDS BRUT</label>
            <div className="info-value" style={{ color: '#f85149', fontSize: '1.2rem', fontWeight: 600 }}>
              {container.weight} tonnes
            </div>
          </div>
          <div className="info-group">
            <label>HEURE DE DÉPART</label>
            <div className="info-value" style={{ fontSize: '1.1rem', fontWeight: 600 }}>{container.departure_time}</div>
          </div>
        </div>

        <div className="location-info" style={{ marginTop: '60px', padding: '30px', background: 'rgba(255,255,255,0.03)', borderRadius: '20px', border: '1px solid var(--border-strong)' }}>
          <label style={{ color: 'var(--accent-cyan)', fontSize: '0.75rem', textTransform: 'none', fontWeight: 500 }}>Position dans le Yard</label>
          <div className="info-value" style={{ fontSize: '2rem', fontWeight: 800, marginTop: '12px', letterSpacing: '1px', color: '#fff' }}>
            {container.location?.replace(/-/g, ' • ')}
          </div>
        </div>
      </div>
    </div>
  )
}
