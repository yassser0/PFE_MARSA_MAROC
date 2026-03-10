import React, { useState } from 'react';
import { Edges } from '@react-three/drei';

const Container = ({ slot, position, onSelect, searchQuery }) => {
    const [hovered, setHovered] = useState(false);

    const isMatch = searchQuery && (
        searchQuery === slot.container_id ||
        (slot.container_details?.location && searchQuery === slot.container_details.location)
    );

    // Realistic color palette
    let color = '#2ca02c'; // Green
    if (slot.container_details?.type === 'export') color = '#2c7fb8'; // Blue
    if (slot.container_details?.type === 'transshipment') color = '#e67e22'; // Orange-ish

    if (isMatch) color = '#ff0000'; // Search match - RED

    return (
        <group position={position}>
            <mesh
                castShadow
                receiveShadow
                onPointerOver={(e) => { e.stopPropagation(); setHovered(true); }}
                onPointerOut={() => setHovered(false)}
                onClick={(e) => { e.stopPropagation(); if (onSelect) onSelect(slot); }}
            >
                <boxGeometry args={[2.3, 0.9, 1.2]} />
                <meshStandardMaterial
                    color={color}
                    metalness={0.7}
                    roughness={0.3}
                    emissive={hovered ? color : '#000'}
                    emissiveIntensity={hovered ? 0.3 : 0}
                />
                {/* Simulated corrugation/edges for realism */}
                <Edges
                    threshold={15}
                    color={hovered ? '#fff' : '#111'}
                    renderOrder={1}
                >
                    <meshBasicMaterial color={hovered ? '#fff' : '#222'} />
                </Edges>
            </mesh>

            {/* Simple ID text or indicator could go here in future */}
        </group>
    );
};

export default Container;
