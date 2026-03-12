import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import KpiHeader from './components/KpiHeader';
import TabNav from './components/TabNav';
import GlobalView3D from './components/GlobalView3D';
import BlockDetail3D from './components/BlockDetail3D';
import Analytics from './components/Analytics';
import { useYardData } from './hooks/useYardData';

export default function App() {
  const { data, error, loading, refresh, lastUpdate } = useYardData(5000);
  const [activeTab, setActiveTab] = useState('Vue Globale 3D');
  const [selectedBlock, setSelectedBlock] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');

  const handleBlockClick = (blockId) => {
    setSelectedBlock(blockId);
    setActiveTab('Vue Détail Bloc');
  };

  const handleTabChange = (tab) => {
    setActiveTab(tab);
    // Wenn auf Block Detail gewechselt und kein Block ausgewählt, ersten Block auswählen
    if (tab === 'Vue Détail Bloc' && !selectedBlock && data?.blocks?.length > 0) {
      setSelectedBlock(data.blocks[0].block_id);
    }
  };

  return (
    <div className="app-layout">
      <Sidebar
        onRefresh={refresh}
        lastUpdate={lastUpdate}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        onBlockSelect={setSelectedBlock}
      />

      <main className="main-content">
        <header className="page-header">
          <div className="header-left">
            <h1>⚓ Marsa Maroc — Yard Intelligence</h1>
            <span className="header-subtitle">TC3 · Terminal à Conteneurs</span>
          </div>
          <div className="header-status">
            {loading && !data && <span className="status-badge loading">⏳ Chargement…</span>}
            {error && <span className="status-badge error">🚨 API non accessible</span>}
            {data && !error && <span className="status-badge ok">🟢 En ligne</span>}
          </div>
        </header>

        {error && !data && (
          <div className="api-error-banner">
            🚨 Impossible de contacter l'API. Vérifiez que <code>python main.py api</code> est en cours d'exécution sur le port 8000.
          </div>
        )}

        <KpiHeader data={data} />

        <div className="content-card">
          <div className="tab-and-blocks">
            <TabNav active={activeTab} onChange={handleTabChange} />

            {/* Quick block navigation buttons in global view */}
            {activeTab === 'Vue Globale 3D' && data && (
              <div className="block-nav-strip">
                {data.blocks.map((b) => (
                  <button
                    key={b.block_id}
                    className="block-nav-btn"
                    onClick={() => handleBlockClick(b.block_id)}
                    title={`Occupation: ${(b.occupancy * 100).toFixed(1)}%`}
                  >
                    Bloc {b.block_id}
                    <span className="block-nav-occ" style={{
                      color: b.occupancy >= 0.8 ? '#d62728' : b.occupancy >= 0.5 ? '#ff7f0e' : '#2ca02c'
                    }}>
                      {(b.occupancy * 100).toFixed(0)}%
                    </span>
                  </button>
                ))}
              </div>
            )}

            {/* Block selector for detail view */}
            {activeTab === 'Vue Détail Bloc' && data && (
              <div className="block-selector-row">
                <label>Choisir le bloc :</label>
                <div className="block-selector-btns">
                  {data.blocks.map((b) => (
                    <button
                      key={b.block_id}
                      className={`block-sel-btn ${selectedBlock === b.block_id ? 'active' : ''}`}
                      onClick={() => setSelectedBlock(b.block_id)}
                    >
                      Bloc {b.block_id}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {activeTab === 'Vue Globale 3D' && (
            <GlobalView3D
              yardData={data}
              searchQuery={searchQuery}
              onBlockClick={handleBlockClick}
            />
          )}

          {activeTab === 'Vue Détail Bloc' && (
            <BlockDetail3D
              yardData={data}
              selectedBlock={selectedBlock || data?.blocks?.[0]?.block_id}
              searchQuery={searchQuery}
            />
          )}

          {activeTab === 'Heatmap & Analytique' && (
            <Analytics yardData={data} />
          )}
        </div>
      </main>
    </div>
  );
}
