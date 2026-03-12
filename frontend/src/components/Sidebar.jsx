import React, { useState } from 'react';
import './Sidebar.css';
import client from '../api/client';
import { Settings, PlusSquare, Play, Trash2, Info, X } from 'lucide-react';
const Sidebar = ({ yardData, onUpdate, selectedContainer, onClearSelection, searchQuery, setSearchQuery }) => {
    const [config, setConfig] = useState({ blocks: 4, bays: 10, rows: 3, height: 4 });
    const [loading, setLoading] = useState(false);

    const handleInit = async () => {
        setLoading(true);
        try {
            await client.post('/yard/init', config);
            onUpdate();
        } catch (err) {
            alert('Failed to initialize yard');
        } finally {
            setLoading(false);
        }
    };



    const handleClearYard = async () => {
        setLoading(true);
        try {
            // Send default config or current config to re-init empty
            await client.post('/yard/init', { ...config });
            onUpdate();
            alert('Yard vidé avec succès !');
        } catch (err) {
            alert('Erreur lors du vidage du yard');
        } finally {
            setLoading(false);
        }
    };

    return (
        <aside className="sidebar">
            <div className="sidebar-logo">
                <div className="logo-box">MM</div>
                <span>YARD AI</span>
            </div>

            {selectedContainer ? (
                <div className="sidebar-section glass-card inspection-panel">
                    <div className="section-header">
                        <h3 className="section-title"><Info size={18} /> Détails Conteneur</h3>
                        <button className="close-btn" onClick={onClearSelection}><X size={16} /></button>
                    </div>
                    <div className="inspection-content">
                        <div className="info-row">
                            <span className="info-label">ID:</span>
                            <span className="info-value highlighted">{selectedContainer.container_id}</span>
                        </div>
                        <div className="info-row">
                            <span className="info-label">Type:</span>
                            <span className="info-value">{selectedContainer.container_details?.type}</span>
                        </div>
                        <div className="info-row">
                            <span className="info-label">Poids:</span>
                            <span className="info-value">{selectedContainer.container_details?.weight} t</span>
                        </div>
                        <div className="info-row">
                            <span className="info-label">Taille:</span>
                            <span className="info-value">{selectedContainer.container_details?.size} ft</span>
                        </div>
                        <div className="info-row">
                            <span className="info-label">Départ:</span>
                            <span className="info-value">{new Date(selectedContainer.container_details?.departure_time).toLocaleString()}</span>
                        </div>
                        <div className="info-row">
                            <span className="info-label">Localisation:</span>
                            <span className="info-value highlighted">{selectedContainer.container_details?.location || 'N/A'}</span>
                        </div>
                    </div>
                </div>
            ) : (
                <>
                    <div className="sidebar-section">
                        <h3 className="section-title"><Settings size={18} /> Configuration</h3>
                        <div className="input-group">
                            <label>Blocs</label>
                            <input type="number" value={config.blocks} onChange={e => setConfig({ ...config, blocks: parseInt(e.target.value) })} />
                        </div>
                        <div className="input-group">
                            <label>Bays</label>
                            <input type="number" value={config.bays} onChange={e => setConfig({ ...config, bays: parseInt(e.target.value) })} />
                        </div>
                        <div className="input-group">
                            <label>Rangées</label>
                            <input type="number" value={config.rows} onChange={e => setConfig({ ...config, rows: parseInt(e.target.value) })} />
                        </div>
                        <div className="input-group">
                            <label>Hauteur</label>
                            <input type="number" value={config.height} onChange={e => setConfig({ ...config, height: parseInt(e.target.value) })} />
                        </div>
                        <button className="primary-btn" onClick={handleInit} disabled={loading}>
                            {loading ? '...' : 'Initialiser'}
                        </button>
                    </div>

                    <div className="sidebar-section">
                        <h3 className="section-title">🔍 Recherche</h3>
                        <div className="input-group">
                            <input
                                type="text"
                                placeholder="ID ou Loc (ex: A-B1-R1-T1)"
                                value={searchQuery}
                                onChange={e => setSearchQuery(e.target.value.toUpperCase())}
                                className="search-input"
                            />
                            {searchQuery && (
                                <button className="clear-search-btn" onClick={() => setSearchQuery('')}>
                                    <X size={14} />
                                </button>
                            )}
                        </div>
                    </div>




                </>
            )}

            <div className="sidebar-footer">
                <button className="danger-btn outline" onClick={handleClearYard} disabled={loading}>
                    <Trash2 size={16} /> Vider le Yard
                </button>
            </div>
        </aside>
    );
};

export default Sidebar;
