import { useEffect, useRef } from 'react'
import { useThree, useFrame } from '@react-three/fiber'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'

export function CameraController({ target = [0, 0, 0], resetTrigger = 0, allowOrbit = true, allowPan = true, allowZoom = true }) {
  const { camera, gl } = useThree()
  const controlsRef = useRef(null)

  useEffect(() => {
    const controls = new OrbitControls(camera, gl.domElement)
    controls.enableDamping = true
    controls.dampingFactor = 0.05
    controls.enableRotate = allowOrbit
    controls.enablePan = allowPan
    controls.enableZoom = allowZoom
    controls.target.set(target[0] || 0, target[1] || 0, target[2] || 0)
    controls.saveState()
    controlsRef.current = controls

    return () => {
      controls.dispose()
    }
  }, [camera, gl.domElement, allowOrbit, allowPan, allowZoom])

  useFrame(() => {
    if (controlsRef.current) {
      controlsRef.current.update()
    }
  })

  // Update target when prop changes
  useEffect(() => {
    if (controlsRef.current) {
      controlsRef.current.target.set(target[0] || 0, target[1] || 0, target[2] || 0)
      controlsRef.current.update()
    }
  }, [target])

  // Handle camera reset button
  useEffect(() => {
    if (resetTrigger > 0 && controlsRef.current) {
      controlsRef.current.reset()
    }
  }, [resetTrigger])

  return null
}

