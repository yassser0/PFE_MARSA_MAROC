import React from 'react';
import './KPICard.css';

const KPICard = ({ title, value, icon }) => {
    return (
        <div className="kpi-card glass-card">
            <div className="kpi-icon-wrapper">
                {icon}
            </div>
            <div className="kpi-content">
                <span className="kpi-title">{title}</span>
                <h2 className="kpi-value">{value}</h2>
            </div>
        </div>
    );
};

export default KPICard;
