import React, { useMemo, Suspense } from 'react'
import { Canvas } from '@react-three/fiber'
import { 
  OrbitControls, 
  PerspectiveCamera, 
  Environment, 
  ContactShadows, 
  Sky, 
  Text
} from '@react-three/drei'

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

function Container({ position, color, data, onSelect, isMatch }) {
  return (
    <mesh 
      position={position} 
      castShadow 
      receiveShadow 
      onClick={() => onSelect(data)} 
      onPointerOver={() => (document.body.style.cursor = 'pointer')} 
      onPointerOut={() => (document.body.style.cursor = 'auto')}
    >
      <boxGeometry args={[2.5, 2.5, 6.1]} />
      <meshStandardMaterial 
        color={isMatch ? '#00fdff' : color} 
        metalness={0.6} 
        roughness={0.4}
        emissive={isMatch ? '#00fdff' : 'black'}
        emissiveIntensity={isMatch ? 0.3 : 0}
      />
    </mesh>
  )
}

export default function BlockDetailView({ yardData, selectedBlock, onBlockChange, searchQuery, onSelectContainer }) {
  const blockIds = useMemo(() => yardData?.blocks?.map(b => b.block_id) || [], [yardData])
  const blockData = useMemo(() => yardData?.blocks?.find(b => b.block_id === selectedBlock), [yardData, selectedBlock])

  if (!yardData) return <div className="glass" style={{ padding: '20px' }}>Chargement des données...</div>
  
  if (!blockData) return (
    <div className="glass" style={{ padding: '40px', textAlign: 'center' }}>
      Sélectionnez un bloc pour commencer l'analyse détaillée.
    </div>
  )

  const occupancyPct = Math.round(blockData.occupancy * 100)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0, gap: '15px' }}>
      <div className="detail-header-row glass" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '15px 25px', borderRadius: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
          <label style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '1px' }}>Zone</label>
          <select 
            value={selectedBlock} 
            onChange={e => onBlockChange(e.target.value)}
            style={{ padding: '8px 12px', background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border)', borderRadius: '6px', color: 'white' }}
          >
            {blockIds.map(id => (
              <option key={id} value={id}>Bloc {id}</option>
            ))}
          </select>
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

            <group position={[-blockData.width/2, 0, -blockData.length/2]}>
              <mesh rotation={[-Math.PI / 2, 0, 0]} position={[blockData.width/2, -0.01, blockData.length/2]} receiveShadow>
                <planeGeometry args={[blockData.width + 40, blockData.length + 40]} />
                <meshStandardMaterial color="#050505" />
              </mesh>
              <gridHelper args={[200, 20, '#1a1a1a', '#0a0a0a']} position={[blockData.width/2, 0, blockData.length/2]} />

              {blockData.stacks.map((stack) => (
                <group key={`${stack.row}-${stack.bay}`} position={[(stack.row - 1) * 2.8 + 1.4, 0, (stack.bay - 1) * 6.4 + 3.2]}>
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
                        isMatch={isMatch}
                      />
                    )
                  })}
                </group>
              ))}
            </group>
            <ContactShadows opacity={0.6} scale={100} blur={2} far={10} color="#000000" />
            <OrbitControls makeDefault maxPolarAngle={Math.PI / 2.1} />
          </Suspense>
        </Canvas>
      </div>
    </div>
  )
}
