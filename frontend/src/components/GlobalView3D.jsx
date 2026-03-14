import React, { useMemo, useState, Suspense } from 'react'
import { Canvas } from '@react-three/fiber'
import { 
  OrbitControls, 
  PerspectiveCamera, 
  Environment, 
  ContactShadows, 
  Sky, 
  Text,
  useGLTF,
  Clone
} from '@react-three/drei'
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
function ContainerModel({ position, color, data, onSelect, isMatch }) {
  const [hovered, setHover] = useState(false)
  
  // Placeholder for Blender model integration
  // To use a blender model: 
  // 1. Uncomment the useGLTF line below
  // 2. Put your .glb file in /public/models/iso_container.glb
  // const { scene } = useGLTF('/models/iso_container.glb', true)

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
          emissive={isMatch || hovered ? '#00fdff' : 'black'}
          emissiveIntensity={isMatch ? 0.6 : hovered ? 0.3 : 0}
        />
      </mesh>
      {/* 
      If using GLTF:
      <Clone 
        object={scene} 
        inject={<meshStandardMaterial color={color} />} 
      /> 
      */}
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

// --- Main Environment ---

function SceneContent({ yardData, searchQuery, onSelectContainer }) {
  return (
    <>
      <Sky distance={450000} sunPosition={[10, 20, 10]} inclination={0} azimuth={0.25} />
      <Environment preset="night" />
      <ambientLight intensity={0.4} />
      <directionalLight 
        position={[100, 150, 100]} 
        intensity={1.5} 
        castShadow 
        shadow-mapSize={[2048, 2048]} 
      />

      {/* Ground & Water */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[50, -0.05, 100]} receiveShadow>
        <planeGeometry args={[500, 600]} />
        <meshStandardMaterial color="#111" roughness={0.9} />
      </mesh>
      
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[-150, -1, 100]}>
        <planeGeometry args={[200, 600]} />
        <meshStandardMaterial color="#001220" roughness={0.1} metalness={0.9} transparent opacity={0.6} />
      </mesh>
      {/* Black asphalt mat underneath the blocks */}
      {yardData?.blocks?.[0] && (
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.05, 0]}>
          <planeGeometry args={[
            2 * yardData.blocks[0].width + 20 + 20, 
            2 * yardData.blocks[0].length + 12 + 20
          ]} />
          <meshStandardMaterial color="#111111" roughness={0.9} />
        </mesh>
      )}

      <gridHelper args={[600, 60, '#222', '#222']} position={[50, 0, 100]} />

      {/* Blocks & Assets */}
      {yardData?.blocks?.map((block) => (
        <group key={block.block_id} position={[block.x, 0, block.y]}>
          {/* Label positioned to the right of the block, running parallel to it */}
          <Text
            position={[block.width + 10, 0.1, block.length / 2]}
            rotation={[-Math.PI / 2, 0, -Math.PI / 2]}
            fontSize={6}
            color="#CCCCCC"
            anchorX="center"
            anchorY="middle"
          >
            ZONE {block.block_id}
          </Text>

          <RTGModel position={[block.width/2, 0, block.length/2]} />

          {block.stacks.map((stack) => (
            <group key={`${block.block_id}-${stack.row}-${stack.bay}`} position={[(stack.row - 1) * 2.8 + 1.4, 0, (stack.bay - 1) * 6.4 + 3.2]}>
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
                  />
                )
              })}
            </group>
          ))}
        </group>
      ))}
      <ContactShadows opacity={0.4} scale={500} blur={2} far={10} color="#000000" />
    </>
  )
}

// --- Entry Point ---

export default function GlobalView3D({ yardData, searchQuery, onInspectBlock, onSelectContainer }) {
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

  if (!yardData) return <div className="loading-spinner">Initialisation du Yard...</div>

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', background: '#080a0c', overflow: 'hidden' }}>
      {/* Analytics HUD Overlay */}
      <div className="analytics-hud" style={{ position: 'absolute', top: '20px', left: '20px', zIndex: 10, pointerEvents: 'none' }}>
        <div className="hud-card glass" style={{ pointerEvents: 'auto' }}>
          <label>OCCUPATION GLOBALE</label>
          <div className="value">{stats.occupancy}%</div>
          <div className="progress-bg"><div className="progress-fill" style={{ width: `${stats.occupancy}%` }}></div></div>
        </div>
      </div>

      <Canvas shadows camera={{ position: [150, 100, 200], fov: 40 }}>
        <Suspense fallback={null}>
          <SceneContent 
            yardData={yardData} 
            searchQuery={searchQuery} 
            onSelectContainer={onSelectContainer} 
          />
          <OrbitControls makeDefault maxPolarAngle={Math.PI / 2.1} minDistance={20} maxDistance={500} />
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
