import { useState } from 'react'
import axios from 'axios'

const API_URL = "http://127.0.0.1:8000"

export default function BatchUpload({ onUploadSuccess }) {
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [stats, setStats] = useState(null)
  const [error, setError] = useState(null)

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0]
    if (selectedFile && selectedFile.type === "text/csv") {
      setFile(selectedFile)
      setError(null)
    } else {
      setError("Please select a valid CSV file.")
      setFile(null)
    }
  }

  const parseCSV = (text) => {
    const lines = text.split('\n').filter(line => line.trim() !== '')
    const headers = lines[0].split(',').map(h => h.trim().toLowerCase())
    
    return lines.slice(1).map(line => {
      const values = line.split(',').map(v => v.trim())
      const entry = {}
      headers.forEach((header, i) => {
        entry[header] = values[i]
      })
      
      // Data normalization
      return {
        id: entry.id || null,
        weight: parseFloat(entry.weight) || 15.0,
        type: (entry.type || 'import').toLowerCase(),
        departure_time: entry.departure_time || new Date(Date.now() + 86400000 * 7).toISOString(),
        size: entry.size ? parseInt(entry.size) : 20
      }
    })
  }

  const handleUpload = async () => {
    if (!file) return

    setLoading(true)
    setError(null)
    setStats(null)

    try {
      const reader = new FileReader()
      reader.onload = async (e) => {
        const text = e.target.result
        const data = parseCSV(text)

        try {
          const response = await axios.post(`${API_URL}/containers/place_batch`, data)
          setStats(response.data)
          if (onUploadSuccess) onUploadSuccess()
        } catch (err) {
          setError(err.response?.data?.detail || "Error connecting to the optimization engine.")
        }
        setLoading(false)
      }
      reader.readAsText(file)
    } catch (err) {
      setError("Failed to read file.")
      setLoading(false)
    }
  }

  return (
    <div style={{
      marginTop: '25px',
      padding: '20px',
      background: 'rgba(255, 255, 255, 0.03)',
      borderRadius: '12px',
      border: '1px solid rgba(255, 255, 255, 0.05)'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '15px' }}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--accent-cyan)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
          <polyline points="17 8 12 3 7 8"></polyline>
          <line x1="12" y1="3" x2="12" y2="15"></line>
        </svg>
        <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '1px' }}>
          Batch CSV Pipeline
        </span>
      </div>

      <div style={{ marginBottom: '15px' }}>
        <input 
          type="file" 
          accept=".csv" 
          onChange={handleFileChange}
          id="csv-upload-input"
          style={{ display: 'none' }}
        />
        <label htmlFor="csv-upload-input" style={{
          display: 'block',
          width: '100%',
          padding: '12px',
          background: 'rgba(255,255,255,0.02)',
          border: '1px dashed rgba(255,255,255,0.15)',
          borderRadius: '8px',
          textAlign: 'center',
          cursor: 'pointer',
          color: file ? 'var(--accent-cyan)' : 'var(--text-muted)',
          fontSize: '0.75rem',
          fontWeight: 600,
          transition: 'all 0.2s'
        }}>
          {file ? `📄 ${file.name}` : "Drop CSV or Click to Browse"}
        </label>
      </div>

      <button 
        onClick={handleUpload} 
        disabled={!file || loading}
        style={{
          width: '100%',
          background: 'linear-gradient(135deg, var(--accent-cyan), #00a8ff)',
          color: '#000',
          border: 'none',
          padding: '12px',
          borderRadius: '8px',
          fontWeight: 800,
          fontSize: '0.75rem',
          textTransform: 'uppercase',
          letterSpacing: '1px',
          cursor: file && !loading ? 'pointer' : 'default',
          opacity: file && !loading ? 1 : 0.5,
          boxShadow: file && !loading ? '0 4px 15px rgba(0, 253, 255, 0.3)' : 'none',
          transition: 'all 0.2s'
        }}
      >
        {loading ? 'Optimizing...' : 'Run Optimization Pipeline'}
      </button>

      {error && (
        <div style={{
          marginTop: '15px',
          padding: '10px',
          background: 'rgba(248, 81, 73, 0.1)',
          border: '1px solid rgba(248, 81, 73, 0.2)',
          color: '#f85149',
          fontSize: '0.7rem',
          borderRadius: '6px'
        }}>
          {error}
        </div>
      )}

      {stats && (
        <div style={{
          marginTop: '15px',
          padding: '12px',
          background: 'rgba(63, 185, 80, 0.05)',
          border: '1px solid rgba(63, 185, 80, 0.15)',
          borderRadius: '8px'
        }}>
          <div style={{ color: '#3fb950', fontWeight: 800, fontSize: '0.7rem', marginBottom: '8px', textTransform: 'uppercase' }}>
            Pipeline Success
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
            <div style={statItemStyle}>
              <span style={statLabelStyle}>PLACED</span>
              <span style={statValueStyle}>{stats.containers_placed}</span>
            </div>
            <div style={statItemStyle}>
              <span style={statLabelStyle}>FAILED</span>
              <span style={statValueStyle}>{stats.failed_placements}</span>
            </div>
            <div style={statItemStyle}>
              <span style={statLabelStyle}>OCCUPANCY</span>
              <span style={statValueStyle}>{stats.yard_occupancy}</span>
            </div>
            <div style={statItemStyle}>
              <span style={statLabelStyle}>TIME</span>
              <span style={statValueStyle}>{stats.processing_time_ms}ms</span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

const statItemStyle = {
  display: 'flex',
  flexDirection: 'column',
  background: 'rgba(255,255,255,0.02)',
  padding: '6px 8px',
  borderRadius: '4px'
}

const statLabelStyle = {
  fontSize: '0.55rem',
  color: 'var(--text-muted)',
  fontWeight: 700,
  letterSpacing: '0.5px'
}

const statValueStyle = {
  fontSize: '0.8rem',
  color: '#fff',
  fontWeight: 800
}
