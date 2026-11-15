import React, { useMemo } from 'react'
import * as THREE from 'three'

/**
 * Directional 3D Vector Arrow Renderer
 * Renders physical vectors (velocity, forces) anchored to dynamic objects.
 */
export function VectorRenderer({ vector, originPos, dynamicVec, visible = true }) {
  const vecData = dynamicVec || vector.static_vector || [0, 1, 0]
  const vx = vecData[0] || 0
  const vy = vecData[1] || 0
  const vz = vecData[2] || 0

  const length = Math.sqrt(vx * vx + vy * vy + vz * vz) * (vector.length_scale || 1.0)
  const isHidden = !visible || !originPos || length < 0.001

  const dir = useMemo(() => {
    if (isHidden) return new THREE.Vector3(0, 1, 0)
    return new THREE.Vector3(vx, vy, vz).normalize()
  }, [vx, vy, vz, isHidden])

  const origin = useMemo(() => {
    if (!originPos) return new THREE.Vector3(0, 0, 0)
    return new THREE.Vector3(originPos[0] || 0, originPos[1] || 0, originPos[2] || 0)
  }, [originPos])

  const hex = useMemo(() => {
    return vector.color ? parseInt(vector.color.replace('#', '0x'), 16) : 0x10b981
  }, [vector.color])

  const arrow = useMemo(() => {
    const effLen = Math.max(length, 0.05)
    const headLength = Math.min(effLen * 0.3, 0.25)
    const headWidth = headLength * 0.5
    return new THREE.ArrowHelper(dir, origin, effLen, hex, headLength, headWidth)
  }, [dir, origin, length, hex])

  if (isHidden) return null

  return <primitive object={arrow} />
}

