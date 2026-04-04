import { useState } from 'react'
import logo from '../assets/logo.png'
import BatchUpload from './BatchUpload'

export default function Sidebar({
  apiOnline, lastRefresh, onInit, onClear, onRefresh, onUploadSuccess,
  searchQuery, onSearchChange
}) {
  const [blocks, setBlocks] = useState(4)
  const [bays, setBays] = useState(12)
  const [rows, setRows] = useState(6)
  const [height, setHeight] = useState(5)
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
      showFeedback('success', `✅ ${result.message}`)
    } else {
      showFeedback('error', `❌ ${result.message}`)
    }
  }

  const handleClear = async () => {
    setClearLoading(true)
    await onClear()
    setClearLoading(false)
    showFeedback('success', '🧹 Yard vidé avec succès.')
  }

  return (
    <aside className="sidebar" style={{
      background: 'rgba(10, 15, 20, 0.7)',
      backdropFilter: 'blur(20px)',
      borderRight: '1px solid rgba(255,255,255,0.08)',
      width: '320px',
      height: '100vh',
      display: 'flex',
      flexDirection: 'column',
      padding: '0',
      zIndex: 100,
      boxShadow: '10px 0 40px rgba(0,0,0,0.5)',
      position: 'relative'
    }}>
      {/* Top Accent Bar */}
      <div style={{
        position: 'absolute',
        top: 0,
        left: 0,
        height: '2px',
        width: '100%',
        background: 'linear-gradient(to right, var(--accent-cyan), transparent)',
        opacity: 0.8
      }} />

      {/* Logo Header */}
      <div style={{
        padding: '30px 25px',
        display: 'flex',
        alignItems: 'center',
        gap: '15px',
        borderBottom: '1px solid rgba(255,255,255,0.05)'
      }}>
        <div style={{
          padding: '8px',
          background: 'rgba(255,255,255,0.03)',
          borderRadius: '12px',
          border: '1px solid rgba(255,255,255,0.05)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}>
          <img src={logo} alt="Logo" style={{ height: '32px', objectFit: 'contain' }} />
        </div>
        <div>
          <h2 style={{
            margin: 0,
            fontSize: '1rem',
            fontWeight: 800,
            color: '#fff',
            letterSpacing: '1px',
            textTransform: 'uppercase'
          }}>
            Marsa <span style={{ color: 'var(--accent-cyan)' }}>MAROC</span>
          </h2>
          <span style={{
            fontSize: '0.65rem',
            color: 'var(--text-secondary)',
            textTransform: 'uppercase',
            fontWeight: 700,
            letterSpacing: '2px'
          }}>
            Yard Optimizer
          </span>
        </div>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '25px' }}>

        {/* Search Section */}
        <section style={{ marginBottom: '35px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '15px' }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--accent-cyan)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8"></circle>
              <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            </svg>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '1px' }}>
              Quick Lookup
            </span>
          </div>
          <div style={{ position: 'relative' }}>
            <input
              type="text"
              value={searchQuery}
              onChange={e => onSearchChange(e.target.value.trim().toUpperCase())}
              placeholder="Search ID or Pos..."
              style={{
                width: '100%',
                background: 'rgba(255,255,255,0.03)',
                border: '1px solid rgba(255,255,255,0.08)',
                borderRadius: '8px',
                padding: '12px 15px',
                color: '#fff',
                fontSize: '0.85rem',
                outline: 'none',
                transition: 'all 0.3s'
              }}
              onFocus={(e) => e.target.style.borderColor = 'var(--accent-cyan)'}
              onBlur={(e) => e.target.style.borderColor = 'rgba(255,255,255,0.08)'}
            />
            {searchQuery && (
              <button
                onClick={() => onSearchChange('')}
                style={{
                  position: 'absolute',
                  right: '10px',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-secondary)',
                  cursor: 'pointer',
                  fontSize: '1.2rem'
                }}
              >
                &times;
              </button>
            )}
          </div>
        </section>

        {/* Configuration Section */}
        <section>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '15px' }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--accent-cyan)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="3" width="7" height="7"></rect>
              <rect x="14" y="3" width="7" height="7"></rect>
              <rect x="14" y="14" width="7" height="7"></rect>
              <rect x="3" y="14" width="7" height="7"></rect>
            </svg>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '1px' }}>
              Yard Parameters
            </span>
          </div>

          <form onSubmit={handleInit} style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div className="form-group-custom">
                <label style={{ fontSize: '0.6rem', color: 'var(--text-secondary)', fontWeight: 700, display: 'block', marginBottom: '6px' }}>BLOCKS</label>
                <input type="number" min={1} max={20} value={blocks} onChange={e => setBlocks(+e.target.value)} style={inputStyle} />
              </div>
              <div className="form-group-custom">
                <label style={{ fontSize: '0.6rem', color: 'var(--text-secondary)', fontWeight: 700, display: 'block', marginBottom: '6px' }}>BAYS</label>
                <input type="number" min={1} max={50} value={bays} onChange={e => setBays(+e.target.value)} style={inputStyle} />
              </div>
              <div className="form-group-custom">
                <label style={{ fontSize: '0.6rem', color: 'var(--text-secondary)', fontWeight: 700, display: 'block', marginBottom: '6px' }}>ROWS</label>
                <input type="number" min={1} max={50} value={rows} onChange={e => setRows(+e.target.value)} style={inputStyle} />
              </div>
              <div className="form-group-custom">
                <label style={{ fontSize: '0.6rem', color: 'var(--text-secondary)', fontWeight: 700, display: 'block', marginBottom: '6px' }}>TIERS</label>
                <input type="number" min={1} max={8} value={height} onChange={e => setHeight(+e.target.value)} style={inputStyle} />
              </div>
            </div>

            <button type="submit" disabled={initLoading} style={{
              background: 'var(--accent-cyan)',
              color: '#000',
              border: 'none',
              padding: '12px',
              borderRadius: '8px',
              fontWeight: 800,
              fontSize: '0.75rem',
              textTransform: 'uppercase',
              letterSpacing: '1px',
              cursor: 'pointer',
              marginTop: '5px',
              boxShadow: '0 4px 15px rgba(0, 253, 255, 0.3)',
              transition: 'all 0.2s'
            }}>
              {initLoading ? 'Processing...' : 'Sync Parameters'}
            </button>
          </form>

          {feedback && (
            <div style={{
              marginTop: '15px',
              padding: '10px 15px',
              borderRadius: '6px',
              fontSize: '0.75rem',
              fontWeight: 600,
              background: feedback.type === 'success' ? 'rgba(63, 185, 80, 0.1)' : 'rgba(248, 81, 73, 0.1)',
              border: `1px solid ${feedback.type === 'success' ? 'rgba(63, 185, 80, 0.2)' : 'rgba(248, 81, 73, 0.2)'}`,
              color: feedback.type === 'success' ? '#3fb950' : '#f85149'
            }}>
              {feedback.message}
            </div>
          )}
        </section>

        {/* Batch Upload Section */}
        <BatchUpload onUploadSuccess={onUploadSuccess || onRefresh} />

        {/* Global Actions */}
        <section style={{ marginTop: '35px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <button onClick={onRefresh} style={secondaryButtonStyle}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: '8px' }}>
              <path d="M23 4v6h-6"></path>
              <path d="M1 20v-6h6"></path>
              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
            </svg>
            Refresh Engine
          </button>
          <button onClick={handleClear} disabled={clearLoading} style={{
            ...secondaryButtonStyle,
            borderColor: 'rgba(248, 81, 73, 0.3)',
            color: '#f85149'
          }}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: '8px' }}>
              <polyline points="3 6 5 6 21 6"></polyline>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
            </svg>
            {clearLoading ? 'Clearing...' : 'Clear All Units'}
          </button>
        </section>

      </div>

      {/* Footer Status */}
      <div style={{
        padding: '20px 25px',
        background: 'rgba(0,0,0,0.1)',
        borderTop: '1px solid rgba(255,255,255,0.05)',
        fontSize: '0.7rem'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
          <div style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            background: apiOnline ? '#3fb950' : '#f85149',
            boxShadow: `0 0 10px ${apiOnline ? '#3fb950' : '#f85149'}`
          }} />
          <span style={{ fontWeight: 700, color: apiOnline ? '#3fb950' : '#f85149' }}>
            {apiOnline ? 'SYSTEM OPERATIONAL' : 'SYSTEM OFFLINE'}
          </span>
        </div>
        <div style={{ color: 'var(--text-muted)', fontSize: '0.6rem', fontWeight: 600 }}>
          LAST UPDATE: {lastRefresh.toLocaleTimeString('fr-FR')}
        </div>
      </div>
    </aside>
  )
}

const inputStyle = {
  width: '100%',
  background: 'rgba(255,255,255,0.03)',
  border: '1px solid rgba(255,255,255,0.08)',
  borderRadius: '6px',
  padding: '8px 10px',
  color: '#fff',
  fontSize: '0.8rem',
  fontWeight: 700,
  outline: 'none'
}

const secondaryButtonStyle = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  width: '100%',
  background: 'rgba(255,255,255,0.03)',
  border: '1px solid rgba(255,255,255,0.1)',
  borderRadius: '8px',
  padding: '10px',
  color: 'var(--text-primary)',
  fontSize: '0.75rem',
  fontWeight: 700,
  textTransform: 'uppercase',
  letterSpacing: '0.5px',
  cursor: 'pointer',
  transition: 'all 0.2s'
}
