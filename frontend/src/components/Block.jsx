import React, { useState } from 'react';
import Container from './Container';

const Block = ({ block, maxHeight, onSelectContainer, onSelectBlock, isDetailView }) => {
    const { x: bx, y: by, block_id, stacks } = block;
    const [hovered, setHovered] = useState(false);

    return (
        <group
            position={[bx, 0, by]}
            onPointerOver={(e) => { e.stopPropagation(); setHovered(true); }}
            onPointerOut={() => setHovered(false)}
            onClick={(e) => { e.stopPropagation(); if (onSelectBlock) onSelectBlock(block_id); }}
        >
            {/* Block Ground Slab */}
            <mesh position={[block.width / 2, 0.05, block.length / 2]} receiveShadow>
                <boxGeometry args={[block.width, 0.1, block.length]} />
                <meshStandardMaterial
                    color={hovered && !isDetailView ? "#4ade80" : "#333"}
                    opacity={hovered && !isDetailView ? 0.4 : 0.2}
                    transparent
                />
            </mesh>

            {stacks.map((stack) => (
                <group key={`${block_id}-R${stack.row}`} position={[0, 0, (stack.row - 1) * 1.2]}>
                    {stack.slots.map((slot) => {
                        if (slot.is_free) return null;
                        return (
                            <Container
                                key={`${block_id}-${stack.row}-${slot.tier}`}
                                slot={slot}
                                position={[block.width / 2, (slot.tier - 0.5) * 1.0, 0.5]}
                                onSelect={onSelectContainer}
                            />
                        );
                    })}
                </group>
            ))}
        </group>
    );
};

export default Block;
