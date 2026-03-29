import { useMemo, useState } from 'react'

export default function ContainerTable({ yardData, searchQuery, onSelectContainer }) {
  const [sortField, setSortField] = useState('departure_time')
  const [sortDir, setSortDir] = useState('asc')

  // Extraire tous les conteneurs du yard
  const allContainers = useMemo(() => {
    if (!yardData) return []
    const list = []
    Object.values(yardData.blocks || {}).forEach(block => {
      Object.values(block.bays || {}).forEach(bay => {
        Object.values(bay.rows || {}).forEach(row => {
          (row.tiers || []).forEach(slot => {
            if (slot.container) {
              list.push({
                ...slot.container,
                slotId: slot.localization
              })
            }
          })
        })
      })
    })
    return list
  }, [yardData])

  // Filtrer par recherche
  const filtered = useMemo(() => {
    if (!searchQuery) return allContainers
    const lower = searchQuery.toLowerCase()
    return allContainers.filter(c => 
      c.id.toLowerCase().includes(lower) || 
      c.slotId.toLowerCase().includes(lower) ||
      c.type.toLowerCase().includes(lower)
    )
  }, [allContainers, searchQuery])

  // Trier
  const sorted = useMemo(() => {
    return [...filtered].sort((a, b) => {
      let valA = a[sortField]
      let valB = b[sortField]

      if (sortField === 'weight' || sortField === 'size') {
        valA = Number(valA || 0)
        valB = Number(valB || 0)
      } else if (sortField === 'departure_time') {
        valA = new Date(valA).getTime()
        valB = new Date(valB).getTime()
      } else {
        valA = String(valA || '').toLowerCase()
        valB = String(valB || '').toLowerCase()
      }

      if (valA < valB) return sortDir === 'asc' ? -1 : 1
      if (valA > valB) return sortDir === 'asc' ? 1 : -1
      return 0
    })
  }, [filtered, sortField, sortDir])

  const handleSort = (field) => {
    if (sortField === field) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDir('asc')
    }
  }

  const thStyle = {
    padding: '12px 15px',
    textAlign: 'left',
    color: 'var(--text-secondary)',
    fontSize: '0.75rem',
    fontWeight: 800,
    textTransform: 'uppercase',
    letterSpacing: '1px',
    cursor: 'pointer',
    borderBottom: '1px solid rgba(255,255,255,0.05)',
    userSelect: 'none'
  }

  const tdStyle = {
    padding: '14px 15px',
    borderBottom: '1px solid rgba(255,255,255,0.03)',
    fontSize: '0.85rem',
    color: '#fff'
  }

  const getTypeStyle = (type) => {
    switch (type) {
      case 'import': return { bg: 'rgba(63, 185, 80, 0.15)', color: '#3fb950' }
      case 'export': return { bg: 'rgba(212, 160, 23, 0.15)', color: '#d4a017' }
      case 'transshipment': return { bg: 'rgba(0, 253, 255, 0.15)', color: '#00fdff' }
      default: return { bg: 'rgba(255,255,255,0.1)', color: '#fff' }
    }
  }

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      
      <div style={{ marginBottom: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '1.2rem', color: '#fff' }}>Inventaire des Conteneurs</h2>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
            {sorted.length} conteneurs placés sur {allContainers.length} total
          </span>
        </div>
      </div>

      <div style={{
        flex: 1,
        background: 'rgba(255,255,255,0.02)',
        borderRadius: '12px',
        border: '1px solid rgba(255,255,255,0.05)',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column'
      }}>
        <div style={{ overflowY: 'auto', flex: 1 }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead style={{ position: 'sticky', top: 0, background: 'rgba(15, 20, 25, 0.95)', backdropFilter: 'blur(10px)', zIndex: 10 }}>
              <tr>
                <th style={thStyle} onClick={() => handleSort('id')}>ID {sortField === 'id' && (sortDir === 'asc' ? '↑' : '↓')}</th>
                <th style={thStyle} onClick={() => handleSort('slotId')}>Position {sortField === 'slotId' && (sortDir === 'asc' ? '↑' : '↓')}</th>
                <th style={thStyle} onClick={() => handleSort('type')}>Type {sortField === 'type' && (sortDir === 'asc' ? '↑' : '↓')}</th>
                <th style={thStyle} onClick={() => handleSort('size')}>Taille {sortField === 'size' && (sortDir === 'asc' ? '↑' : '↓')}</th>
                <th style={thStyle} onClick={() => handleSort('weight')}>Poids (T) {sortField === 'weight' && (sortDir === 'asc' ? '↑' : '↓')}</th>
                <th style={thStyle} onClick={() => handleSort('departure_time')}>Départ {sortField === 'departure_time' && (sortDir === 'asc' ? '↑' : '↓')}</th>
                <th style={thStyle}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {sorted.length === 0 ? (
                <tr>
                  <td colSpan="7" style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                    Aucun conteneur trouvé.
                  </td>
                </tr>
              ) : (
                sorted.map(c => {
                  const typeColors = getTypeStyle(c.type)
                  return (
                    <tr key={c.id} style={{ transition: 'background 0.2s', cursor: 'pointer' }}
                        onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.03)'}
                        onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                        onClick={() => onSelectContainer(c)}>
                      <td style={{ ...tdStyle, fontWeight: 800, color: 'var(--accent-cyan)' }}>{c.id}</td>
                      <td style={tdStyle}>
                        <span style={{ padding: '4px 8px', background: 'rgba(255,255,255,0.05)', borderRadius: '4px', fontFamily: 'monospace' }}>
                          {c.slotId}
                        </span>
                      </td>
                      <td style={tdStyle}>
                        <span style={{
                          padding: '4px 10px',
                          borderRadius: '20px',
                          fontSize: '0.75rem',
                          fontWeight: 700,
                          background: typeColors.bg,
                          color: typeColors.color,
                          textTransform: 'uppercase'
                        }}>
                          {c.type}
                        </span>
                      </td>
                      <td style={tdStyle}>{c.size} ft</td>
                      <td style={tdStyle}>{c.weight.toFixed(2)}</td>
                      <td style={tdStyle}>{new Date(c.departure_time).toLocaleString('fr-FR')}</td>
                      <td style={tdStyle}>
                        <button
                          onClick={(e) => { e.stopPropagation(); onSelectContainer(c) }}
                          style={{
                            background: 'rgba(0, 253, 255, 0.1)',
                            border: '1px solid rgba(0, 253, 255, 0.3)',
                            color: 'var(--accent-cyan)',
                            padding: '6px 12px',
                            borderRadius: '4px',
                            cursor: 'pointer',
                            fontSize: '0.7rem',
                            fontWeight: 700
                          }}
                        >
                          Détails
                        </button>
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
