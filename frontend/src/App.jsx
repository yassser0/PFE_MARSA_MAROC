import { useState, useEffect, useCallback, useRef } from 'react'
import axios from 'axios'
import Sidebar from './components/Sidebar'
import KpiHeader from './components/KpiHeader'
import GlobalView3D from './components/GlobalView3D'
import BlockDetailView from './components/BlockDetailView'
import AnalyticsView from './components/AnalyticsView'
import ContainerInfoDrawer from './components/ContainerInfoDrawer'
import logo from './assets/logo.png'

const API_URL = 'http://127.0.0.1:8000'
const TABS = ['Vue Globale 3D', 'Vue Détail Bloc', 'Heatmap & Analytique']

export default function App() {
  const [yardData, setYardData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [apiOnline, setApiOnline] = useState(false)
  const [activeTab, setActiveTab] = useState('Vue Globale 3D')
  const [selectedBlock, setSelectedBlock] = useState('A')
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedContainer, setSelectedContainer] = useState(null)
  const [lastRefresh, setLastRefresh] = useState(new Date())
  const intervalRef = useRef(null)

  const fetchYardData = useCallback(async () => {
    try {
      const res = await axios.get(`${API_URL}/yard?_t=${Date.now()}`)
      setYardData(res.data)
      setApiOnline(true)
      setLastRefresh(new Date())
    } catch {
      setApiOnline(false)
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

  // Auto-select container on search match
  useEffect(() => {
    if (!searchQuery || !yardData) {
      setSelectedContainer(null)
      return
    }

    // Search globally across all blocks
    for (const block of yardData.blocks) {
      for (const stack of block.stacks) {
        for (const slot of stack.slots) {
          if (!slot.is_free && (slot.container_id === searchQuery || slot.container_details?.location === searchQuery)) {
            setSelectedContainer({ id: slot.container_id, ...slot.container_details })
            return
          }
        }
      }
    }
  }, [searchQuery, yardData])

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
    await axios.post(`${API_URL}/yard/init`, { blocks: 4, bays: 24, rows: 6, max_height: 5 }).catch(() => { })
    await fetchYardData()
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
            <GlobalView3D
              yardData={yardData}
              searchQuery={searchQuery}
              onInspectBlock={handleInspectBlock}
              onSelectContainer={setSelectedContainer}
            />
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
            <AnalyticsView yardData={yardData} />
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
