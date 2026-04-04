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

// ── File Zone Item ────────────────────────────────────────────────────────────
function FileZone({ label, file, onFileSelect, icon, color = 'var(--accent-cyan)' }) {
  const [dragOver, setDragOver] = useState(false)
  
  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    if (e.dataTransfer.files[0]?.name.endsWith('.csv')) {
      onFileSelect(e.dataTransfer.files[0])
    }
  }

  return (
    <div style={{ flex: 1, minWidth: '140px' }}>
      <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)', fontWeight: 800, marginBottom: '6px', textTransform: 'uppercase' }}>
        {label}
      </div>
      <div
        onDrop={handleDrop}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onClick={() => {
            const input = document.createElement('input');
            input.type = 'file';
            input.accept = '.csv';
            input.onchange = (e) => onFileSelect(e.target.files[0]);
            input.click();
        }}
        style={{
          padding: '12px',
          background: dragOver ? `${color}10` : 'rgba(255,255,255,0.02)',
          border: `1px dashed ${dragOver ? color : 'rgba(255,255,255,0.15)'}`,
          borderRadius: '8px', textAlign: 'center', cursor: 'pointer',
          transition: 'all 0.2s', borderStyle: file ? 'solid' : 'dashed',
          borderColor: file ? color : undefined
        }}
      >
        <div style={{ fontSize: '1rem', marginBottom: '4px' }}>
          {file ? '✅' : icon}
        </div>
        <div style={{
          color: file ? color : 'var(--text-muted)',
          fontSize: '0.65rem', fontWeight: 700,
          whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'
        }}>
          {file ? file.name : 'Choisir .csv'}
        </div>
      </div>
    </div>
  )
}

// ── Composant principal ───────────────────────────────────────────────────────
export default function BatchUpload({ onUploadSuccess }) {
  const [mode, setMode] = useState('standard') // 'standard' or 'hybrid'
  const [file, setFile] = useState(null)          // Arrivals file
  const [snapshotFile, setSnapshotFile] = useState(null) // Snapshot file (hybrid only)
  
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const handleUpload = async () => {
    if (!file) return
    if (mode === 'hybrid' && !snapshotFile) {
        setError("Veuillez sélectionner les deux fichiers pour le mode hybride.")
        return
    }

    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const formData = new FormData()
      
      let endpoint = `${API_URL}/containers/upload-csv`
      if (mode === 'hybrid') {
          endpoint = `${API_URL}/containers/upload-dual-csv`
          formData.append('snapshot', snapshotFile)
          formData.append('arrivals', file)
      } else {
          formData.append('file', file)
      }

      // 1. Envoyer le fichier pour lancer la tâche de fond
      const response = await axios.post(
        endpoint,
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
          } catch (pollErr) {
            clearInterval(pollInterval)
            setError("Connexion perdue avec le serveur.")
            setLoading(false)
          }
        }, 1000)
      }
    } catch (err) {
      setLoading(false)
      setError(err.response?.data?.detail || "Erreur de connexion à l'API.")
    }
  }

  return (
    <div style={{
      marginTop: '25px', padding: '20px',
      background: 'rgba(255,255,255,0.03)', borderRadius: '12px',
      border: '1px solid rgba(255,255,255,0.05)'
    }}>
      {/* Header & Toggle */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--accent-cyan)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '1px' }}>
            {mode === 'hybrid' ? 'Hybrid Processing' : 'Standard ETL'}
            </span>
        </div>

        {/* Toggle Mode */}
        <div style={{ 
            display: 'flex', background: 'rgba(255,255,255,0.05)', 
            borderRadius: '20px', padding: '2px', border: '1px solid rgba(255,255,255,0.1)'
        }}>
            <button 
                onClick={() => setMode('standard')}
                style={{
                    border: 'none', background: mode === 'standard' ? 'var(--accent-cyan)' : 'transparent',
                    color: mode === 'standard' ? '#000' : 'var(--text-muted)',
                    fontSize: '0.55rem', fontWeight: 800, padding: '4px 10px', 
                    borderRadius: '20px', cursor: 'pointer', transition: '0.2s'
                }}>STANDARD</button>
            <button 
                onClick={() => setMode('hybrid')}
                style={{
                    border: 'none', background: mode === 'hybrid' ? 'var(--accent-cyan)' : 'transparent',
                    color: mode === 'hybrid' ? '#000' : 'var(--text-muted)',
                    fontSize: '0.55rem', fontWeight: 800, padding: '4px 10px', 
                    borderRadius: '20px', cursor: 'pointer', transition: '0.2s'
                }}>HYBRID (SNAPSHOT)</button>
        </div>
      </div>

      {/* Badges couches */}
      <div style={{ display: 'flex', gap: '5px', flexWrap: 'wrap', marginBottom: '20px' }}>
        <LayerBadge label="Bronze" color="#cd7f32" icon="📦" />
        <LayerBadge label="Silver" color="#a8b2c0" icon="🧹" />
        <LayerBadge label="Gold" color="#d4a017" icon="📊" />
      </div>

      {/* Zone(s) de dépôt */}
      <div style={{ display: 'flex', gap: '12px', marginBottom: '15px' }}>
        {mode === 'hybrid' && (
            <FileZone 
                label="1. Snapshot Terminal" 
                file={snapshotFile} 
                onFileSelect={setSnapshotFile} 
                icon="🏗️" 
                color="#d4a017"
            />
        )}
        <FileZone 
            label={mode === 'hybrid' ? "2. Nouvelles Arrivées" : "Fichier Conteneurs"} 
            file={file} 
            onFileSelect={setFile} 
            icon="🚢" 
            color="var(--accent-cyan)"
        />
      </div>

      {/* Bouton lancer */}
      <button
        onClick={handleUpload}
        disabled={!file || (mode === 'hybrid' && !snapshotFile) || loading}
        style={{
          width: '100%',
          background: loading
            ? 'rgba(255,255,255,0.05)'
            : 'linear-gradient(135deg, #cd7f32, #d4a017, var(--accent-cyan))',
          color: loading ? 'var(--text-secondary)' : '#000',
          border: 'none', padding: '12px 16px',
          borderRadius: '8px', fontWeight: 800,
          fontSize: '0.75rem', textTransform: 'uppercase',
          letterSpacing: '1px', cursor: 'pointer',
          opacity: (!file || (mode === 'hybrid' && !snapshotFile)) ? 0.3 : 1, 
          transition: 'all 0.2s',
          boxShadow: loading ? 'none' : '0 4px 20px rgba(212, 160, 23, 0.4)'
        }}
      >
        {loading ? 'Traitement en cours...' : mode === 'hybrid' ? 'Lancer Optimisation Hybride' : 'Lancer Traitement ETL'}
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
          <div style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            marginBottom: '10px', padding: '8px 10px',
            background: 'rgba(63,185,80,0.07)', border: '1px solid rgba(63,185,80,0.2)',
            borderRadius: '8px'
          }}>
            <span style={{ color: '#3fb950', fontWeight: 800, fontSize: '0.68rem', textTransform: 'uppercase' }}>
              ✅ Succès : {result.total_placed} conteneurs placés
            </span>
            <span style={{ fontSize: '0.6rem', color: 'var(--text-muted)', fontWeight: 700 }}>
              {result.processing_time_ms}ms
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px' }}>
            {result.arrivals_report && (
                <div style={statItemStyle}>
                    <span style={statLabelStyle}>ARRIVÉES (OPTIMISÉS)</span>
                    <span style={{ ...statValueStyle, color: 'var(--accent-cyan)' }}>{result.arrivals_report.placed}</span>
                </div>
            )}
            <div style={statItemStyle}>
              <span style={statLabelStyle}>OCCUPATION GLOBALE</span>
              <span style={{ ...statValueStyle, color: '#fff' }}>{result.yard_occupancy}</span>
            </div>
            <div style={statItemStyle}>
              <span style={statLabelStyle}>STATUS GÉNÉRAL</span>
              <span style={{ ...statValueStyle, color: '#3fb950' }}>OPÉRATIONNEL</span>
            </div>
          </div>
        </div>
      )}

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  )
}
