import React, { useRef, useState, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Text, GradientTexture } from '@react-three/drei';
import * as THREE from 'three';

// ---------- Color logic based on container type / priority ----------
function getContainerColor(details) {
  if (!details) return '#2ca02c'; // green - normal
  const type = (details.type || '').toUpperCase();
  if (type.includes('REEFER')) return '#1e90ff';      // blue  - reefer / empty equiv
  if (type.includes('EMPTY')) return '#1e90ff';       // blue  - empty
  if (type.includes('HAZARD') || type.includes('DGR')) return '#d62728'; // red - dangerous
  // Departure time heuristic: if < 2h away = yellow
  if (details.departure_time) {
    const dep = new Date(details.departure_time);
    const now = new Date();
    if (!isNaN(dep) && (dep - now) < 2 * 60 * 60 * 1000) return '#f4c430'; // yellow
  }
  return '#2ca02c'; // default green
}

// ---------- Animated single container box ----------
function ContainerBox({ position, color, label, details, onClick, highlight }) {
  const ref = useRef();
  const [hov, setHov] = useState(false);

  useFrame(() => {
    if (!ref.current) return;
    const targetScale = hov ? 1.12 : 1;
    ref.current.scale.setScalar(
      THREE.MathUtils.lerp(ref.current.scale.x, targetScale, 0.18)
    );
  });

  const emissive = highlight ? '#00fdff' : (hov ? '#ffffff' : color);

  return (
    <mesh
      ref={ref}
      position={position}
      castShadow
      onPointerOver={(e) => { e.stopPropagation(); setHov(true); document.body.style.cursor = 'pointer'; }}
      onPointerOut={() => { setHov(false); document.body.style.cursor = 'default'; }}
      onClick={(e) => { e.stopPropagation(); onClick && onClick({ label, details }); }}
    >
      {/* 20ft = 0.75 wide, 40ft = 1.5 wide, height 0.85, depth 1.3 */}
      <boxGeometry args={[details?.size === 40 ? 1.45 : 0.75, 0.83, 1.25]} />
      <meshStandardMaterial
        color={highlight ? '#00fdff' : color}
        emissive={emissive}
        emissiveIntensity={hov ? 0.45 : (highlight ? 0.6 : 0.12)}
        roughness={0.3}
        metalness={0.5}
      />
    </mesh>
  );
}

// ---------- Ground / Tarmac ----------
function YardGround() {
  return (
    <mesh receiveShadow rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.01, 0]}>
      <planeGeometry args={[300, 300]} />
      <meshStandardMaterial color="#1a1f28" roughness={0.95} />
    </mesh>
  );
}

// ---------- Water / Quay area ----------
function WaterArea() {
  const ref = useRef();
  useFrame(({ clock }) => {
    if (ref.current) ref.current.material.opacity = 0.72 + Math.sin(clock.elapsedTime * 0.5) * 0.05;
  });
  return (
    <mesh ref={ref} rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.03, -60]}>
      <planeGeometry args={[300, 80]} />
      <meshStandardMaterial color="#0a3060" transparent opacity={0.72} roughness={0.1} metalness={0.3} />
    </mesh>
  );
}

// ---------- Quay wall ----------
function QuayWall() {
  return (
    <mesh position={[0, 0.5, -22]} castShadow>
      <boxGeometry args={[300, 1.2, 1]} />
      <meshStandardMaterial color="#3a3a3a" roughness={0.9} />
    </mesh>
  );
}

// ---------- Road / Lane ----------
function Road({ from, to, width = 4 }) {
  const [fx, fz] = from;
  const [tx, tz] = to;
  const cx = (fx + tx) / 2;
  const cz = (fz + tz) / 2;
  const len = Math.sqrt((tx - fx) ** 2 + (tz - fz) ** 2);
  const angle = Math.atan2(tz - fz, tx - fx);
  return (
    <mesh rotation={[-Math.PI / 2, 0, angle]} position={[cx, 0.01, cz]} receiveShadow>
      <planeGeometry args={[len, width]} />
      <meshStandardMaterial color="#252830" roughness={0.95} />
    </mesh>
  );
}

// ---------- STS Crane (simplified T-shape) ----------
function Crane({ position }) {
  const [px, py, pz] = position;
  return (
    <group position={[px, py, pz]}>
      {/* Legs */}
      {[-3, 3].map((dx) => (
        <mesh key={dx} position={[dx, 8, 0]} castShadow>
          <boxGeometry args={[0.5, 16, 0.5]} />
          <meshStandardMaterial color="#ff8c00" roughness={0.6} metalness={0.6} />
        </mesh>
      ))}
      {/* Horizontal boom */}
      <mesh position={[0, 16, 0]} castShadow>
        <boxGeometry args={[20, 0.5, 0.5]} />
        <meshStandardMaterial color="#ff8c00" roughness={0.6} metalness={0.6} />
      </mesh>
      {/* Trolley */}
      <mesh position={[0, 14, 0]} castShadow>
        <boxGeometry args={[1.5, 1, 1.5]} />
        <meshStandardMaterial color="#cc6600" roughness={0.4} metalness={0.7} />
      </mesh>
      {/* Spreader cable */}
      <mesh position={[0, 10.5, 0]}>
        <boxGeometry args={[0.1, 7, 0.1]} />
        <meshStandardMaterial color="#888" />
      </mesh>
      {/* Spreader bar */}
      <mesh position={[0, 7, 0]}>
        <boxGeometry args={[4, 0.2, 1.5]} />
        <meshStandardMaterial color="#ffaa00" roughness={0.4} metalness={0.8} />
      </mesh>
    </group>
  );
}

// ---------- Gate structure ----------
function Gate({ position }) {
  const [px, py, pz] = position;
  return (
    <group position={[px, py, pz]}>
      {/* Gate pillars */}
      {[-5, 5].map((dx) => (
        <mesh key={dx} position={[dx, 4, 0]} castShadow>
          <boxGeometry args={[1, 8, 1]} />
          <meshStandardMaterial color="#445566" roughness={0.7} />
        </mesh>
      ))}
      <mesh position={[0, 8, 0]}>
        <boxGeometry args={[12, 0.5, 1]} />
        <meshStandardMaterial color="#445566" roughness={0.7} />
      </mesh>
      <Text position={[0, 9.5, 0]} fontSize={1.5} color="#00fdff" anchorX="center">GATE</Text>
      <Text position={[0, 7.5, 0]} fontSize={0.8} color="#ffcc00" anchorX="center">TC3 CASABLANCA</Text>
    </group>
  );
}

// ---------- Port lamp post ----------
function LampPost({ position }) {
  return (
    <group position={position}>
      <mesh position={[0, 6, 0]}>
        <cylinderGeometry args={[0.1, 0.15, 12, 6]} />
        <meshStandardMaterial color="#444" />
      </mesh>
      <mesh position={[0, 12.2, 0]}>
        <boxGeometry args={[2, 0.2, 0.3]} />
        <meshStandardMaterial color="#555" />
      </mesh>
      <pointLight position={[0, 12, 0]} intensity={30} distance={25} color="#ffe8a0" />
    </group>
  );
}

// ---------- Block occupancy label ----------
function BlockLabel({ position, blockId, occupancy }) {
  const pct = (occupancy * 100).toFixed(0);
  const col = occupancy >= 0.8 ? '#d62728' : occupancy >= 0.5 ? '#ff7f0e' : '#2ca02c';
  return (
    <group position={position}>
      <Text
        position={[0, 0, 0]}
        fontSize={1.8}
        color="white"
        anchorX="center"
        outlineWidth={0.06}
        outlineColor="#000"
      >
        {`Bloc ${blockId}`}
      </Text>
      <Text
        position={[0, -2.2, 0]}
        fontSize={1.2}
        color={col}
        anchorX="center"
        outlineWidth={0.05}
        outlineColor="#000"
      >
        {`${pct}% occupé`}
      </Text>
    </group>
  );
}

// ---------- Main GlobalView3D component ----------
export default function GlobalView3D({ yardData, searchQuery, onBlockClick }) {
  const [selectedContainer, setSelectedContainer] = useState(null);

  const handleContainerClick = (info) => setSelectedContainer(info);

  // TC3 block layout: 2 columns × 2 rows with road spacing
  const BLOCK_OFFSETS = useMemo(() => ({
    A: [0,   0],
    B: [35,  0],
    C: [0,   35],
    D: [35,  35],
    E: [70,  0],
    F: [70,  35],
  }), []);

  if (!yardData) {
    return (
      <div className="canvas-wrapper" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <p style={{ color: '#8b949e' }}>Chargement des données du yard…</p>
      </div>
    );
  }

  // Compute a reasonable camera start position
  const nBlocks = yardData.blocks.length;
  const camDist = Math.max(60, nBlocks * 18);

  return (
    <div className="canvas-wrapper" style={{ position: 'relative', flex: 1, overflow: 'hidden' }}>

      {/* Container detail popup */}
      {selectedContainer && (
        <div className="container-popup" onClick={() => setSelectedContainer(null)}>
          <button className="popup-close" onClick={() => setSelectedContainer(null)}>✕</button>
          <div className="popup-id">{selectedContainer.label}</div>
          {selectedContainer.details ? (
            <table className="popup-table">
              <tbody>
                {[
                  ['Type', selectedContainer.details.type],
                  ['Taille', `${selectedContainer.details.size} ft`],
                  ['Poids', `${selectedContainer.details.weight} t`],
                  ['Destination', selectedContainer.details.destination || '—'],
                  ['Départ', selectedContainer.details.departure_time || '—'],
                  ['Priorité', selectedContainer.details.priority || '—'],
                  ['Localisation', selectedContainer.details.location],
                ].map(([k, v]) => v != null ? (
                  <tr key={k}>
                    <td className="popup-key">{k}</td>
                    <td className="popup-val">{v}</td>
                  </tr>
                ) : null)}
              </tbody>
            </table>
          ) : <p style={{ color: '#8b949e' }}>Pas de détails disponibles.</p>}
          <div className="popup-hint">Cliquer pour fermer</div>
        </div>
      )}

      {/* Legend */}
      <div className="yard-legend">
        <span className="leg-item" style={{ color: '#2ca02c' }}>● Normal</span>
        <span className="leg-item" style={{ color: '#f4c430' }}>● Pickup imminent</span>
        <span className="leg-item" style={{ color: '#d62728' }}>● Dangereux</span>
        <span className="leg-item" style={{ color: '#1e90ff' }}>● Reefer / Vide</span>
        <span className="leg-item" style={{ color: '#00fdff' }}>● Trouvé</span>
      </div>

      <Canvas
        shadows
        camera={{ position: [camDist, camDist * 0.7, camDist * 1.1], fov: 45 }}
        gl={{ antialias: true, alpha: false }}
        style={{ background: 'transparent', width: '100%', height: '100%' }}
      >
        {/* Fog for depth */}
        <fog attach="fog" args={['#0a0e17', 80, 280]} />

        {/* Sky gradient via background */}
        <color attach="background" args={['#0a0e17']} />

        {/* Lighting – port atmosphere */}
        <ambientLight intensity={0.35} color="#b0c8ff" />
        <directionalLight
          position={[60, 80, 40]}
          intensity={1.6}
          color="#fff8e7"
          castShadow
          shadow-mapSize-width={2048}
          shadow-mapSize-height={2048}
          shadow-camera-far={300}
          shadow-camera-left={-100}
          shadow-camera-right={100}
          shadow-camera-top={100}
          shadow-camera-bottom={-100}
        />
        <hemisphereLight groundColor="#0a1020" skyColor="#405070" intensity={0.5} />

        <OrbitControls
          makeDefault
          enableDamping
          dampingFactor={0.08}
          maxPolarAngle={Math.PI / 2.1}
          minDistance={10}
          maxDistance={200}
        />

        {/* Ground */}
        <YardGround />

        {/* Water / Quay */}
        <WaterArea />
        <QuayWall />

        {/* STS Cranes along waterfront */}
        {[10, 35, 60, 85].map((x) => (
          <Crane key={x} position={[x - 10, 0, -12]} />
        ))}

        {/* Gate */}
        <Gate position={[-20, 0, 75]} />

        {/* Main roads */}
        <Road from={[-30, 80]} to={[120, 80]} width={7} />  {/* horizontal front road */}
        <Road from={[-30, -15]} to={[120, -15]} width={6} /> {/* quayside road */}
        <Road from={[17, -15]} to={[17, 80]} width={5} />   {/* inter-block lane A/B */}
        <Road from={[52, -15]} to={[52, 80]} width={5} />   {/* inter-block lane B/C */}
        <Road from={[-5, 17]} to={[120, 17]} width={4} />   {/* intra-block cross-lane */}
        <Road from={[-5, 52]} to={[120, 52]} width={4} />

        {/* Lamp posts */}
        {[
          [16, 0, 18], [16, 0, 52], [51, 0, 18], [51, 0, 52],
          [16, 0, -5], [51, 0, -5], [16, 0, 75], [51, 0, 75],
        ].map((p, i) => <LampPost key={i} position={p} />)}

        {/* --- Blocks from API --- */}
        {yardData.blocks.map((block, bi) => {
          const offset = BLOCK_OFFSETS[block.block_id] || [bi * 35, 0];
          const [ox, oz] = offset;

          const maxRows  = yardData.n_rows  || 3;
          const maxBays  = yardData.n_bays  || 10;

          // Block footprint for floor slab
          const footW = maxRows  * 2.5 + 1;
          const footD = maxBays  * 1.5 + 1;

          const containers = [];

          block.stacks.forEach((stack) => {
            stack.slots?.forEach((slot) => {
              if (!slot.is_free) {
                const details  = slot.container_details;
                const color    = getContainerColor(details);
                const rowX     = (stack.row - 1) * 2.5 + 0.375;
                const bayZ     = (stack.bay - 1) * 1.5 + 0.6;
                const tierY    = (slot.tier - 1) * 0.9 + 0.425;

                const locStr   = details?.location || '';
                const highlight = searchQuery && (
                  searchQuery === slot.container_id || searchQuery === locStr
                );

                containers.push(
                  <ContainerBox
                    key={`${block.block_id}-${stack.bay}-${stack.row}-${slot.tier}`}
                    position={[ox + rowX, tierY, oz + bayZ]}
                    color={color}
                    label={slot.container_id}
                    details={details}
                    highlight={highlight}
                    onClick={handleContainerClick}
                  />
                );
              }
            });
          });

          return (
            <group key={block.block_id}>
              {/* Block tarmac slab */}
              <mesh
                receiveShadow
                rotation={[-Math.PI / 2, 0, 0]}
                position={[ox + footW / 2 - 0.5, 0.005, oz + footD / 2 - 0.5]}
              >
                <planeGeometry args={[footW, footD]} />
                <meshStandardMaterial color="#1e2530" roughness={0.92} />
              </mesh>

              {/* Block boundary lines */}
              <lineSegments position={[ox + footW / 2 - 0.5, 0.02, oz + footD / 2 - 0.5]}>
                <edgesGeometry args={[new THREE.BoxGeometry(footW, 0.01, footD)]} />
                <lineBasicMaterial color="#2a4a2a" linewidth={1} />
              </lineSegments>

              {/* Containers */}
              {containers}

              {/* Overhead block label */}
              <BlockLabel
                position={[ox + footW / 2 - 0.5, yardData.max_height * 1.1 + 4, oz + footD / 2 - 0.5]}
                blockId={block.block_id}
                occupancy={block.occupancy}
              />

              {/* "Inspect" clickable plane */}
              <mesh
                rotation={[-Math.PI / 2, 0, 0]}
                position={[ox + footW / 2 - 0.5, 0.03, oz + footD / 2 - 0.5]}
                onClick={() => onBlockClick(block.block_id)}
              >
                <planeGeometry args={[footW, footD]} />
                <meshStandardMaterial transparent opacity={0} depthWrite={false} />
              </mesh>
            </group>
          );
        })}

        {/* Grid overlay */}
        <gridHelper args={[300, 60, '#141a24', '#0d1119']} position={[50, 0, 30]} />
      </Canvas>

      <div className="canvas-hint">
        🖱️ Cliquer + glisser · Scroll pour zoomer · Cliquer un conteneur pour les détails · Cliquer le sol d'un bloc pour l'inspecter
      </div>
    </div>
  );
}
