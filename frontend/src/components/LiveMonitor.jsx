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

  const { total_arrivals, by_type, window_start, window_end } = data

  return (
    <div className="live-monitor">
      <div className="live-header">
        <div className="live-badge">
          <span className="live-dot" />
          EN DIRECT
        </div>
        <div className="live-meta">
          Fenêtre : {new Date(window_start).toLocaleTimeString()} - {new Date(window_end).toLocaleTimeString()}
        </div>
      </div>

      <div className="live-stats-grid">
        <div className="live-card highlight">
          <h3>Arrivées (10 min)</h3>
          <div className="value">{total_arrivals}</div>
          <div className="subtitle">Conteneurs détectés</div>
        </div>

        {Object.entries(by_type).map(([type, stats]) => (
          <div key={type} className="live-card">
            <h3>Type: {type}</h3>
            <div className="value-small">{stats.count} unités</div>
            <div className="progress-bar">
              <div 
                className="progress-fill" 
                style={{ width: `${(stats.count / total_arrivals) * 100}%` }} 
              />
            </div>
            <div className="footer-stat">Poids moy: {stats.avg_weight} t</div>
          </div>
        ))}
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
