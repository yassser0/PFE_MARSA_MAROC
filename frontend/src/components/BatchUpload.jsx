import { useState, useCallback } from 'react'
import axios from 'axios'

const API_URL = "http://127.0.0.1:8000"

// ── Styles partagés ──────────────────────────────────────────────────────────
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

// ── Composant badge couche ────────────────────────────────────────────────────
function LayerBadge({ label, color, icon }) {
  return (
    <div style={{
      display: 'inline-flex', alignItems: 'center', gap: '5px',
      padding: '2px 8px', borderRadius: '20px',
      background: `${color}18`, border: `1px solid ${color}40`,
      fontSize: '0.6rem', fontWeight: 800, color,
      letterSpacing: '1px', textTransform: 'uppercase'
    }}>
      {icon} {label}
    </div>
  )
}

// ── Composant rapport couche ──────────────────────────────────────────────────
function LayerReport({ title, color, icon, children }) {
  const [open, setOpen] = useState(false)
  return (
    <div style={{
      marginBottom: '8px', borderRadius: '8px',
      border: `1px solid ${color}25`,
      background: `${color}08`, overflow: 'hidden'
    }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          width: '100%', display: 'flex', alignItems: 'center',
          justifyContent: 'space-between', background: 'none',
          border: 'none', padding: '8px 12px', cursor: 'pointer',
          color, fontSize: '0.65rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '1px'
        }}
      >
        <span>{icon} {title}</span>
        <span style={{ fontSize: '0.8rem', opacity: 0.7 }}>{open ? '▲' : '▼'}</span>
      </button>
      {open && (
        <div style={{ padding: '0 12px 10px', fontSize: '0.62rem', color: 'var(--text-secondary)' }}>
          {children}
        </div>
      )}
    </div>
  )
}

// ── Composant principal ───────────────────────────────────────────────────────
export default function BatchUpload({ onUploadSuccess }) {
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [dragOver, setDragOver] = useState(false)

  const handleFile = useCallback((f) => {
    if (f && f.name.endsWith('.csv')) {
      setFile(f)
      setError(null)
      setResult(null)
    } else {
      setError("Veuillez sélectionner un fichier .csv valide.")
    }
  }, [])

  const handleFileChange = (e) => handleFile(e.target.files[0])

  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    handleFile(e.dataTransfer.files[0])
  }

  const handleUpload = async () => {
    if (!file) return
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const formData = new FormData()
      formData.append('file', file)

      // 1. Envoyer le fichier pour lancer la tâche de fond
      const response = await axios.post(
        `${API_URL}/containers/upload-csv`,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } }
      )

      if (response.data.status === 'processing') {
        // 2. Commencer le polling
        const pollInterval = setInterval(async () => {
          try {
            const statusRes = await axios.get(`${API_URL}/containers/upload-status`)
            const job = statusRes.data

            if (job.status === 'success') {
              clearInterval(pollInterval)
              setResult(job.result)
              setLoading(false)
              if (onUploadSuccess) onUploadSuccess(job.result)
            } else if (job.status === 'error') {
              clearInterval(pollInterval)
              setError(job.message || "Erreur lors du traitement ETL.")
              setLoading(false)
            }
            // Si c'est toujours 'processing', on ne fait rien et on attend le prochain tick
          } catch (pollErr) {
            clearInterval(pollInterval)
            setError("Connexion perdue avec le serveur pendant le traitement.")
            setLoading(false)
          }
        }, 1000) // Polling toutes les secondes
      } else {
        // Fallback just in case
        setResult(response.data)
        setLoading(false)
        if (onUploadSuccess) onUploadSuccess(response.data)
      }
    } catch (err) {
      setLoading(false)
      const detail = err.response?.data?.detail
      setError(
        typeof detail === 'string'
          ? detail
          : "Erreur de connexion à la pipeline ETL."
      )
    }
  }

  return (
    <div style={{
      marginTop: '25px', padding: '20px',
      background: 'rgba(255,255,255,0.03)', borderRadius: '12px',
      border: '1px solid rgba(255,255,255,0.05)'
    }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '15px' }}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--accent-cyan)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
          <polyline points="17 8 12 3 7 8" />
          <line x1="12" y1="3" x2="12" y2="15" />
        </svg>
        <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '1px' }}>
          ETL Pipeline · CSV Upload
        </span>
      </div>

      {/* Badges couches */}
      <div style={{ display: 'flex', gap: '5px', flexWrap: 'wrap', marginBottom: '15px' }}>
        <LayerBadge label="Bronze" color="#cd7f32" icon="📦" />
        <LayerBadge label="Silver" color="#a8b2c0" icon="🧹" />
        <LayerBadge label="Gold" color="#d4a017" icon="📊" />
      </div>

      {/* Zone de dépôt */}
      <div
        onDrop={handleDrop}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onClick={() => document.getElementById('csv-etl-input').click()}
        style={{
          marginBottom: '12px', padding: '16px',
          background: dragOver ? 'rgba(0,253,255,0.07)' : 'rgba(255,255,255,0.02)',
          border: `1px dashed ${dragOver ? 'var(--accent-cyan)' : 'rgba(255,255,255,0.15)'}`,
          borderRadius: '8px', textAlign: 'center', cursor: 'pointer',
          transition: 'all 0.2s'
        }}
      >
        <input type="file" accept=".csv" onChange={handleFileChange} id="csv-etl-input" style={{ display: 'none' }} />
        <div style={{ fontSize: '1.2rem', marginBottom: '6px' }}>
          {file ? '📄' : '📁'}
        </div>
        <div style={{
          color: file ? 'var(--accent-cyan)' : 'var(--text-muted)',
          fontSize: '0.72rem', fontWeight: 700
        }}>
          {file ? file.name : 'Glisser-déposer ou cliquer pour choisir'}
        </div>
        {file && (
          <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)', marginTop: '4px' }}>
            {(file.size / 1024).toFixed(1)} KB
          </div>
        )}
      </div>

      {/* Bouton lancer */}
      <button
        onClick={handleUpload}
        disabled={!file || loading}
        style={{
          width: '100%',
          background: loading
            ? 'rgba(255,255,255,0.05)'
            : 'linear-gradient(135deg, #cd7f32, #d4a017, var(--accent-cyan))',
          color: loading ? 'var(--text-secondary)' : '#000',
          border: 'none', padding: '12px 16px',
          borderRadius: '8px', fontWeight: 800,
          fontSize: '0.75rem', textTransform: 'uppercase',
          letterSpacing: '1px', cursor: file && !loading ? 'pointer' : 'default',
          opacity: file ? 1 : 0.5, transition: 'all 0.2s',
          boxShadow: (file && !loading) ? '0 4px 20px rgba(212, 160, 23, 0.4)' : 'none',
          position: 'relative', overflow: 'hidden'
        }}
      >
        {loading ? (
          <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
            <span style={{
              display: 'inline-block', width: '10px', height: '10px',
              border: '2px solid rgba(255,255,255,0.3)',
              borderTopColor: 'var(--accent-cyan)', borderRadius: '50%',
              animation: 'spin 0.8s linear infinite'
            }} />
            Pipeline ETL en cours...
          </span>
        ) : 'Lancer le traitement de données '}
      </button>

      {/* Erreur */}
      {error && (
        <div style={{
          marginTop: '12px', padding: '10px 12px',
          background: 'rgba(248,81,73,0.08)', border: '1px solid rgba(248,81,73,0.25)',
          borderRadius: '8px', color: '#f85149', fontSize: '0.7rem', fontWeight: 600
        }}>
          ❌ {error}
        </div>
      )}

      {/* Résultat pipeline */}
      {result && result.pipeline_status === 'SUCCESS' && (
        <div style={{ marginTop: '14px' }}>

          {/* Bannière succès */}
          <div style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            marginBottom: '10px', padding: '8px 10px',
            background: 'rgba(63,185,80,0.07)', border: '1px solid rgba(63,185,80,0.2)',
            borderRadius: '8px'
          }}>
            <span style={{ color: '#3fb950', fontWeight: 800, fontSize: '0.68rem', textTransform: 'uppercase' }}>
              ✅ Pipeline Réussie
            </span>
            <span style={{ fontSize: '0.6rem', color: 'var(--text-muted)', fontWeight: 700 }}>
              {result.processing_time_ms}ms total
            </span>
          </div>

          {/* KPIs placement */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '6px', marginBottom: '10px' }}>
            <div style={statItemStyle}>
              <span style={statLabelStyle}>BRONZE</span>
              <span style={{ ...statValueStyle, color: '#cd7f32' }}>{result.bronze_report?.total_rows_ingested ?? '-'}</span>
            </div>
            <div style={statItemStyle}>
              <span style={statLabelStyle}>SILVER</span>
              <span style={{ ...statValueStyle, color: '#a8b2c0' }}>{result.silver_report?.total_cleaned ?? '-'}</span>
            </div>
            <div style={statItemStyle}>
              <span style={statLabelStyle}>PLACÉS</span>
              <span style={{ ...statValueStyle, color: '#3fb950' }}>{result.containers_placed}</span>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px', marginBottom: '10px' }}>
            <div style={statItemStyle}>
              <span style={statLabelStyle}>OCCUPANCY</span>
              <span style={{ ...statValueStyle, color: 'var(--accent-cyan)' }}>{result.yard_occupancy}</span>
            </div>
            <div style={statItemStyle}>
              <span style={statLabelStyle}>ZONE TAMPON</span>
              <span style={{ ...statValueStyle, color: '#d29922' }}>{result.waitlist_count || 0}</span>
            </div>
          </div>

        </div>
      )}

      {/* Keyframe pour le spinner */}
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  )
}
