import React, { useRef, useState } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Text } from '@react-three/drei';
import * as THREE from 'three';

const CONTAINER_COLOR = '#2ca02c';
const HIGHLIGHT_COLOR = '#00fdff';
const FLOOR_COLOR = '#1a2a1a';

function Container({ position, color, hoverText, onClick }) {
  const meshRef = useRef();
  const [hovered, setHovered] = useState(false);

  useFrame(() => {
    if (meshRef.current) {
      meshRef.current.scale.y = THREE.MathUtils.lerp(
        meshRef.current.scale.y,
        hovered ? 1.15 : 1.0,
        0.1
      );
    }
  });

  return (
    <mesh
      ref={meshRef}
      position={position}
      onPointerOver={(e) => { e.stopPropagation(); setHovered(true); document.body.style.cursor = 'pointer'; }}
      onPointerOut={() => { setHovered(false); document.body.style.cursor = 'default'; }}
      onClick={(e) => { e.stopPropagation(); onClick && onClick(hoverText); }}
    >
      <boxGeometry args={[0.75, 0.85, 1.2]} />
      <meshStandardMaterial
        color={hovered ? '#ffffff' : color}
        emissive={color}
        emissiveIntensity={hovered ? 0.4 : 0.1}
        roughness={0.3}
        metalness={0.4}
      />
    </mesh>
  );
}

function BlockFloor({ position, width, depth, label }) {
  return (
    <group position={position}>
      <mesh rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[width, depth]} />
        <meshStandardMaterial color={FLOOR_COLOR} transparent opacity={0.5} />
      </mesh>
      <Text
        position={[0, 5, 0]}
        fontSize={1.2}
        color="white"
        anchorX="center"
        anchorY="middle"
        outlineWidth={0.05}
        outlineColor="#000"
      >
        {label}
      </Text>
    </group>
  );
}

export default function GlobalView3D({ yardData, searchQuery, onBlockClick }) {
  const [tooltip, setTooltip] = useState(null);

  if (!yardData) return <div className="view-placeholder">Chargement des données…</div>;

  const handleContainerClick = (text) => setTooltip(text);

  return (
    <div className="canvas-wrapper">
      {tooltip && (
        <div className="tooltip-box" onClick={() => setTooltip(null)}>
          <span className="tooltip-close">✕</span>
          <div dangerouslySetInnerHTML={{ __html: tooltip }} />
        </div>
      )}
      <Canvas
        camera={{ position: [30, 25, 40], fov: 50 }}
        style={{ background: 'transparent' }}
      >
        <ambientLight intensity={0.5} />
        <directionalLight position={[20, 30, 20]} intensity={1.2} castShadow />
        <pointLight position={[-10, 20, -10]} intensity={0.4} color="#4488ff" />
        <OrbitControls makeDefault dampingFactor={0.1} />

        {yardData.blocks.map((block) => {
          const bx = block.x;
          const by = block.y;
          const bw = block.width;
          const bl = block.length;

          const containers = [];

          block.stacks.forEach((stack) => {
            stack.slots?.forEach((slot) => {
              if (!slot.is_free) {
                const rowOffset = (stack.row - 1) * 2.5;
                const bayOffset = (stack.bay - 1) * 1.5;
                const tierIdx = (slot.tier - 1) * 1.0;
                const details = slot.container_details;

                const hover = `<b>${slot.container_id}</b>${details
                  ? `<br/>Type: ${details.type}<br/>Taille: ${details.size}ft<br/>Poids: ${details.weight}t<br/>Départ: ${details.departure_time}<br/>Loc: ${details.location}`
                  : ''
                }`;

                const locStr = details?.location || '';
                const isMatch = searchQuery && (
                  searchQuery === slot.container_id || searchQuery === locStr
                );

                const color = isMatch ? HIGHLIGHT_COLOR : CONTAINER_COLOR;

                containers.push(
                  <Container
                    key={`${block.block_id}-${stack.bay}-${stack.row}-${slot.tier}`}
                    position={[bx + rowOffset + 0.375, tierIdx + 0.425 + 0.01, by + bayOffset + 0.6]}
                    color={color}
                    hoverText={hover}
                    onClick={handleContainerClick}
                  />
                );
              }
            });
          });

          return (
            <group key={block.block_id}>
              <BlockFloor
                position={[bx + bw / 2, 0, by + bl / 2]}
                width={bw}
                depth={bl}
                label={`Bloc ${block.block_id}`}
              />
              {containers}
              {/* Clickable block label for navigation */}
              <mesh
                position={[bx + bw / 2, 0.05, by + bl / 2]}
                rotation={[-Math.PI / 2, 0, 0]}
                onClick={() => onBlockClick(block.block_id)}
              >
                <planeGeometry args={[bw, bl]} />
                <meshStandardMaterial transparent opacity={0} />
              </mesh>
            </group>
          );
        })}

        {/* Grid */}
        <gridHelper args={[200, 50, '#1a2a3a', '#0d1a26']} position={[25, 0, 25]} />
      </Canvas>

      <div className="canvas-hint">
        🖱️ Cliquer + glisser pour pivoter · Scroll pour zoomer · Cliquer sur un conteneur pour les détails
      </div>
    </div>
  );
}
