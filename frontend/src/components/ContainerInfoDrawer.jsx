import React from 'react'

export default function ContainerInfoDrawer({ container, onClose }) {
  if (!container) return null

  return (
    <div className={`container-drawer ${container ? 'open' : ''}`}>
      <div className="drawer-header">
        <h3>Informations Conteneur</h3>
        <button className="btn-close" onClick={onClose}>&times;</button>
      </div>
      
      <div className="drawer-content">
        <div className="info-group main-info">
          <label>ID DU CONTENEUR</label>
          <div className="info-value highlight">{container.id}</div>
        </div>

        <div className="info-grid">
          <div className="info-group">
            <label>Type</label>
            <div className="info-value">{container.type || 'N/A'}</div>
          </div>
          <div className="info-group">
            <label>Taille</label>
            <div className="info-value">{container.size || 'N/A'} ft</div>
          </div>
          <div className="info-group">
            <label>Poids</label>
            <div className="info-value">{container.weight || 'N/A'} t</div>
          </div>
          <div className="info-group">
            <label>Départ</label>
            <div className="info-value">{container.departure_time || 'N/A'}</div>
          </div>
        </div>

        <div className="info-group location-info">
          <label>Localisation Actuelle</label>
          <div className="info-value">{container.location || 'Inconnu'}</div>
        </div>

        <div className="drawer-footer">
          <button className="btn-action" onClick={onClose}>Fermer</button>
        </div>
      </div>
    </div>
  )
}
