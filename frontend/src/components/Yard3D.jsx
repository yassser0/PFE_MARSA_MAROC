import React, { Suspense } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, PerspectiveCamera, Environment, ContactShadows, Sky, Float } from '@react-three/drei';
import Block from './Block';
import Crane from './Crane';

const Yard3D = ({ data, onSelectContainer, onSelectBlock, isDetailView, searchQuery }) => {
    if (!data) return <div className="loading-overlay">Chargement des données...</div>;

    return (
        <div style={{ width: '100%', height: '100%', position: 'relative' }}>
            <Canvas shadows gl={{ antialias: true, stencil: false, depth: true }} dpr={[1, 2]}>
                {/* Global Atmosphere */}
                <color attach="background" args={['#0a0b0d']} />
                <fog attach="fog" args={['#0a0b0d', 10, 150]} />

                <Suspense fallback={null}>
                    <PerspectiveCamera makeDefault position={isDetailView ? [15, 15, 15] : [40, 30, 45]} fov={40} />
                    <OrbitControls
                        makeDefault
                        target={isDetailView ? [4, 0, 6] : [11, 0, 15]}
                        minPolarAngle={0}
                        maxPolarAngle={Math.PI / 2.1}
                        enableDamping={true}
                    />

                    <Sky distance={1000} sunPosition={[0, -1, 0.5]} inclination={0.6} azimuth={0.25} turbidity={10} rayleigh={2} />
                    <ambientLight intensity={0.2} />

                    {/* Main Industrial Lighting */}
                    <directionalLight
                        position={[-50, 100, 50]}
                        intensity={3}
                        castShadow
                        shadow-mapSize={[4096, 4096]}
                        shadow-camera-left={-100}
                        shadow-camera-right={100}
                        shadow-camera-top={100}
                        shadow-camera-bottom={-100}
                    />
                    <pointLight position={[50, 20, 50]} intensity={1.5} color="#ffd27d" />

                    <Environment preset="night" />

                    {/* Terminal Group - Rotated to match TC3 Photo */}
                    <group rotation={[0, -Math.PI / 6, 0]}>
                        <group position={[0, 0, 0]}>
                            {data.blocks.map((block) => (
                                <group key={block.block_id}>
                                    <Block
                                        block={block}
                                        maxHeight={data.max_height}
                                        onSelectContainer={onSelectContainer}
                                        onSelectBlock={onSelectBlock}
                                        isDetailView={isDetailView}
                                        searchQuery={searchQuery}
                                    />
                                    {/* RTG Crane over each block */}
                                    {(!isDetailView || data.blocks.length === 1) && (
                                        <Crane
                                            position={[block.x + block.width / 2 - 1.2, 0, block.y + block.length / 2]}
                                            width={block.width + 4}
                                            length={block.length}
                                        />
                                    )}
                                </group>
                            ))}
                        </group>

                        {/* Realistic Yard Foundation (Asphalt + Quay) */}
                        <group position={[11, 0, 15]}>
                            {/* Asphalt Surface */}
                            <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.05, 0]} receiveShadow>
                                <planeGeometry args={[120, 150]} />
                                <meshStandardMaterial color="#111115" roughness={0.8} metalness={0.1} />
                            </mesh>

                            {/* Quay Wall (Transitions to water) */}
                            <mesh position={[-60, -2.5, 0]} receiveShadow>
                                <boxGeometry args={[0.5, 5, 150]} />
                                <meshStandardMaterial color="#2c2c2c" />
                            </mesh>

                            {/* Ground Markings */}
                            <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.01, 0]}>
                                <planeGeometry args={[115, 0.2]} />
                                <meshStandardMaterial color="#f1c40f" transparent opacity={0.4} />
                            </mesh>
                            <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.01, 20]}>
                                <planeGeometry args={[115, 0.2]} />
                                <meshStandardMaterial color="#f1c40f" transparent opacity={0.4} />
                            </mesh>
                        </group>

                        {/* Visual Depth Grids */}
                        <gridHelper args={[150, 30, "#222", "#111"]} position={[11, 0, 15]} rotation={[0, 0, 0]} />
                    </group>

                    {/* Water Surface - Deep and Reflective */}
                    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -4.8, 0]} receiveShadow>
                        <planeGeometry args={[1000, 1000]} />
                        <meshStandardMaterial color="#001b2e" roughness={0.3} metalness={0.9} />
                    </mesh>

                    {/* Lighting Poles for Grounding */}
                    {[[-40, 0, -20], [-40, 0, 50], [60, 0, -20], [60, 0, 50]].map((pos, i) => (
                        <group key={i} position={pos}>
                            <mesh position={[0, 10, 0]}>
                                <cylinderGeometry args={[0.2, 0.3, 20]} />
                                <meshStandardMaterial color="#333" />
                            </mesh>
                            <mesh position={[0, 20, 0.5]} rotation={[Math.PI / 4, 0, 0]}>
                                <boxGeometry args={[1, 0.5, 2]} />
                                <meshStandardMaterial color="#fff" emissive="#fff" emissiveIntensity={2} />
                            </mesh>
                            <pointLight position={[0, 19, 1]} intensity={0.5} distance={30} color="#fff" />
                        </group>
                    ))}

                    <ContactShadows opacity={0.6} scale={200} blur={2} far={10} resolution={1024} />
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
