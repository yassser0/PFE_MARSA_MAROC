import React, { useRef, useState } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Text } from '@react-three/drei';

function getContainerColor(details) {
  if (!details) return '#2ca02c';
  const type = (details.type || '').toUpperCase();
  if (type.includes('REEFER') || type.includes('EMPTY')) return '#1e90ff';
  if (type.includes('HAZARD') || type.includes('DGR')) return '#d62728';
  if (details.departure_time) {
    const dep = new Date(details.departure_time);
    const now = new Date();
    if (!isNaN(dep) && (dep - now) < 2 * 60 * 60 * 1000) return '#f4c430';
  }
  return '#2ca02c';
}

function ContainerBox({ position, color, label, details, highlight, onClick }) {
  const [hov, setHov] = useState(false);
  return (
    <mesh
      position={position}
      scale={hov ? [1.08, 1.12, 1.08] : [1, 1, 1]}
      castShadow
      onPointerOver={(e) => { e.stopPropagation(); setHov(true); document.body.style.cursor = 'pointer'; }}
      onPointerOut={() => { setHov(false); document.body.style.cursor = 'default'; }}
      onClick={(e) => { e.stopPropagation(); onClick && onClick({ label, details }); }}
    >
      <boxGeometry args={[details?.size === 40 ? 1.45 : 0.75, 0.83, 1.25]} />
      <meshStandardMaterial
        color={highlight ? '#00fdff' : color}
        emissive={highlight ? '#00fdff' : (hov ? '#fff' : color)}
        emissiveIntensity={hov ? 0.4 : (highlight ? 0.6 : 0.12)}
        roughness={0.3}
        metalness={0.5}
      />
    </mesh>
  );
}

// Row / Bay axis labels
function AxisLabel({ position, text }) {
  return (
    <Text position={position} fontSize={0.7} color="#556677" anchorX="center">
      {text}
    </Text>
  );
}

export default function BlockDetail3D({ yardData, selectedBlock, searchQuery }) {
  const [selected, setSelected] = useState(null);

  if (!yardData) return null;

  const blockData = yardData.blocks.find((b) => b.block_id === selectedBlock);
  if (!blockData) return (
    <div className="view-placeholder">Sélectionnez un bloc dans la barre ci-dessus.</div>
  );

  const maxBays  = yardData.n_bays  || 10;
  const maxRows  = yardData.n_rows  || 3;
  const maxH     = yardData.max_height || 4;

  const containers = [];
  blockData.stacks.forEach((stack) => {
    stack.slots?.forEach((slot) => {
      if (!slot.is_free) {
        const details   = slot.container_details;
        const color     = getContainerColor(details);
        const rowX      = (stack.row - 1) * 2.5 + 0.375;
        const bayZ      = (stack.bay - 1) * 1.5 + 0.6;
        const tierY     = (slot.tier - 1) * 0.9 + 0.425;
        const locStr    = details?.location || '';
        const highlight = searchQuery && (
          searchQuery === slot.container_id || searchQuery === locStr
        );
        containers.push(
          <ContainerBox
            key={`${stack.bay}-${stack.row}-${slot.tier}`}
            position={[rowX, tierY, bayZ]}
            color={color}
            label={slot.container_id}
            details={details}
            highlight={highlight}
            onClick={setSelected}
          />
        );
      }
    });
  });

  // Row labels
  const rowLabels = Array.from({ length: maxRows }, (_, i) => (
    <AxisLabel key={`r${i}`} position={[i * 2.5 + 0.375, -0.5, -1]} text={`R${i + 1}`} />
  ));

  // Bay labels
  const bayLabels = Array.from({ length: maxBays }, (_, i) => (
    <AxisLabel key={`b${i}`} position={[-1.2, -0.5, i * 1.5 + 0.6]} text={`B${i + 1}`} />
  ));

  const camX = maxRows * 1.4;
  const camY = maxH * 2.5;
  const camZ = maxBays * 2.2;

  return (
    <div className="canvas-wrapper" style={{ flex: 1, position: 'relative' }}>

      {selected && (
        <div className="container-popup" onClick={() => setSelected(null)}>
          <button className="popup-close" onClick={() => setSelected(null)}>✕</button>
          <div className="popup-id">{selected.label}</div>
          {selected.details ? (
            <table className="popup-table">
              <tbody>
                {[
                  ['Type', selected.details.type],
                  ['Taille', `${selected.details.size} ft`],
                  ['Poids', `${selected.details.weight} t`],
                  ['Destination', selected.details.destination || '—'],
                  ['Départ', selected.details.departure_time || '—'],
                  ['Priorité', selected.details.priority || '—'],
                  ['Localisation', selected.details.location],
                ].map(([k, v]) => v != null ? (
                  <tr key={k}>
                    <td className="popup-key">{k}</td>
                    <td className="popup-val">{v}</td>
                  </tr>
                ) : null)}
              </tbody>
            </table>
          ) : <p style={{ color: '#8b949e' }}>Pas de détails.</p>}
          <div className="popup-hint">Cliquer pour fermer</div>
        </div>
      )}

      {/* Stats strip */}
      <div className="block-stats-row">
        <div className="block-stat"><span>Bloc</span><strong>{blockData.block_id}</strong></div>
        <div className="block-stat"><span>Occupation</span><strong style={{
          color: blockData.occupancy >= 0.8 ? '#d62728' : blockData.occupancy >= 0.5 ? '#ff7f0e' : '#2ca02c'
        }}>{(blockData.occupancy * 100).toFixed(1)}%</strong></div>
        <div className="block-stat"><span>Bays</span><strong>{maxBays}</strong></div>
        <div className="block-stat"><span>Rangées</span><strong>{maxRows}</strong></div>
        <div className="block-stat"><span>Niveaux max</span><strong>{maxH}</strong></div>
      </div>

      <Canvas
        shadows
        camera={{ position: [camX, camY, camZ], fov: 50 }}
        style={{ background: 'transparent', flex: 1, height: '420px' }}
      >
        <fog attach="fog" args={['#0a0e17', 30, 120]} />
        <color attach="background" args={['#0a0e17']} />

        <ambientLight intensity={0.5} color="#b0c8ff" />
        <directionalLight position={[15, 25, 15]} intensity={1.5} castShadow color="#fff8e7" />
        <hemisphereLight groundColor="#0a1020" skyColor="#405070" intensity={0.4} />

        <OrbitControls enableDamping dampingFactor={0.1} />

        {/* Ground slab */}
        <mesh receiveShadow rotation={[-Math.PI / 2, 0, 0]} position={[(maxRows * 2.5) / 2, 0, (maxBays * 1.5) / 2]}>
          <planeGeometry args={[maxRows * 2.5 + 4, maxBays * 1.5 + 4]} />
          <meshStandardMaterial color="#1a1f28" roughness={0.95} />
        </mesh>

        {/* Bay dividers */}
        {Array.from({ length: maxBays }).map((_, i) => (
          <mesh key={`div-${i}`} receiveShadow rotation={[-Math.PI / 2, 0, 0]} position={[(maxRows * 2.5) / 2, 0.01, i * 1.5 + 0.6]}>
            <planeGeometry args={[maxRows * 2.5, 1.25]} />
            <meshStandardMaterial color={i % 2 === 0 ? '#1e2530' : '#1a2028'} />
          </mesh>
        ))}

        {/* Grid */}
        <gridHelper args={[80, 40, '#1a2a1a', '#111820']} position={[(maxRows * 2.5) / 2, 0.02, (maxBays * 1.5) / 2]} />

        {/* Axis labels */}
        {rowLabels}
        {bayLabels}

        {/* Block title */}
        <Text
          position={[(maxRows * 2.5) / 2, maxH * 1.1 + 2.5, -2]}
          fontSize={1.2}
          color="#7ac97a"
          anchorX="center"
          outlineWidth={0.05}
          outlineColor="#000"
        >
          {`Bloc ${blockData.block_id}  ·  ${(blockData.occupancy * 100).toFixed(1)}% occupé`}
        </Text>

        {containers}
      </Canvas>

      <div className="canvas-hint">
        🖱️ Orbite · Scroll pour zoomer · Cliquer sur un conteneur pour les détails
      </div>
    </div>
  );
}
