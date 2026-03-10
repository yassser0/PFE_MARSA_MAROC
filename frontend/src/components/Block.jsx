import React, { useState } from 'react';
import { Text } from '@react-three/drei';
import Container from './Container';

const Block = ({ block, maxHeight, onSelectContainer, onSelectBlock, isDetailView, searchQuery }) => {
    const { x: bx, y: by, block_id, stacks } = block;
    const [hovered, setHovered] = useState(false);

    return (
        <group
            position={[bx, 0, by]}
            onPointerOver={(e) => { e.stopPropagation(); setHovered(true); }}
            onPointerOut={() => setHovered(false)}
            onClick={(e) => { e.stopPropagation(); if (onSelectBlock) onSelectBlock(block_id); }}
        >
            {/* Block Ground Slab - Dynamic width for spacing */}
            <mesh position={[block.width * 1.4, -0.05, block.length * 1.2 / 2]} receiveShadow>
                <boxGeometry args={[block.width * 3, 0.1, block.length * 1.5]} />
                <meshStandardMaterial
                    color={hovered && !isDetailView ? "#4ade80" : "#222"}
                    opacity={hovered && !isDetailView ? 0.4 : 0.6}
                    transparent
                />
            </mesh>

            {/* Block Name Label */}
            {!isDetailView && (
                <Text
                    position={[block.width, 10, block.length / 2]}
                    fontSize={3}
                    color="white"
                    anchorX="center"
                    anchorY="middle"
                    rotation={[0, -Math.PI / 2, 0]} // Rotate to face camera better
                >
                    Bloc {block_id}
                </Text>
            )}

            {stacks.map((stack) => (
                <group key={`${block_id}-B${stack.bay}-R${stack.row}`} position={[(stack.row - 1) * 4.5, 0, (stack.bay - 1) * 2.5]}>
                    {stack.slots.map((slot) => {
                        if (slot.is_free) return null;
                        return (
                            <Container
                                key={`${block_id}-${stack.bay}-${stack.row}-${slot.tier}`}
                                slot={slot}
                                position={[0, (slot.tier - 0.5) * 1.0, 0]}
                                onSelect={onSelectContainer}
                                searchQuery={searchQuery}
                            />
                        );
                    })}
                </group>
            ))}
        </group>
    );
};

export default Block;
