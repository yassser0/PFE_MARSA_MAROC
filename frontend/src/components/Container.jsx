import React, { useState } from 'react';

const Container = ({ slot, position, onSelect }) => {
    const [hovered, setHovered] = useState(false);

    // Color coding by type
    let color = '#2ca02c'; // Default green
    if (slot.container_details?.type === 'export') color = '#2c7fb8';
    if (slot.container_details?.type === 'transshipment') color = '#feb24c';

    return (
        <mesh
            position={position}
            castShadow
            receiveShadow
            onPointerOver={(e) => { e.stopPropagation(); setHovered(true); if (onSelect) onSelect(slot); }}
            onPointerOut={() => setHovered(false)}
            onClick={(e) => { e.stopPropagation(); if (onSelect) onSelect(slot); }}
        >
            <boxGeometry args={[1.2, 0.9, 1]} />
            <meshStandardMaterial
                color={hovered ? '#4ade80' : color}
                metalness={0.6}
                roughness={0.2}
                emissive={hovered ? '#2ca02c' : '#000'}
                emissiveIntensity={hovered ? 0.5 : 0}
            />
        </mesh>
    );
};

export default Container;
