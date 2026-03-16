import React, { useMemo, useState, Suspense, useEffect } from 'react'
import { Canvas } from '@react-three/fiber'
import { 
  OrbitControls, 
  PerspectiveCamera, 
  Environment, 
  ContactShadows, 
  Grid,
  Sky, 
  Text,
  Html
} from '@react-three/drei'
import { useThree, useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import TooltipHUD from './TooltipHUD'

// --- Co-shared logic with GlobalView ---
const STATUS_PALETTE = {
  'normal': '#3fb950',
  'scheduled': '#d29922',
  'urgent': '#f85149',
  'empty': '#58a6ff',
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

function Container({ position, color, data, onSelect, isMatch, onHover }) {
  const [hovered, setHover] = useState(false)
  const [pulse, setPulse] = useState(false)
  const [highlight, setHighlight] = useState(false)

  // Trigger pulse and highlight animation when search match occurs
  useEffect(() => {
    if (isMatch) {
      setPulse(true)
      setHighlight(true)
      const pulseTimer = setTimeout(() => setPulse(false), 800)
      const highlightTimer = setTimeout(() => setHighlight(false), 3000)
      return () => {
        clearTimeout(pulseTimer)
        clearTimeout(highlightTimer)
      }
    } else {
      setHighlight(false)
      setPulse(false)
    }
  }, [isMatch])
  
  return (
    <group position={position}>
      <mesh 
        castShadow 
        receiveShadow 
        onClick={(e) => {
          e.stopPropagation()
          onSelect(data)
        }} 
        onPointerOver={(e) => {
          e.stopPropagation()
          setHover(true)
          onHover(data)
          document.body.style.cursor = 'pointer'
        }} 
        onPointerOut={() => {
          setHover(false)
          onHover(null)
          document.body.style.cursor = 'auto'
        }}
        scale={hovered ? 1.03 : pulse ? 1.15 : 1}
      >
        <boxGeometry args={[2.5, 2.5, 6.1]} />
        <meshStandardMaterial 
          color={highlight ? '#00fdff' : color} 
          metalness={0.6} 
          roughness={0.4}
          emissive={highlight || hovered ? '#00fdff' : 'black'}
          emissiveIntensity={highlight ? 0.8 : hovered ? 0.3 : 0}
        />
      </mesh>
    </group>
  )
}

/**
 * Camera Focus Controller (Fly-To) 
 * Releases control after 2s or when target reached
 */
function CameraFocus({ targetPos }) {
  const { camera, controls } = useThree()
  const [active, setActive] = useState(false)
  const lastTarget = React.useRef(null)

  useEffect(() => {
    if (targetPos && JSON.stringify(targetPos) !== JSON.stringify(lastTarget.current)) {
      setActive(true)
      lastTarget.current = targetPos
      const timer = setTimeout(() => setActive(false), 2000)
      return () => clearTimeout(timer)
    }
  }, [targetPos])
  
  useFrame((state, delta) => {
    if (!active || !targetPos || !controls) return

    const targetVec = new THREE.Vector3(...targetPos)
    controls.target.lerp(targetVec, 0.1)
    
    const desiredCamPos = new THREE.Vector3(
      targetVec.x + 35,
      targetVec.y + 35,
      targetVec.z + 35
    )
    camera.position.lerp(desiredCamPos, 0.05)
    
    controls.update()
    if (camera.position.distanceTo(desiredCamPos) < 0.5) {
      setActive(false)
    }
  })

  return null
}

/**
 * RTG Crane component (Procedural version)
 */
function RTGModel({ position, label }) {
  return (
    <group position={position}>
      {/* Legs */}
      <mesh position={[-6, 6, 0]} castShadow> 
        <boxGeometry args={[0.8, 12, 1.2]} /> 
        <meshStandardMaterial color="#ebc034" metalness={0.7} roughness={0.3} /> 
      </mesh>
      <mesh position={[6, 6, 0]} castShadow> 
        <boxGeometry args={[0.8, 12, 1.2]} /> 
        <meshStandardMaterial color="#ebc034" metalness={0.7} roughness={0.3} /> 
      </mesh>
      {/* Top Beam */}
      <mesh position={[0, 12, 0]} castShadow> 
        <boxGeometry args={[13, 1, 3]} /> 
        <meshStandardMaterial color="#ebc034" metalness={0.7} roughness={0.3} /> 
      </mesh>
      {/* Trolley */}
      <mesh position={[0, 11, 0]}> 
        <boxGeometry args={[2, 0.5, 2]} /> 
        <meshStandardMaterial color="#333" /> 
      </mesh>

      {/* Block Identification Label */}
      <Text
        position={[0, 15, 0]}
        fontSize={8}
        color="#FFFFFF"
        anchorX="center"
        anchorY="middle"
        outlineWidth={0.5}
        outlineColor="#000000"
      >
        {label}
      </Text>
    </group>
  )
}


export default function BlockDetailView({ yardData, selectedBlock, onBlockChange, searchQuery, onSelectContainer }) {
  const [visibleRow, setVisibleRow] = useState(0) // 0 means all rows visible
  const [hoveredContainer, setHoveredContainer] = useState(null)
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 })

  // Track mouse movement for tooltip
  useEffect(() => {
    const handleMouseMove = (e) => {
      setMousePos({ x: e.clientX, y: e.clientY })
    }
    window.addEventListener('mousemove', handleMouseMove)
    return () => window.removeEventListener('mousemove', handleMouseMove)
  }, [])

  // Auto-focus row on search
  useEffect(() => {
    if (!searchQuery || !yardData) {
      setVisibleRow(0)
      return
    }
    const blockData = yardData?.blocks?.find(b => b.block_id === selectedBlock)
    if (!blockData) return

    for (const stack of blockData.stacks) {
      for (const slot of stack.slots) {
        if (!slot.is_free && (slot.container_id === searchQuery || slot.container_details?.location === searchQuery)) {
          setVisibleRow(stack.row)
          return
        }
      }
    }
  }, [searchQuery, yardData, selectedBlock])

  const blockIds = useMemo(() => yardData?.blocks?.map(b => b.block_id) || [], [yardData])
  const blockData = useMemo(() => yardData?.blocks?.find(b => b.block_id === selectedBlock), [yardData, selectedBlock])

  const targetContainerPos = useMemo(() => {
    if (!searchQuery || !blockData) return null
    for (const stack of blockData.stacks) {
      for (const slot of stack.slots) {
        if (!slot.is_free && (slot.container_id === searchQuery || slot.container_details?.location === searchQuery)) {
          return [
            (stack.row - 1 - yardData.n_rows / 2 + 0.5) * 2.8,
            (slot.tier - 1) * 2.6 + 1.3,
            (stack.bay - 1 - yardData.n_bays / 2 + 0.5) * 6.4
          ]
        }
      }
    }
    return null
  }, [searchQuery, blockData, yardData])

  if (!yardData) return <div className="glass" style={{ padding: '20px' }}>Chargement des données...</div>
  
  if (!blockData) return (
    <div className="glass" style={{ padding: '40px', textAlign: 'center' }}>
      Sélectionnez un bloc pour commencer l'analyse détaillée.
    </div>
  )

  const occupancyPct = Math.round(blockData.occupancy * 100)

  return (
    <div style={{ position: 'relative', display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0, gap: '15px' }}>
      <TooltipHUD 
        data={hoveredContainer} 
        mousePos={mousePos}
      />
      
      <div className="detail-header-row glass" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '15px 25px', borderRadius: '12px', gap: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '25px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <label style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '1px' }}>Zone</label>
            <select 
              value={selectedBlock} 
              onChange={e => { onBlockChange(e.target.value); setVisibleRow(0); }}
              style={{ padding: '8px 12px', background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border)', borderRadius: '6px', color: 'white' }}
            >
              {blockIds.map(id => (
                <option key={id} value={id}>Bloc {id}</option>
              ))}
            </select>
          </div>

          {/* New Row Visibility Slider for Detail View */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', paddingLeft: '20px', borderLeft: '1px solid var(--border)' }}>
            <label style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '1px' }}>Visibilité Rangées</label>
            <input 
              type="range" 
              min="0" 
              max={yardData.n_rows} 
              value={visibleRow} 
              onChange={(e) => setVisibleRow(parseInt(e.target.value))}
              style={{ width: '100px' }}
            />
            <span style={{ fontSize: '0.8rem', color: 'white', minWidth: '40px' }}>
              {visibleRow === 0 ? 'Toutes' : `R${visibleRow}`}
            </span>
          </div>
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontWeight: 700, textTransform: 'uppercase' }}>Densité</span>
          <div style={{ width: '120px', height: '6px', background: 'rgba(255,255,255,0.05)', borderRadius: '3px', overflow: 'hidden' }}>
            <div style={{ width: `${occupancyPct}%`, height: '100%', background: occupancyPct > 80 ? 'var(--accent-red)' : 'var(--accent-green)', transition: 'width 0.5s' }} />
          </div>
          <strong style={{ fontSize: '1rem', color: occupancyPct > 80 ? 'var(--accent-red)' : 'var(--accent-green)' }}>{occupancyPct}%</strong>
        </div>
      </div>

      <div className="chart-container glass" style={{ flex: 1, borderRadius: '12px', overflow: 'hidden', position: 'relative', background: '#080a0c' }}>
        <Canvas shadows camera={{ position: [40, 30, 40], fov: 35 }}>
          <Suspense fallback={null}>
            <Sky inclination={0.1} distance={450000} />
            <Environment preset="night" />
            <ambientLight intensity={0.5} />
            <directionalLight position={[20, 50, 20]} intensity={1.2} castShadow />

            <group position={[0, 0, 0]}>
              <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.01, 0]} receiveShadow>
                <planeGeometry args={[blockData.width + 40, blockData.length + 40]} />
                <meshStandardMaterial color="#050505" roughness={0.7} metalness={0.8} />
              </mesh>
              
              <Grid
                position={[0, 0, 0]}
                args={[200, 200]}
                cellSize={2}
                cellThickness={1}
                cellColor="#111"
                sectionSize={10}
                sectionThickness={1.5}
                sectionColor="#222"
                fadeDistance={80}
                fadeStrength={1}
              />

              <RTGModel position={[0, 0, 0]} label={selectedBlock} />

              {blockData.stacks.map((stack) => {
                // Force visibility if stack contains the searched container
                const hasSearchMatch = searchQuery && stack.slots.some(s => 
                  !s.is_free && (s.container_id === searchQuery || s.container_details?.location === searchQuery)
                );
                const isTargetRow = visibleRow === 0 || stack.row === visibleRow || hasSearchMatch;
                
                if (!isTargetRow) return null;

                return (
                  <group key={`${stack.row}-${stack.bay}`} position={[
                    (stack.row - 1 - yardData.n_rows/2 + 0.5) * 2.8, 
                    0, 
                    (stack.bay - 1 - yardData.n_bays/2 + 0.5) * 6.4
                  ]}>
                    {stack.slots.map((slot) => {
                      if (slot.is_free) return null;
                      const isMatch = searchQuery && (slot.container_id === searchQuery || slot.container_details?.location === searchQuery)
                      return (
                        <Container 
                          key={slot.container_id}
                          position={[0, (slot.tier - 1) * 2.6 + 1.3, 0]}
                          color={getStatusColor(slot)}
                          data={{ id: slot.container_id, ...slot.container_details }}
                          onSelect={onSelectContainer}
                          onHover={setHoveredContainer}
                          isMatch={isMatch}
                        />
                      )
                    })}
                  </group>
                )
              })}
            </group>
            <CameraFocus targetPos={targetContainerPos} />
            <ContactShadows opacity={0.6} scale={100} blur={2} far={10} color="#000000" />
            <OrbitControls makeDefault maxPolarAngle={Math.PI / 2.1} />
          </Suspense>
        </Canvas>
      </div>
    </div>
  )
}
