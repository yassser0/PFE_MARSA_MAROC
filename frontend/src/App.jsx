import { useState, useEffect, useCallback, useRef } from 'react'
import axios from 'axios'
import Sidebar from './components/Sidebar'
import KpiHeader from './components/KpiHeader'
import GlobalView3D from './components/GlobalView3D'
import BlockDetailView from './components/BlockDetailView'
import AnalyticsView from './components/AnalyticsView'
import ContainerTable from './components/ContainerTable'
import ContainerInfoDrawer from './components/ContainerInfoDrawer'
import ErrorBoundary from './components/ErrorBoundary'
import logo from './assets/logo.png'

const API_URL = 'http://127.0.0.1:8000'
const TABS = ['Vue Globale 3D', 'Vue Détail Bloc', 'Heatmap & Analytique', 'Tableau des Conteneurs']

export default function App() {
  const [yardData, setYardData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [apiOnline, setApiOnline] = useState(false)
  const [activeTab, setActiveTab] = useState('Vue Globale 3D')
  const [selectedBlock, setSelectedBlock] = useState('A')
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedContainer, setSelectedContainer] = useState(null)
  const [lastRefresh, setLastRefresh] = useState(new Date())
  const [goldKpis, setGoldKpis] = useState(null)
  const [silverReport, setSilverReport] = useState(null)
  const intervalRef = useRef(null)

  const fetchYardData = useCallback(async () => {
    try {
      const res = await axios.get(`${API_URL}/yard?_t=${Date.now()}`)
      setYardData(res.data)
      setApiOnline(true)
      setLastRefresh(new Date())

      // Tenter de récupérer les derniers KPIs Gold pour l'affichage analytique
      try {
        const kpisRes = await axios.get(`${API_URL}/containers/latest-kpis`)
        if (kpisRes.data && !kpisRes.data.message) {
          setGoldKpis(kpisRes.data)
          if (kpisRes.data.pipeline_quality) {
            setSilverReport({
              quality_score: kpisRes.data.pipeline_quality.quality_score_pct,
              total_raw: kpisRes.data.pipeline_quality.total_raw_ingested,
              total_cleaned: kpisRes.data.pipeline_quality.total_after_silver,
              duplicates_removed: kpisRes.data.pipeline_quality.duplicates_removed,
              invalid_nulls_removed: kpisRes.data.pipeline_quality.invalid_removed,
            })
          }
        } else {
          // Si aucun KPI n'est trouvé (après un reset), on vide l'état
          setGoldKpis(null)
          setSilverReport(null)
        }
      } catch (e) {
        setGoldKpis(null)
        setSilverReport(null)
      }

    } finally {
      setLoading(false)
    }
  }, [])

  // Auto-refresh every 15 seconds
  useEffect(() => {
    fetchYardData()
    intervalRef.current = setInterval(fetchYardData, 15000)
    return () => clearInterval(intervalRef.current)
  }, [fetchYardData])


  const handleInitYard = async (config) => {
    try {
      const res = await axios.post(`${API_URL}/yard/init`, config)
      await fetchYardData()
      return { ok: true, message: res.data.message, capacity: res.data.total_capacity }
    } catch (e) {
      return { ok: false, message: e?.response?.data?.detail || 'Erreur inconnue' }
    }
  }

  const handleClearYard = async () => {
    const config = yardData ? {
      blocks: Math.max(1, yardData.n_blocks - 2), // Soustraire S1 et S2 qui sont ajoutés par le backend
      bays: yardData.n_bays,
      rows: yardData.n_rows,
      max_height: yardData.max_height
    } : { blocks: 4, bays: 24, rows: 6, max_height: 5 }

    await axios.post(`${API_URL}/yard/init`, config).catch(() => { })
    await fetchYardData()
  }

  const handleUploadSuccess = async (etlResult) => {
    if (etlResult) {
      if (etlResult.gold_kpis) setGoldKpis(etlResult.gold_kpis)
      if (etlResult.silver_report) setSilverReport(etlResult.silver_report)
    }
    await fetchYardData()
    setActiveTab('Vue Globale 3D')
  }

  const handleInspectBlock = (blockId) => {
    setSelectedBlock(blockId)
    setActiveTab('Vue Détail Bloc')
  }

  return (
    <div className="app-layout">
      <Sidebar
        apiOnline={apiOnline}
        lastRefresh={lastRefresh}
        onInit={handleInitYard}
        onClear={handleClearYard}
        onRefresh={fetchYardData}
        onUploadSuccess={handleUploadSuccess}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
      />

      <div className="main-content">
        {/* KPI Header */}
        <header className="header">
          <div className="header-top">
            <h1 className="header-title">
              <img src={logo} alt="Marsa Maroc" style={{ height: '32px', marginRight: '12px', verticalAlign: 'middle' }} />
              Marsa Maroc — Yard Optimization
            </h1>
            <div className="connection-status">
              <div className={`status-dot ${apiOnline ? '' : 'offline'}`} />
              <span style={{ color: 'var(--text-secondary)' }}>
                {apiOnline ? 'API connectée' : 'API hors ligne'}
              </span>
            </div>
          </div>
          {yardData && <KpiHeader data={yardData} />}
        </header>

        {/* Tabs */}
        <div className="tabs-bar">
          {TABS.map(tab => (
            <button
              key={tab}
              className={`tab-btn ${activeTab === tab ? 'active' : ''}`}
              onClick={() => setActiveTab(tab)}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="tab-content">
          {loading && (
            <div className="loading-spinner">
              <div className="spinner" />
              <span>Connexion à l'API...</span>
            </div>
          )}

          {!loading && !apiOnline && (
            <div className="alert alert-error">
              🚨 API non accessible. Veuillez lancer <code>python main.py api</code>.
            </div>
          )}

          {!loading && yardData && activeTab === 'Vue Globale 3D' && (
            <ErrorBoundary name="Vue 3D Globale">
              <GlobalView3D
                yardData={yardData}
                searchQuery={searchQuery}
                onInspectBlock={handleInspectBlock}
                onSelectContainer={setSelectedContainer}
              />
            </ErrorBoundary>
          )}

          {!loading && yardData && activeTab === 'Vue Détail Bloc' && (
            <BlockDetailView
              yardData={yardData}
              selectedBlock={selectedBlock}
              onBlockChange={setSelectedBlock}
              searchQuery={searchQuery}
              onSelectContainer={setSelectedContainer}
            />
          )}

          {!loading && yardData && activeTab === 'Heatmap & Analytique' && (
            <AnalyticsView yardData={yardData} goldKpis={goldKpis} silverReport={silverReport} />
          )}

          {!loading && yardData && activeTab === 'Tableau des Conteneurs' && (
            <ContainerTable 
              yardData={yardData} 
              searchQuery={searchQuery}
              onSelectContainer={setSelectedContainer}
            />
          )}
        </div>
      </div>

      <ContainerInfoDrawer
        container={selectedContainer}
        onClose={() => setSelectedContainer(null)}
      />
    </div>
  )
}
