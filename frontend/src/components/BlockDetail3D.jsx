import React, { useRef, useState } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Text } from '@react-three/drei';

const CONTAINER_COLOR = '#2ca02c';
const HIGHLIGHT_COLOR = '#00fdff';

function Container({ position, color, hoverText, onClick }) {
  const [hovered, setHovered] = useState(false);

  return (
    <mesh
      position={position}
      scale={hovered ? [1.05, 1.1, 1.05] : [1, 1, 1]}
      onPointerOver={(e) => { e.stopPropagation(); setHovered(true); document.body.style.cursor = 'pointer'; }}
      onPointerOut={() => { setHovered(false); document.body.style.cursor = 'default'; }}
      onClick={(e) => { e.stopPropagation(); onClick && onClick(hoverText); }}
    >
      <boxGeometry args={[0.75, 0.85, 1.2]} />
      <meshStandardMaterial
        color={hovered ? '#ffffff' : color}
        emissive={color}
        emissiveIntensity={hovered ? 0.5 : 0.15}
        roughness={0.25}
        metalness={0.5}
      />
    </mesh>
  );
}

export default function BlockDetail3D({ yardData, selectedBlock, searchQuery }) {
  const [tooltip, setTooltip] = useState(null);

  if (!yardData) return null;

  const blockData = yardData.blocks.find((b) => b.block_id === selectedBlock);
  if (!blockData) return <div className="view-placeholder">Bloc introuvable.</div>;

  const containers = [];

  blockData.stacks.forEach((stack) => {
    stack.slots?.forEach((slot) => {
      if (!slot.is_free) {
        const rowOffset = (stack.row - 1) * 2.5;
        const bayOffset = (stack.bay - 1) * 1.5;
        const tierIdx = slot.tier - 1;
        const details = slot.container_details;

        const hover = `<b>${slot.container_id}</b>${details
          ? `<br/>Type: ${details.type}<br/>Taille: ${details.size}ft<br/>Poids: ${details.weight}t<br/>Départ: ${details.departure_time}<br/>Loc: ${details.location}`
          : ''
        }`;

        const locStr = details?.location || '';
        const isMatch = searchQuery && (
          searchQuery === slot.container_id || searchQuery === locStr
        );

        containers.push(
          <Container
            key={`${stack.bay}-${stack.row}-${slot.tier}`}
            position={[rowOffset + 0.375, tierIdx * 1.0 + 0.425, bayOffset + 0.6]}
            color={isMatch ? HIGHLIGHT_COLOR : CONTAINER_COLOR}
            hoverText={hover}
            onClick={setTooltip}
          />
        );
      }
    });
  });

  const maxBays = yardData.n_bays;
  const maxRows = yardData.n_rows;

  return (
    <div className="canvas-wrapper">
      {tooltip && (
        <div className="tooltip-box" onClick={() => setTooltip(null)}>
          <span className="tooltip-close">✕</span>
          <div dangerouslySetInnerHTML={{ __html: tooltip }} />
        </div>
      )}

      <div className="block-stats-row">
        <div className="block-stat">
          <span>Bloc</span>
          <strong>{blockData.block_id}</strong>
        </div>
        <div className="block-stat">
          <span>Occupation</span>
          <strong>{(blockData.occupancy * 100).toFixed(1)}%</strong>
        </div>
        <div className="block-stat">
          <span>Bays</span>
          <strong>{maxBays}</strong>
        </div>
        <div className="block-stat">
          <span>Rangées</span>
          <strong>{maxRows}</strong>
        </div>
      </div>

      <Canvas
        camera={{ position: [maxRows * 3, yardData.max_height * 2.5, maxBays * 3], fov: 50 }}
        style={{ background: 'transparent', height: '500px' }}
      >
        <ambientLight intensity={0.6} />
        <directionalLight position={[10, 20, 10]} intensity={1.3} />
        <pointLight position={[-5, 10, -5]} intensity={0.3} color="#4488ff" />
        <OrbitControls makeDefault dampingFactor={0.1} />

        {containers}

        {/* Floor grid lines for bays */}
        {Array.from({ length: maxBays }).map((_, bIdx) => (
          <mesh key={`floor-${bIdx}`} position={[(maxRows * 2.5) / 2 - 0.375, 0.01, bIdx * 1.5 + 0.6]} rotation={[-Math.PI / 2, 0, 0]}>
            <planeGeometry args={[maxRows * 2.5, 1.2]} />
            <meshStandardMaterial color="#0d1f0d" transparent opacity={0.6} />
          </mesh>
        ))}

        <gridHelper args={[50, 30, '#1a3a1a', '#0a1a0a']} position={[6, 0, 7]} />

        <Text position={[(maxRows * 2.5) / 2, yardData.max_height + 2, -1]} fontSize={1} color="#7ac97a" anchorX="center">
          {`Bloc ${blockData.block_id} — ${(blockData.occupancy * 100).toFixed(1)}% occupé`}
        </Text>
      </Canvas>

      <div className="canvas-hint">
        🖱️ Orbite · Scroll pour zoomer · Cliquer sur un conteneur pour les détails
      </div>
    </div>
  );
}
