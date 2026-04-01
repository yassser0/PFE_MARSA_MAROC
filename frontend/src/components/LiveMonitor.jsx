import { useState, useEffect } from 'react'
import axios from 'axios'

const API_URL = 'http://127.0.0.1:8000'

export default function LiveMonitor() {
  const [data, setData] = useState(null)
  const [status, setStatus] = useState('waiting')
  const [error, setError] = useState(null)
  const [lastFetch, setLastFetch] = useState(new Date())

  const fetchData = async () => {
    try {
      const res = await axios.get(`${API_URL}/streaming/kpis?_t=${Date.now()}`)
      if (res.data.status === 'active') {
        setData(res.data.data)
        setStatus('active')
      } else {
        setStatus('waiting')
      }
      setLastFetch(new Date())
      setError(null)
    } catch (err) {
      console.error('Error fetching streaming KPIs:', err)
      setError("Impossible de contacter le service de streaming.")
    }
  }

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 5000)
    return () => clearInterval(interval)
  }, [])

  if (error) {
    return <div className="alert alert-error">{error}</div>
  }

  if (status === 'waiting') {
    return (
      <div className="live-monitor-placeholder">
        <div className="spinner-container">
          <div className="pulse-loader" />
          <p>En attente du flux temps réel (Spark Structured Streaming)...</p>
          <small style={{ opacity: 0.7 }}>Assurez-vous que <code>python streaming/spark_streamer.py</code> est lancé.</small>
        </div>
      </div>
    )
  }

  const { last_update, batch_id, total_placed_in_stream, yard_occupancy, last_container } = data || {}
  
  // Format date if exists
  const luDt = last_update ? new Date(last_update).toLocaleTimeString() : 'N/A'

  return (
    <div className="live-monitor">
      <div className="live-header">
        <div className="live-badge">
          <span className="live-dot" />
          EN DIRECT
        </div>
        <div className="live-meta">
          Dernière mise à jour : {luDt} (Batch #{batch_id || 0})
        </div>
      </div>

      <div className="live-stats-grid">
        <div className="live-card highlight">
          <h3>Placés via Streaming</h3>
          <div className="value">{total_placed_in_stream || 0}</div>
          <div className="subtitle">Conteneurs insérés en temps réel</div>
        </div>

        <div className="live-card">
          <h3>Dernier Conteneur</h3>
          <div className="value-small" style={{marginTop: '15px'}}>{last_container || 'Aucun'}</div>
        </div>
        
        <div className="live-card">
          <h3>Occupation Portuaire</h3>
          <div className="value-small" style={{marginTop: '15px'}}>{yard_occupancy || '0%'}</div>
        </div>
      </div>

      <div className="live-info-box">
        <h4>Architecture Big Data Pillar 1</h4>
        <p>
          Ce dashboard est alimenté par <strong>Spark Structured Streaming</strong>. 
          Les données sont ingérées depuis HDFS, nettoyées en mode Silver, 
          puis agrégées en mode Gold via des fenêtres glissantes (Sliding Windows).
        </p>
      </div>
    </div>
  )
}
