import React, { useState, useEffect } from 'react';
import './App.css';
import client from './api/client';
import Sidebar from './components/Sidebar';
import Yard3D from './components/Yard3D';
import KPICard from './components/KPICard';
import { Ship, RefreshCw, BarChart3, Box } from 'lucide-react';

function App() {
  const [yardData, setYardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('3D View');

  const [selectedBlock, setSelectedBlock] = useState(null);
  const [selectedContainer, setSelectedContainer] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');

  const fetchYardData = async () => {
    try {
      const response = await client.get('/yard');
      setYardData(response.json || response.data);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch yard data:', err);
      setError('Connection to API failed');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchYardData();
    const interval = setInterval(fetchYardData, 5000);
    return () => clearInterval(interval);
  }, []);

  const renderView = () => {
    if (!yardData) return <div className="placeholder-msg">Chargement...</div>;

    switch (activeTab) {
      case '3D View':
        return <Yard3D data={yardData} onSelectContainer={setSelectedContainer} onSelectBlock={(id) => { setSelectedBlock(id); setActiveTab('Detail'); }} searchQuery={searchQuery} />;
      case 'Detail':
        const block = yardData.blocks.find(b => b.block_id === (selectedBlock || 'A'));
        return (
          <div className="view-container">
            <div className="view-header">
              <h3>Inspection du Bloc {block?.block_id}</h3>
              <button className="secondary-btn small" onClick={() => setActiveTab('3D View')}>Retour</button>
            </div>
            <div className="detail-canvas-wrapper">
              <Yard3D data={{ ...yardData, blocks: [block] }} isDetailView onSelectContainer={setSelectedContainer} searchQuery={searchQuery} />
            </div>
          </div>
        );
      case 'Analytics':
        return (
          <div className="view-container analytics-view">
            <h3>Analytique Globale</h3>
            <div className="charts-grid">
              {yardData.blocks.map(b => (
                <div key={b.block_id} className="chart-item glass-card">
                  <div className="chart-info">
                    <h4>Bloc {b.block_id}</h4>
                    <span>{(b.occupancy * 100).toFixed(1)}%</span>
                  </div>
                  <div className="bar-bg">
                    <div className="bar-fill" style={{ width: `${b.occupancy * 100}%` }}></div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="app-container">
      <Sidebar
        yardData={yardData}
        onUpdate={fetchYardData}
        selectedContainer={selectedContainer}
        onClearSelection={() => setSelectedContainer(null)}
        searchQuery={searchQuery}
        setSearchQuery={setSearchQuery}
      />

      <main className="main-content">
        <header className="main-header">
          <div className="title-section">
            <h1><Ship size={32} className="accent-icon" /> Marsa Maroc Yard Intelligence</h1>
            <p className="subtitle">Systeme d'Optimisation et de Visualisation 3D</p>
          </div>

          <div className="tabs-container">
            {['3D View', 'Detail', 'Analytics'].map(tab => (
              <button
                key={tab}
                className={`tab-btn ${activeTab === tab ? 'active' : ''}`}
                onClick={() => setActiveTab(tab)}
              >
                {tab}
              </button>
            ))}
          </div>
        </header>

        {yardData && (
          <div className="kpi-grid">
            <KPICard title="Occupation" value={`${(yardData.occupancy_rate * 100).toFixed(1)}%`} icon={<BarChart3 />} />
            <KPICard title="Slots Occupés" value={yardData.used_slots} icon={<Box />} />
            <KPICard title="Capacité Totale" value={yardData.total_capacity} icon={<Ship />} />
            <KPICard title="Hauteur Moyenne" value={yardData.average_stack_height.toFixed(1)} icon={<RefreshCw />} />
          </div>
        )}

        <div className="canvas-container">
          {renderView()}
        </div>
      </main>
    </div>
  );
}

export default App;
