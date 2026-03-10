import React from 'react';

const Crane = ({ position, width, length, height = 8 }) => {
    return (
        <group position={position}>
            {/* Main structure legs - Left */}
            <mesh position={[-width / 2 + 0.5, height / 2, -length / 2 + 0.5]} castShadow>
                <boxGeometry args={[0.5, height, 0.5]} />
                <meshStandardMaterial color="#333" />
            </mesh>
            <mesh position={[-width / 2 + 0.5, height / 2, length / 2 - 0.5]} castShadow>
                <boxGeometry args={[0.5, height, 0.5]} />
                <meshStandardMaterial color="#333" />
            </mesh>

            {/* Main structure legs - Right */}
            <mesh position={[width / 2 - 0.5, height / 2, -length / 2 + 0.5]} castShadow>
                <boxGeometry args={[0.5, height, 0.5]} />
                <meshStandardMaterial color="#333" />
            </mesh>
            <mesh position={[width / 2 - 0.5, height / 2, length / 2 - 0.5]} castShadow>
                <boxGeometry args={[0.5, height, 0.5]} />
                <meshStandardMaterial color="#333" />
            </mesh>

            {/* Top Gantry Beams */}
            <mesh position={[0, height, -length / 2 + 0.5]} castShadow>
                <boxGeometry args={[width, 0.6, 0.6]} />
                <meshStandardMaterial color="#f1c40f" /> {/* Industrial Yellow */}
            </mesh>
            <mesh position={[0, height, length / 2 - 0.5]} castShadow>
                <boxGeometry args={[width, 0.6, 0.6]} />
                <meshStandardMaterial color="#f1c40f" />
            </mesh>

            {/* Cross Beams (the rails) */}
            <mesh position={[-width / 2 + 0.5, height, 0]} castShadow>
                <boxGeometry args={[0.6, 0.6, length]} />
                <meshStandardMaterial color="#e67e22" />
            </mesh>
            <mesh position={[width / 2 - 0.5, height, 0]} castShadow>
                <boxGeometry args={[0.6, 0.6, length]} />
                <meshStandardMaterial color="#e67e22" />
            </mesh>

            {/* Spreader/Trolley (Moveable part) */}
            <mesh position={[0, height - 0.5, 0]} castShadow>
                <boxGeometry args={[3, 0.4, 2]} />
                <meshStandardMaterial color="#2c3e50" />
            </mesh>

            {/* Cables (simplified) */}
            <mesh position={[0, height / 2 + 1, 0]}>
                <cylinderGeometry args={[0.05, 0.05, height - 2]} />
                <meshStandardMaterial color="#111" />
            </mesh>
        </group>
    );
};

export default Crane;
