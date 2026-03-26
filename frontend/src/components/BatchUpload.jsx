import { useState } from 'react'
import axios from 'axios'

const API_URL = "http://127.0.0.1:8000"

export default function BatchUpload({ onUploadSuccess }) {
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [stats, setStats] = useState(null)
  const [error, setError] = useState(null)
  const [validationErrors, setValidationErrors] = useState([])
  const [validData, setValidData] = useState([])

  const validateRow = (entry, index) => {
    const errors = []
    
    if (!entry.id) errors.push("ID manquant")
    
    const weight = parseFloat(entry.weight)
    if (isNaN(weight) || weight < 1.0 || weight > 50.0) {
      errors.push(`Poids invalide (${entry.weight}t) - doit être entre 1 et 50`)
    }
    
    const size = parseInt(entry.size)
    if (isNaN(size) || (size !== 20 && size !== 40)) {
      errors.push(`Taille invalide (${entry.size}) - doit être 20 ou 40`)
    }
    
    try {
      if (entry.departure_time) {
        new Date(entry.departure_time).toISOString()
      } else {
        errors.push("Date de départ manquante")
      }
    } catch (e) {
      errors.push(`Format de date invalide (${entry.departure_time})`)
    }
    
    return errors.length > 0 ? { row: index + 2, errors } : null
  }

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0]
    if (selectedFile && (selectedFile.type === "text/csv" || selectedFile.name.endsWith('.csv'))) {
      setFile(selectedFile)
      setError(null)
      setValidationErrors([])
      setStats(null)
      
      const reader = new FileReader()
      reader.onload = (event) => {
        const text = event.target.result
        const lines = text.split('\n').filter(line => line.trim() !== '')
        if (lines.length < 2) {
          setError("Le fichier CSV est vide ou mal formé.")
          return
        }
        
        const headers = lines[0].split(',').map(h => h.trim().toLowerCase())
        const rows = lines.slice(1).map(line => {
          const values = line.split(',').map(v => v.trim())
          const entry = {}
          headers.forEach((header, i) => { entry[header] = values[i] })
          return entry
        })
        
        const foundErrors = []
        const parsedData = rows.map((row, i) => {
          const err = validateRow(row, i)
          if (err) foundErrors.push(err)
          
          let formattedDate = row.departure_time;
          try {
            if (row.departure_time) {
              formattedDate = new Date(row.departure_time).toISOString();
            }
          } catch(e) {}
          
          return {
            id: row.id,
            weight: parseFloat(row.weight),
            type: (row.type || 'import').toLowerCase(),
            departure_time: formattedDate,
            size: parseInt(row.size)
          }
        })
        
        setValidationErrors(foundErrors)
        setValidData(foundErrors.length === 0 ? parsedData : [])
      }
      reader.readAsText(selectedFile)
    } else {
      setError("Veuillez sélectionner un fichier CSV valide.")
      setFile(null)
    }
  }

  const handleUpload = async () => {
    if (!validData.length || validationErrors.length > 0) return

    setLoading(true)
    setError(null)
    setStats(null)

    try {
      const response = await axios.post(`${API_URL}/containers/place_batch`, validData)
      setStats(response.data)
      if (onUploadSuccess) onUploadSuccess()
    } catch (err) {
      setError(err.response?.data?.detail || "Erreur de connexion au moteur d'optimisation.")
    } finally {
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
        disabled={!file || loading || validationErrors.length > 0}
        style={{
          width: '100%',
          background: validationErrors.length > 0 
            ? 'rgba(248, 81, 73, 0.1)' 
            : 'linear-gradient(135deg, var(--accent-cyan), #00a8ff)',
          color: validationErrors.length > 0 ? '#f85149' : '#000',
          border: validationErrors.length > 0 ? '1px solid rgba(248, 81, 73, 0.3)' : 'none',
          padding: '12px',
          borderRadius: '8px',
          fontWeight: 800,
          fontSize: '0.75rem',
          textTransform: 'uppercase',
          letterSpacing: '1px',
          cursor: validData.length && !loading ? 'pointer' : 'default',
          opacity: file && !loading ? 1 : 0.5,
          boxShadow: validData.length && !loading ? '0 4px 15px rgba(0, 253, 255, 0.3)' : 'none',
          transition: 'all 0.2s'
        }}
      >
        {loading ? 'Optimisation en cours...' : 
         validationErrors.length > 0 ? `${validationErrors.length} Erreurs Détectées` :
         'Lancer la Pipeline d\'Optimisation'}
      </button>

      {validationErrors.length > 0 && (
        <div style={{
          marginTop: '15px',
          padding: '12px',
          background: 'rgba(248, 81, 73, 0.05)',
          border: '1px solid rgba(248, 81, 73, 0.2)',
          borderRadius: '8px',
          maxHeight: '150px',
          overflowY: 'auto'
        }}>
          <div style={{ color: '#f85149', fontWeight: 800, fontSize: '0.65rem', marginBottom: '8px', textTransform: 'uppercase' }}>
            Rapport de Validation ({validationErrors.length} erreurs)
          </div>
          {validationErrors.map((err, i) => (
            <div key={i} style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', marginBottom: '4px', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '2px' }}>
              <strong style={{ color: '#f85149' }}>Ligne {err.row}:</strong> {err.errors.join(', ')}
            </div>
          ))}
        </div>
      )}

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
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
             <div style={{ color: '#3fb950', fontWeight: 800, fontSize: '0.7rem', textTransform: 'uppercase' }}>
              Pipeline Success
            </div>
            {stats.silver_report && (
              <div style={{ fontSize: '0.6rem', color: 'var(--accent-cyan)', fontWeight: 700 }}>
                SILVER LAYER: {stats.silver_report.quality_score}% CLEAN
              </div>
            )}
          </div>

          {stats.silver_report && (
            <div style={{ 
              marginBottom: '15px', 
              padding: '8px', 
              background: 'rgba(0,253,255,0.03)', 
              borderRadius: '6px',
              fontSize: '0.65rem',
              color: 'var(--text-secondary)',
              border: '1px solid rgba(0,253,255,0.05)'
            }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '5px' }}>
                <span>📦 Bruts: {stats.silver_report.total_raw}</span>
                <span>🧹 Doublons: {stats.silver_report.duplicates_removed}</span>
                <span>🚫 Invalides: {stats.silver_report.invalid_rows_filtered}</span>
                <span style={{ color: 'var(--accent-cyan)' }}>✨ Silver: {stats.silver_report.total_cleaned}</span>
              </div>
            </div>
          )}

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
