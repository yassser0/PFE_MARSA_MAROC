import React, { useState } from 'react';
import client from '../api/client';
import { Plus } from 'lucide-react';

const ContainerForm = ({ onPlaced }) => {
    const [formData, setFormData] = useState({
        size: 20,
        weight: 15.0,
        type: 'import',
        departure_time: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
        zones_20ft: ['A', 'B'],
        zones_40ft: ['C', 'D']
    });

    const handleSubmit = async (e) => {
        e.preventDefault();
        try {
            const response = await client.post('/containers/place', formData);
            alert(`Success! Container placed in ${response.data.best_slot.position_key}`);
            onPlaced();
        } catch (err) {
            alert('Placement failed: ' + (err.response?.data?.detail || err.message));
        }
    };

    return (
        <form onSubmit={handleSubmit} className="placement-form">
            <div className="input-row">
                <div className="input-group half">
                    <label>Taille</label>
                    <select value={formData.size} onChange={e => setFormData({ ...formData, size: parseInt(e.target.value) })}>
                        <option value={20}>20ft</option>
                        <option value={40}>40ft</option>
                    </select>
                </div>
                <div className="input-group half">
                    <label>Poids (t)</label>
                    <input type="number" step="0.5" value={formData.weight} onChange={e => setFormData({ ...formData, weight: parseFloat(e.target.value) })} />
                </div>
            </div>

            <div className="input-group">
                <label>Type</label>
                <select value={formData.type} onChange={e => setFormData({ ...formData, type: e.target.value })}>
                    <option value="import">Import</option>
                    <option value="export">Export</option>
                    <option value="transshipment">Transshipment</option>
                </select>
            </div>

            <button type="submit" className="primary-btn pulse">
                <Plus size={18} /> Placer Conteneur
            </button>

            <style jsx>{`
        .placement-form { margin-top: 10px; }
        .input-row { display: flex; gap: 10px; }
        .half { flex: 1; }
        select {
          width: 100%;
          background: rgba(255, 255, 255, 0.05);
          border: 1px solid var(--border-light);
          color: white;
          padding: 10px;
          border-radius: 6px;
        }
        .pulse:hover { 
          box-shadow: 0 0 15px var(--accent-green);
        }
      `}</style>
        </form>
    );
};

export default ContainerForm;
