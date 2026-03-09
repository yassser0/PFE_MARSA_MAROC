import React, { Suspense } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, PerspectiveCamera, Environment, ContactShadows, Sky, Float } from '@react-three/drei';
import Block from './Block';

const Yard3D = ({ data, onSelectContainer, onSelectBlock, isDetailView }) => {
    if (!data) return <div className="loading-overlay">Chargement des données...</div>;

    return (
        <div style={{ width: '100%', height: '100%', position: 'relative' }}>
            <Canvas shadows>
                <Suspense fallback={null}>
                    <PerspectiveCamera makeDefault position={isDetailView ? [15, 15, 15] : [60, 50, 60]} fov={50} />
                    <OrbitControls
                        makeDefault
                        minPolarAngle={0}
                        maxPolarAngle={Math.PI / 2.1}
                        enableDamping={true}
                    />

                    <Sky distance={450000} sunPosition={[0, 1, 0]} inclination={0} azimuth={0.25} />
                    <ambientLight intensity={0.4} />
                    <pointLight position={[100, 100, 100]} intensity={1.2} castShadow />
                    <directionalLight
                        position={[-50, 100, 50]}
                        intensity={2}
                        castShadow
                        shadow-mapSize={[4096, 4096]}
                    />

                    <Environment preset="city" />

                    {/* Terminal Group - Rotated to match TC3 Photo */}
                    <group rotation={[0, -Math.PI / 6, 0]}>
                        <group position={[0, 0, 0]}>
                            {data.blocks.map((block) => (
                                <Block
                                    key={block.block_id}
                                    block={block}
                                    maxHeight={data.max_height}
                                    onSelectContainer={onSelectContainer}
                                    onSelectBlock={onSelectBlock}
                                    isDetailView={isDetailView}
                                />
                            ))}
                        </group>

                        {/* Quay / Asphalt */}
                        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[20, -0.05, 30]} receiveShadow>
                            <planeGeometry args={[300, 400]} />
                            <meshStandardMaterial color="#1e1e24" roughness={0.9} metalness={0.1} />
                        </mesh>

                        {/* Quay Lines (simplified) */}
                        <gridHelper args={[400, 40, "#444", "#222"]} position={[20, 0.01, 30]} rotation={[0, 0, 0]} />
                    </group>

                    {/* Water Surface */}
                    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -2, 0]}>
                        <planeGeometry args={[10000, 10000]} />
                        <meshStandardMaterial color="#005b96" transparent opacity={0.6} roughness={0.1} />
                    </mesh>

                    <ContactShadows opacity={0.6} scale={300} blur={2} far={20} />
                </Suspense>
            </Canvas>

            {!isDetailView && (
                <div className="yard-legend">
                    <span>Survolez un conteneur pour l'inspecter</span>
                    <span>Cliquez sur un bloc pour l'isoler</span>
                </div>
            )}

            <style jsx>{`
        .yard-legend {
          position: absolute;
          bottom: 20px;
          right: 20px;
          background: rgba(0, 0, 0, 0.7);
          padding: 10px 15px;
          border-radius: 8px;
          border: 1px solid rgba(255, 255, 255, 0.1);
          color: white;
          font-size: 0.8rem;
          display: flex;
          flex-direction: column;
          gap: 5px;
          pointer-events: none;
        }
      `}</style>
        </div>
    );
};

export default Yard3D;
