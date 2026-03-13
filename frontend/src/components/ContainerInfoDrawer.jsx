import React from 'react'

export default function ContainerInfoDrawer({ container, onClose }) {
  if (!container) return null

  return (
    <div className={`container-drawer ${container ? 'open' : ''}`}>
      <div className="drawer-header">
        <div>
          <span style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '2px', fontWeight: 600 }}>Détails de l'unité</span>
          <h3 style={{ marginTop: '4px' }}>Logistics Intelligence</h3>
        </div>
        <button className="btn-close" onClick={onClose}>&times;</button>
      </div>
      
      <div className="drawer-content">
        <div className="info-group main-info">
          <label>ID DU CONTENEUR</label>
          <div className="info-value highlight">{container.id}</div>
        </div>

        <div className="info-grid">
          <div className="info-group">
            <label>Type Opérationnel</label>
            <div className="info-value" style={{ 
              color: container.type === 'import' ? 'var(--accent-green)' : 
                     container.type === 'export' ? 'var(--accent-blue)' : 
                     'var(--accent-orange)',
              fontWeight: 600,
              textTransform: 'capitalize'
            }}>
              {container.type}
            </div>
          </div>
          <div className="info-group">
            <label>Taille Standard</label>
            <div className="info-value">{container.size} ft (EVP)</div>
          </div>
          <div className="info-group">
            <label>Poids Brut</label>
            <div className="info-value" style={{ color: container.weight > 25 ? 'var(--accent-red)' : 'var(--text-primary)' }}>
              {container.weight} tonnes
            </div>
          </div>
          <div className="info-group">
            <label>Heure de Départ</label>
            <div className="info-value" style={{ fontSize: '0.9rem' }}>{container.departure_time}</div>
          </div>
        </div>

        <div className="location-info" style={{ marginTop: '40px', padding: '24px', background: 'rgba(255,255,255,0.03)', borderRadius: '16px', border: '1px solid var(--border-strong)' }}>
          <label style={{ color: 'var(--accent-cyan)', fontSize: '0.65rem' }}>Position dans le Yard</label>
          <div className="info-value" style={{ fontSize: '1.4rem', fontWeight: 700, marginTop: '8px', letterSpacing: '1px' }}>
            {container.location?.replace(/-/g, ' • ')}
          </div>
        </div>

        <div style={{ marginTop: 'auto', paddingTop: '40px' }}>
          <button className="btn-action" onClick={onClose}>
            Terminer l'inspection
          </button>
        </div>
      </div>
    </div>
  )
}
