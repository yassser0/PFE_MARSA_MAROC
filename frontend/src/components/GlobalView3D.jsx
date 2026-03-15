import React, { useMemo, useState, Suspense } from 'react'
import { Canvas } from '@react-three/fiber'
import { 
  OrbitControls, 
  PerspectiveCamera, 
  Environment, 
  ContactShadows, 
  Sky, 
  Text,
  Grid,
  useGLTF,
  Clone,
  useHelper
} from '@react-three/drei'
import { useThree, useFrame } from '@react-three/fiber'
import * as THREE from 'three'

// --- Constants & Palettes ---
const STATUS_PALETTE = {
  'normal': '#3fb950',        // Green
  'scheduled': '#d29922',     // Yellow
  'urgent': '#f85149',        // Red
  'empty': '#58a6ff',         // Blue
  'default': '#8b949e'
}

function getStatusColor(slot) {
  const details = slot.container_details;
  if (!details) return STATUS_PALETTE.default;
  if (details.type === 'export') return STATUS_PALETTE.scheduled;
  if (details.weight > 25) return STATUS_PALETTE.urgent;
  if (details.type === 'empty') return STATUS_PALETTE.empty;
  return STATUS_PALETTE.normal;
}

// --- Dynamic Model Loader (Blender Integration) ---

/**
 * Container component that can use a Blender model or a Box fallback.
 */
function ContainerModel({ position, color, data, onSelect, isMatch, opacity = 1.0 }) {
  const [hovered, setHover] = useState(false)
  
  if (opacity <= 0) return null; // Fully hidden

  return (
    <group position={position}>
      <mesh 
        castShadow 
        receiveShadow 
        onPointerOver={(e) => { e.stopPropagation(); setHover(true); document.body.style.cursor = 'pointer' }} 
        onPointerOut={() => { setHover(false); document.body.style.cursor = 'auto' }} 
        onClick={(e) => { e.stopPropagation(); onSelect(data) }}
      >
        <boxGeometry args={[2.5, 2.5, 6.1]} />
        <meshStandardMaterial 
          color={isMatch ? '#00fdff' : color} 
          metalness={0.6} 
          roughness={0.4}
          transparent={opacity < 1}
          opacity={opacity}
          depthWrite={opacity >= 1} // CRITICAL: disable depthWrite for transparent objects
          emissive={isMatch || hovered ? '#00fdff' : 'black'}
          emissiveIntensity={isMatch ? 0.6 : hovered ? 0.3 : 0}
        />
      </mesh>
    </group>
  )
}

/**
 * RTG Crane component (Blender placeholders included)
 */
function RTGModel({ position }) {
  // const { scene } = useGLTF('/models/rtg_crane.glb', true)
  
  return (
    <group position={position}>
      {/* Procedural fallback for now */}
      <mesh position={[-6, 6, 0]} castShadow> <boxGeometry args={[0.8, 12, 1.2]} /> <meshStandardMaterial color="#ebc034" /> </mesh>
      <mesh position={[6, 6, 0]} castShadow> <boxGeometry args={[0.8, 12, 1.2]} /> <meshStandardMaterial color="#ebc034" /> </mesh>
      <mesh position={[0, 12, 0]} castShadow> <boxGeometry args={[13, 1, 3]} /> <meshStandardMaterial color="#ebc034" /> </mesh>
      <mesh position={[0, 11, 0]}> <boxGeometry args={[2, 0.5, 2]} /> <meshStandardMaterial color="#333" /> </mesh>
    </group>
  )
}

/**
 * Camera Focus Controller (Fly-To)
 */
function CameraFocus({ targetPos }) {
  const { camera, controls } = useThree()
  
  useFrame((state, delta) => {
    if (!targetPos || !controls) return

    // Interpolate target
    const targetVec = new THREE.Vector3(...targetPos)
    controls.target.lerp(targetVec, 0.1)
    
    // Interpolate camera position (offset for viewing angle)
    const desiredCamPos = new THREE.Vector3(
      targetVec.x + 30,
      targetVec.y + 30,
      targetVec.z + 30
    )
    camera.position.lerp(desiredCamPos, 0.05)
    
    controls.update()
  })

  return null
}

// --- Main Environment ---

function SceneContent({ yardData, searchQuery, onSelectContainer, visibleRow }) {
  return (
    <>
      <Sky inclination={0.1} distance={450000} />
      <Environment preset="night" />
      <ambientLight intensity={0.5} />
      <directionalLight 
        position={[20, 50, 20]} 
        intensity={1.2} 
        castShadow 
        shadow-mapSize={[2048, 2048]} 
      />

      {/* Ground calculated dynamically based on block layout */}
      {yardData?.blocks?.length > 0 && (() => {
        // Find bounds of all blocks
        let minX = Infinity, maxX = -Infinity, minZ = Infinity, maxZ = -Infinity;
        
        yardData.blocks.forEach(b => {
          // Block origin is at its center (usually), but let's assume its extent
          const halfW = b.width / 2;
          const halfL = b.length / 2;
          minX = Math.min(minX, b.x - halfW);
          maxX = Math.max(maxX, b.x + halfW);
          minZ = Math.min(minZ, b.y - halfL);
          maxZ = Math.max(maxZ, b.y + halfL);
        });

        const width = maxX - minX + 25; // Adjusted margin
        const length = maxZ - minZ + 25;
        const centerX = (maxX + minX) / 2;
        const centerZ = (maxZ + minZ) / 2;

        return (
          <group position={[centerX, -0.04, centerZ]}>
            <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
              <planeGeometry args={[width, length]} />
              <meshStandardMaterial color="#050505" roughness={0.7} metalness={0.8} />
            </mesh>
            <Grid
              position={[0, 0.01, 0]}
              args={[Math.max(width, length) * 2, Math.max(width, length) * 2]}
              cellSize={2}
              cellThickness={1}
              cellColor="#111"
              sectionSize={10}
              sectionThickness={1.5}
              sectionColor="#222"
              fadeDistance={80}
              fadeStrength={1}
            />
          </group>
        )
      })()}

      {/* Blocks & Assets */}
      {yardData?.blocks?.map((block) => (
        <group key={block.block_id} position={[block.x, 0, block.y]}>
          {/* Label positioned above the block for clear identification */}
          <Text
            position={[0, 15, 0]}
            rotation={[0, 0, 0]}
            fontSize={8}
            color="#FFFFFF"
            anchorX="center"
            anchorY="middle"
            outlineWidth={0.5}
            outlineColor="#000000"
          >
            {block.block_id}
          </Text>

          <RTGModel position={[0, 0, 0]} />

          {block.stacks.map((stack) => {
            // Force visibility if stack contains the searched container
            const hasSearchMatch = searchQuery && stack.slots.some(s => 
              !s.is_free && (s.container_id === searchQuery || s.container_details?.location === searchQuery)
            );
            const isTargetRow = visibleRow === 0 || stack.row === visibleRow || hasSearchMatch;
            
            if (!isTargetRow) return null; 

            return (
              <group key={`${block.block_id}-${stack.row}-${stack.bay}`} position={[
                (stack.row - 1 - yardData.n_rows/2 + 0.5) * 2.8, 
                0, 
                (stack.bay - 1 - yardData.n_bays/2 + 0.5) * 6.4
              ]}>
                {stack.slots.map((slot) => {
                  if (slot.is_free) return null;
                  const isMatch = searchQuery && (slot.container_id === searchQuery || slot.container_details?.location === searchQuery)
                  return (
                    <ContainerModel 
                      key={slot.container_id}
                      position={[0, (slot.tier - 1) * 2.6 + 1.3, 0]}
                      color={getStatusColor(slot)}
                      data={{ id: slot.container_id, ...slot.container_details }}
                      onSelect={onSelectContainer}
                      isMatch={isMatch}
                      opacity={1.0} // Keep fully opaque for target row
                    />
                  )
                })}
              </group>
            )
          })}
        </group>
      ))}
      <ContactShadows opacity={0.6} scale={500} blur={2} far={10} color="#000000" />
    </>
  )
}

// --- Entry Point ---

export default function GlobalView3D({ yardData, searchQuery, onInspectBlock, onSelectContainer }) {
  const [visibleRow, setVisibleRow] = useState(0) // 0 means all rows visible
  
  const stats = useMemo(() => {
    if (!yardData) return { occupancy: 0, count: 0, alerts: 0 }
    const totalSlots = yardData.n_blocks * yardData.n_bays * yardData.n_rows * yardData.max_height
    let filled = 0
    yardData.blocks.forEach(b => {
      b.stacks.forEach(s => {
        s.slots.forEach(sl => { if (!sl.is_free) filled++ })
      })
    })
    return {
      occupancy: totalSlots > 0 ? ((filled / totalSlots) * 100).toFixed(1) : 0,
      count: filled,
      alerts: filled > totalSlots * 0.8 ? 1 : 0
    }
  }, [yardData])

  // Find target position for Fly-To
  const targetContainerPos = useMemo(() => {
    if (!searchQuery || !yardData) return null
    
    for (const block of yardData.blocks) {
      for (const stack of block.stacks) {
        for (const slot of stack.slots) {
          if (!slot.is_free && (slot.container_id === searchQuery || slot.container_details?.location === searchQuery)) {
            return [
              block.x + (stack.row - 1 - yardData.n_rows/2 + 0.5) * 2.8,
              (slot.tier - 1) * 2.6 + 1.3,
              block.y + (stack.bay - 1 - yardData.n_bays/2 + 0.5) * 6.4
            ]
          }
        }
      }
    }
    return null
  }, [searchQuery, yardData])

  if (!yardData) return <div className="loading-spinner">Initialisation du Yard...</div>

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', background: '#080a0c', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
      {/* Unified Horizontal Header Bar */}
      <div style={{ padding: '15px' }}>
        <div className="detail-header-row glass" style={{ 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'space-between', 
          padding: '12px 25px', 
          borderRadius: '12px',
          gap: '20px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '30px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <label style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '1px' }}>Vue</label>
              <span style={{ color: '#fff', fontSize: '0.9rem', fontWeight: 600 }}>GLOBALE</span>
            </div>

            {/* Row Visibility Tool */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '15px', paddingLeft: '20px', borderLeft: '1px solid var(--border)' }}>
              <label style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '1px' }}>Visibilité Rangées</label>
              <input 
                type="range" 
                min="0" 
                max={yardData.n_rows} 
                value={visibleRow} 
                onChange={(e) => setVisibleRow(parseInt(e.target.value))}
                style={{ width: '120px' }}
              />
              <span style={{ fontSize: '0.8rem', color: 'white', minWidth: '50px' }}>
                {visibleRow === 0 ? 'Toutes' : `R${visibleRow}`}
              </span>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontWeight: 700, textTransform: 'uppercase' }}>Occupation Globale</span>
            <div style={{ width: '150px', height: '6px', background: 'rgba(255,255,255,0.05)', borderRadius: '3px', overflow: 'hidden' }}>
              <div style={{ width: `${stats.occupancy}%`, height: '100%', background: 'var(--accent-cyan)', transition: 'width 0.5s' }} />
            </div>
            <strong style={{ fontSize: '1.1rem', color: 'var(--accent-cyan)' }}>{stats.occupancy}%</strong>
          </div>
        </div>
      </div>

      <Canvas shadows camera={{ position: [80, 60, 100], fov: 40 }}>
        <Suspense fallback={null}>
          <SceneContent 
            yardData={yardData} 
            searchQuery={searchQuery} 
            onSelectContainer={onSelectContainer} 
            visibleRow={visibleRow}
          />
          <CameraFocus targetPos={targetContainerPos} />
          <OrbitControls makeDefault maxPolarAngle={Math.PI / 2.1} minDistance={10} maxDistance={400} />
        </Suspense>
      </Canvas>

      <div className="block-nav-overlay" style={{
        position: 'absolute', bottom: '20px', left: '50%', transform: 'translateX(-50%)',
        display: 'flex', gap: '10px', zIndex: 10
      }}>
        {yardData.blocks.map(b => (
          <button key={b.block_id} className="btn-block-nav glass" onClick={() => onInspectBlock(b.block_id)}>
            FOCUS {b.block_id}
          </button>
        ))}
      </div>
    </div>
  )
}
