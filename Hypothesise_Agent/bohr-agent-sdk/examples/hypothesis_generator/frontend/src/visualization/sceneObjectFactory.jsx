import React, { useMemo } from 'react'
import * as THREE from 'three'

/**
 * Scene Object Factory
 * Instantiates declarative 3D geometry and materials for React Three Fiber.
 */
export function RenderSceneObject({ obj, dynamicTransform, onHover, onClick, isSelected }) {
  const { id, name, type, dimensions = {}, material = {}, metadata = {} } = obj

  // Combine static position/rotation with dynamic animation transform
  const pos = dynamicTransform?.position || obj.position || [0, 0, 0]
  const rot = dynamicTransform?.rotation || obj.rotation || [0, 0, 0]
  const scale = dynamicTransform?.scale || obj.scale || [1, 1, 1]
  const emissiveIntensity = typeof dynamicTransform?.emissiveIntensity === 'number'
    ? dynamicTransform.emissiveIntensity
    : material.emissiveIntensity || 0.0

  // Line geometry caching
  const lineGeometry = useMemo(() => {
    if (type !== 'line') return null
    const pointsData = metadata?.points || []
    if (!Array.isArray(pointsData) || pointsData.length === 0) return null
    const pts = pointsData.map((p) => new THREE.Vector3(p[0] || 0, p[1] || 0, p[2] || 0))
    return new THREE.BufferGeometry().setFromPoints(pts)
  }, [type, metadata?.points])

  const handlePointerOver = (e) => {
    e.stopPropagation()
    if (onHover) onHover({ id, name, type, metadata, dimensions, position: pos })
  }

  const handlePointerOut = (e) => {
    e.stopPropagation()
    if (onHover) onHover(null)
  }

  const handleClick = (e) => {
    e.stopPropagation()
    if (onClick) onClick({ id, name, type, metadata, dimensions })
  }

  const matColor = isSelected ? '#38bdf8' : material.color || '#94a3b8'

  switch (type) {
    case 'box': {
      const w = dimensions.width || 1
      const h = dimensions.height || 1
      const d = dimensions.depth || 1
      return (
        <mesh
          position={pos}
          rotation={rot}
          scale={scale}
          onPointerOver={handlePointerOver}
          onPointerOut={handlePointerOut}
          onClick={handleClick}
        >
          <boxGeometry args={[w, h, d]} />
          <meshStandardMaterial
            color={matColor}
            metalness={material.metalness}
            roughness={material.roughness}
            opacity={material.opacity}
            transparent={material.transparent}
            wireframe={material.wireframe}
            emissive={material.emissive}
            emissiveIntensity={emissiveIntensity}
          />
        </mesh>
      )
    }

    case 'sphere': {
      const r = dimensions.radius || 0.5
      return (
        <mesh
          position={pos}
          rotation={rot}
          scale={scale}
          onPointerOver={handlePointerOver}
          onPointerOut={handlePointerOut}
          onClick={handleClick}
        >
          <sphereGeometry args={[r, 32, 32]} />
          <meshStandardMaterial
            color={matColor}
            metalness={material.metalness}
            roughness={material.roughness}
            opacity={material.opacity}
            transparent={material.transparent}
            wireframe={material.wireframe}
            emissive={material.emissive}
            emissiveIntensity={emissiveIntensity}
          />
        </mesh>
      )
    }

    case 'cylinder': {
      const r = dimensions.radius || 0.2
      const h = dimensions.height || 1
      return (
        <mesh
          position={pos}
          rotation={rot}
          scale={scale}
          onPointerOver={handlePointerOver}
          onPointerOut={handlePointerOut}
          onClick={handleClick}
        >
          <cylinderGeometry args={[r, r, h, 32]} />
          <meshStandardMaterial
            color={matColor}
            metalness={material.metalness}
            roughness={material.roughness}
            opacity={material.opacity}
            transparent={material.transparent}
            wireframe={material.wireframe}
            emissive={material.emissive}
            emissiveIntensity={emissiveIntensity}
          />
        </mesh>
      )
    }

    case 'capsule': {
      const r = dimensions.radius || 0.2
      const l = dimensions.length || 0.6
      return (
        <mesh
          position={pos}
          rotation={rot}
          scale={scale}
          onPointerOver={handlePointerOver}
          onPointerOut={handlePointerOut}
          onClick={handleClick}
        >
          <capsuleGeometry args={[r, l, 16, 32]} />
          <meshStandardMaterial
            color={matColor}
            metalness={material.metalness}
            roughness={material.roughness}
            opacity={material.opacity}
            transparent={material.transparent}
          />
        </mesh>
      )
    }

    case 'torus': {
      const r = dimensions.radius || 0.5
      const tube = dimensions.tube || 0.05
      return (
        <mesh
          position={pos}
          rotation={rot}
          scale={scale}
          onPointerOver={handlePointerOver}
          onPointerOut={handlePointerOut}
          onClick={handleClick}
        >
          <torusGeometry args={[r, tube, 16, 64]} />
          <meshStandardMaterial
            color={matColor}
            metalness={material.metalness}
            roughness={material.roughness}
            opacity={material.opacity}
            transparent={material.transparent}
            emissive={material.emissive}
            emissiveIntensity={emissiveIntensity}
          />
        </mesh>
      )
    }

    case 'arrow': {
      const len = dimensions.length || 1.0
      const radius = dimensions.radius || 0.04
      const headLength = len * 0.3
      const headRadius = radius * 2.5
      const shaftLength = len - headLength
      return (
        <group position={pos} rotation={rot} scale={scale}>
          {/* Shaft pointing +Y natively */}
          <mesh position={[0, shaftLength / 2, 0]}>
            <cylinderGeometry args={[radius, radius, shaftLength, 16]} />
            <meshStandardMaterial color={matColor} metalness={0.5} roughness={0.3} />
          </mesh>
          {/* Head Cone pointing +Y natively */}
          <mesh position={[0, shaftLength + headLength / 2, 0]}>
            <coneGeometry args={[headRadius, headLength, 16]} />
            <meshStandardMaterial color={matColor} metalness={0.5} roughness={0.3} />
          </mesh>
        </group>
      )
    }

    case 'line': {
      if (!lineGeometry) return null
      return (
        <line geometry={lineGeometry} position={pos} rotation={rot}>
          <lineBasicMaterial
            color={material.color || '#38bdf8'}
            transparent={material.transparent}
            opacity={material.opacity || 0.6}
            linewidth={2}
          />
        </line>
      )
    }

    case 'plane': {
      const w = dimensions.width || 4
      const d = dimensions.depth || 4
      return (
        <mesh
          position={pos}
          rotation={rot}
          scale={scale}
          onPointerOver={handlePointerOver}
          onPointerOut={handlePointerOut}
        >
          <planeGeometry args={[w, d]} />
          <meshStandardMaterial
            color={matColor}
            roughness={0.9}
            metalness={0.1}
            side={THREE.DoubleSide}
          />
        </mesh>
      )
    }

    case 'group':
    default:
      return (
        <group position={pos} rotation={rot} scale={scale}>
          {obj.children?.map((child) => (
            <RenderSceneObject
              key={child.id}
              obj={child}
              onHover={onHover}
              onClick={onClick}
              isSelected={isSelected}
            />
          ))}
        </group>
      )
  }
}

