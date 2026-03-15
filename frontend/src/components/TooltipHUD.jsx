import React from 'react'

/**
 * TooltipHUD - A shared floating tooltip component with edge detection.
 * @param {Object} data - The container detail data.
 * @param {Object} mousePos - {x, y} coordinates of the mouse.
 */
export default function TooltipHUD({ data, mousePos }) {
  if (!data || !mousePos) return null
  
  const isUrgent = data.weight > 25
  const statusColor = isUrgent ? 'var(--accent-red)' : 'var(--accent-cyan)'

  // Smart positioning to keep tooltip on screen
  const tooltipWidth = 280
  const tooltipHeight = 280 // Conservative estimate
  
  const viewportWidth = typeof window !== 'undefined' ? window.innerWidth : 1920
  const viewportHeight = typeof window !== 'undefined' ? window.innerHeight : 1080

  // Flip horizontally if overflow right
  const x = mousePos.x + tooltipWidth + 40 > viewportWidth 
    ? mousePos.x - tooltipWidth - 20 
    : mousePos.x + 20

  // Flip vertically if overflow bottom
  const y = mousePos.y + tooltipHeight + 40 > viewportHeight 
    ? mousePos.y - tooltipHeight - 20 
    : mousePos.y + 20

  return (
    <div className="floating-tooltip-container" style={{
      position: 'fixed',
      left: 0,
      top: 0,
      transform: `translate(${x}px, ${y}px)`,
      zIndex: 2000,
      width: '280px',
      pointerEvents: 'none',
      transition: 'transform 0.1s ease-out',
      animation: 'hudPopIn 0.3s cubic-bezier(0.16, 1, 0.3, 1)'
    }}>
      <div style={{
        background: 'rgba(10, 15, 20, 0.9)',
        backdropFilter: 'blur(20px)',
        borderRadius: '12px',
        border: `1px solid ${statusColor}44`,
        padding: '16px',
        boxShadow: '0 20px 50px rgba(0,0,0,0.6)',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
        position: 'relative',
        overflow: 'hidden'
      }}>
        {/* Accent Bar */}
        <div style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '4px',
          height: '100%',
          background: statusColor,
          boxShadow: `0 0 15px ${statusColor}`
        }} />

        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <div style={{ fontSize: '0.65rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '1.5px', marginBottom: '4px' }}>
              Container ID
            </div>
            <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#fff', letterSpacing: '0.5px', fontFamily: 'monospace' }}>
              {data.id}
            </div>
          </div>
          <div style={{ 
            background: `${statusColor}22`, 
            padding: '4px 8px', 
            borderRadius: '4px', 
            border: `1px solid ${statusColor}44`,
            fontSize: '0.65rem',
            fontWeight: 800,
            color: statusColor,
            textTransform: 'uppercase'
          }}>
            {data.type || 'Standard'}
          </div>
        </div>

        {/* Stats Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--text-secondary)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect>
              <line x1="16" y1="21" x2="16" y2="7"></line>
              <line x1="8" y1="21" x2="8" y2="7"></line>
            </svg>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontSize: '0.6rem', color: 'var(--text-secondary)', fontWeight: 600 }}>SIZE</span>
              <span style={{ fontSize: '0.85rem', fontWeight: 700 }}>{data.size || 40}ft</span>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={statusColor} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M7 20l4-16m2 16l4-16M6 9h14M4 15h14"></path>
            </svg>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontSize: '0.6rem', color: 'var(--text-secondary)', fontWeight: 600 }}>WEIGHT</span>
              <span style={{ fontSize: '0.85rem', fontWeight: 700, color: statusColor }}>{data.weight || 0}t</span>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', gridColumn: 'span 2' }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--text-secondary)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10"></circle>
              <polyline points="12 6 12 12 16 14"></polyline>
            </svg>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontSize: '0.6rem', color: 'var(--text-secondary)', fontWeight: 600 }}>DEPARTURE</span>
              <span style={{ fontSize: '0.85rem', fontWeight: 600, fontFamily: 'monospace' }}>{data.departure_time || 'N/A'}</span>
            </div>
          </div>
        </div>

        {/* Location Footer */}
        <div style={{ 
          background: 'rgba(255,255,255,0.03)', 
          margin: '0 -16px -16px -16px', 
          padding: '12px 16px', 
          borderTop: '1px solid rgba(255,255,255,0.06)',
          display: 'flex',
          flexDirection: 'column',
          gap: '4px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="var(--accent-cyan)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
              <circle cx="12" cy="10" r="3"></circle>
            </svg>
            <span style={{ fontSize: '0.6rem', color: 'var(--accent-cyan)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '1px' }}>Current Location</span>
          </div>
          <div style={{ fontSize: '1rem', fontWeight: 800, letterSpacing: '1px', color: '#fff' }}>
            {data.location?.split('-').map((part, i) => (
              <React.Fragment key={i}>
                {i > 0 && <span style={{ opacity: 0.3, margin: '0 6px' }}>/</span>}
                {part}
              </React.Fragment>
            )) || 'YARD • STACK • UNK'}
          </div>
        </div>
        
        {/* Scanning effect */}
        <div className="scanning-line" style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '2px',
          background: `linear-gradient(to right, transparent, ${statusColor}, transparent)`,
          opacity: 0.5,
          pointerEvents: 'none'
        }} />
      </div>
    </div>
  )
}
