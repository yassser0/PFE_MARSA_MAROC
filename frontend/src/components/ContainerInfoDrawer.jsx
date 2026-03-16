import React from 'react'

export default function ContainerInfoDrawer({ container, onClose }) {
  if (!container) return null

  const isUrgent = container.weight > 25
  const statusColor = isUrgent ? 'var(--accent-red)' : 'var(--accent-cyan)'

  return (
    <div className={`container-drawer ${container ? 'open' : ''}`} style={{
      background: 'rgba(8, 10, 12, 0.8)',
      backdropFilter: 'blur(30px)',
      boxShadow: '-20px 0 60px rgba(0,0,0,0.8)',
      borderLeft: '1px solid rgba(255,255,255,0.05)',
      display: 'flex',
      flexDirection: 'column',
      position: 'fixed',
      top: 0,
      right: container ? 0 : '-420px',
      width: '420px',
      height: '100vh',
      zIndex: 2000,
      transition: 'right 0.6s cubic-bezier(0.16, 1, 0.3, 1)',
      overflow: 'hidden'
    }}>
      {/* Accent Line on the left */}
      <div style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '4px',
        height: '100%',
        background: statusColor,
        boxShadow: `0 0 20px ${statusColor}44`,
        zIndex: 5
      }} />

      {/* Background Scanning Effect Overlay */}
      <div className="scanning-line" style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '2px',
        background: `linear-gradient(to right, transparent, ${statusColor}22, transparent)`,
        opacity: 0.3,
        pointerEvents: 'none'
      }} />

      <div className="drawer-header" style={{
        padding: '40px 30px 20px',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-start'
      }}>
        <div>
          <span style={{ 
            fontSize: '0.7rem', 
            color: 'var(--text-secondary)', 
            textTransform: 'uppercase', 
            letterSpacing: '3px', 
            fontWeight: 800,
            display: 'block',
            marginBottom: '6px'
          }}>
            Unit Intelligence
          </span>
          <h3 style={{ 
            margin: 0, 
            fontSize: '1.6rem', 
            fontWeight: 800, 
            color: '#fff',
            letterSpacing: '-0.5px'
          }}>
            Marsa Logistics <span style={{ color: statusColor }}>•</span>
          </h3>
        </div>
        <button 
          className="btn-close" 
          onClick={onClose}
          style={{
            background: 'rgba(255,255,255,0.03)',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: '50%',
            width: '40px',
            height: '40px',
            color: '#fff',
            cursor: 'pointer',
            fontSize: '1.4rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'all 0.3s'
          }}
        >
          &times;
        </button>
      </div>

      <div className="drawer-content" style={{ padding: '40px 30px', flex: 1, overflowY: 'auto' }}>
        {/* Main ID Section */}
        <div style={{ marginBottom: '40px' }}>
          <label style={{ 
            fontSize: '0.65rem', 
            color: 'var(--text-secondary)', 
            fontWeight: 700, 
            textTransform: 'uppercase', 
            letterSpacing: '1.5px',
            marginBottom: '12px',
            display: 'block'
          }}>
            Container Identifier
          </label>
          <div style={{ 
            background: 'rgba(255,255,255,0.02)',
            border: `1px solid ${statusColor}33`,
            borderRadius: '16px',
            padding: '24px',
            fontSize: '2.4rem',
            fontWeight: 900,
            color: '#fff',
            fontFamily: 'monospace',
            textAlign: 'center',
            boxShadow: `inset 0 0 30px ${statusColor}08`,
            position: 'relative',
            overflow: 'hidden'
          }}>
            {container.id}
            <div style={{
              position: 'absolute',
              bottom: 0,
              left: 0,
              width: '100%',
              height: '4px',
              background: statusColor,
              opacity: 0.5
            }} />
          </div>
        </div>

        {/* Detailed Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '30px' }}>
          {/* Status/Type */}
          <div className="info-group">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--text-secondary)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path>
              </svg>
              <span style={{ fontSize: '0.65rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Classification</span>
            </div>
            <div style={{ 
              fontSize: '1.1rem', 
              fontWeight: 700, 
              color: statusColor,
              textTransform: 'capitalize'
            }}>
              {container.type || 'Standard'}
            </div>
          </div>

          {/* Size */}
          <div className="info-group">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--text-secondary)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect>
                <line x1="16" y1="21" x2="16" y2="7"></line>
                <line x1="8" y1="21" x2="8" y2="7"></line>
              </svg>
              <span style={{ fontSize: '0.65rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Dimensions</span>
            </div>
            <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#fff' }}>
              {container.size} ft <span style={{ fontSize: '0.8rem', opacity: 0.5 }}>(EVP)</span>
            </div>
          </div>

          {/* Weight */}
          <div className="info-group">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={statusColor} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M7 20l4-16m2 16l4-16M6 9h14M4 15h14"></path>
              </svg>
              <span style={{ fontSize: '0.65rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Gross Weight</span>
            </div>
            <div style={{ fontSize: '1.4rem', fontWeight: 800, color: statusColor }}>
              {container.weight} <span style={{ fontSize: '0.9rem', opacity: 0.8 }}>tonnes</span>
            </div>
          </div>

          {/* Departure */}
          <div className="info-group">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--text-secondary)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10"></circle>
                <polyline points="12 6 12 12 16 14"></polyline>
              </svg>
              <span style={{ fontSize: '0.65rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Departure</span>
            </div>
            <div style={{ fontSize: '1rem', fontWeight: 600, color: '#fff', fontFamily: 'monospace' }}>
              {container.departure_time?.split(' ')[0]}
              <span style={{ display: 'block', fontSize: '0.85rem', opacity: 0.5 }}>{container.departure_time?.split(' ')[1]}</span>
            </div>
          </div>
        </div>

        {/* Location High-Tech Panel */}
        <div style={{ 
          marginTop: '60px', 
          padding: '24px', 
          background: 'linear-gradient(135deg, rgba(0, 253, 255, 0.03) 0%, transparent 100%)', 
          borderRadius: '20px', 
          border: '1px solid rgba(255,255,255,0.06)',
          position: 'relative'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--accent-cyan)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
              <circle cx="12" cy="10" r="3"></circle>
            </svg>
            <span style={{ fontSize: '0.7rem', color: 'var(--accent-cyan)', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '1px' }}>
              Geospatial Location
            </span>
          </div>
          
          <div style={{ 
            fontSize: '1.8rem', 
            fontWeight: 900, 
            letterSpacing: '2px', 
            color: '#fff',
            display: 'inline-block',
            padding: '4px 12px',
            background: '#003db3', // Blue background from image 2
            borderRadius: '4px',
            marginBottom: '16px'
          }}>
            {container.location || 'YARD • UNK'}
          </div>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <span style={{ fontSize: '0.6rem', color: 'var(--text-secondary)', fontWeight: 700, textTransform: 'uppercase' }}>Structure</span>
            <div style={{ display: 'flex', gap: '6px' }}>
              <span style={{ padding: '4px 8px', background: 'rgba(255,255,255,0.04)', borderRadius: '4px', fontSize: '0.7rem', color: '#fff', fontWeight: 700, border: '1px solid rgba(255,255,255,0.1)' }}>
                [BLOC]
              </span>
              <span style={{ padding: '4px 8px', background: 'rgba(255,255,255,0.04)', borderRadius: '4px', fontSize: '0.7rem', color: '#fff', fontWeight: 700, border: '1px solid rgba(255,255,255,0.1)' }}>
                [TRAVÉE]
              </span>
              <span style={{ padding: '4px 8px', background: 'rgba(255,255,255,0.04)', borderRadius: '4px', fontSize: '0.7rem', color: '#fff', fontWeight: 700, border: '1px solid rgba(255,255,255,0.1)' }}>
                [CELLULE]
              </span>
              <span style={{ padding: '4px 8px', background: 'rgba(255,255,255,0.04)', borderRadius: '4px', fontSize: '0.7rem', color: '#fff', fontWeight: 700, border: '1px solid rgba(255,255,255,0.1)' }}>
                [NIVEAU]
              </span>
            </div>
          </div>
        </div>
      </div>
      
      {/* Footer Branding */}
      <div style={{ padding: '24px 30px', borderTop: '1px solid rgba(255,255,255,0.06)', background: 'rgba(0,0,0,0.2)', textAlign: 'center' }}>
         <span style={{ fontSize: '0.6rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '4px' }}>Marsa Maroc Digital Twin System</span>
      </div>
    </div>
  )
}
