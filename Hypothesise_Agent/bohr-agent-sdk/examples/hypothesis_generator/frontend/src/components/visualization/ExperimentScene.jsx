import React from 'react'
import { Canvas } from '@react-three/fiber'
import { CameraController } from './CameraController'
import { RenderSceneObject } from '../../visualization/sceneObjectFactory'
import { VectorRenderer } from './VectorRenderer'

export function ExperimentScene({
  spec,
  currentTime = 0,
  animationController,
  showGrid = true,
  showAxes = true,
  showVectors = true,
  resetCameraTrigger = 0,
  zoomTrigger = 0,
  onObjectHover,
  onObjectClick,
  selectedObjectId,
}) {
  const { camera, lighting, objects = [], vectors = [], controls = {} } = spec

  const camPos = camera?.position || [0, 2.5, 6]
  const camTarget = camera?.target || [0, 0, 0]
  const camFov = camera?.fov || 50

  // Calculate evaluated object transforms for current time
  const evaluatedTransforms = {}
  for (const obj of objects) {
    if (animationController) {
      const transform = animationController.getObjectTransform(obj.id, currentTime)
      if (transform) evaluatedTransforms[obj.id] = transform
    }
  }

  return (
    <div style={{ width: '100%', height: '100%', position: 'relative' }}>
      <Canvas
        camera={{ position: camPos, fov: camFov }}
        style={{ background: controls.background_color || '#0b0f19' }}
      >
        {/* Studio Lighting */}
        <ambientLight intensity={lighting?.ambient_intensity ?? 0.75} />
        <directionalLight
          position={lighting?.directional_position || [5, 10, 7]}
          intensity={lighting?.directional_intensity ?? 0.9}
        />
        <pointLight position={[-4, 6, -4]} intensity={0.3} />

        {/* Camera Navigation */}
        <CameraController
          target={camTarget}
          resetTrigger={resetCameraTrigger}
          zoomTrigger={zoomTrigger}
          allowOrbit={controls.allow_orbit ?? true}
          allowPan={controls.allow_pan ?? true}
          allowZoom={controls.allow_zoom ?? true}
        />

        {/* Spatial References */}
        {showGrid && (
          <gridHelper args={[16, 16, '#334155', '#1e293b']} position={[0, -0.01, 0]} />
        )}
        {showAxes && <axesHelper args={[1.5]} position={[0, 0.01, 0]} />}

        {/* Allowlisted Scene Objects */}
        {objects.map((obj) => (
          <RenderSceneObject
            key={obj.id}
            obj={obj}
            dynamicTransform={evaluatedTransforms[obj.id]}
            onHover={onObjectHover}
            onClick={onObjectClick}
            isSelected={selectedObjectId === obj.id}
          />
        ))}

        {/* Physical Vector Overlays */}
        {showVectors &&
          vectors.map((vec) => {
            const originObj = objects.find((o) => o.id === vec.origin_object_id)
            const originPos = evaluatedTransforms[vec.origin_object_id]?.position || originObj?.position
            const dynamicVec = vec.dynamic_track && animationController
              ? animationController.getDynamicMeasurement(vec.dynamic_track, currentTime)
              : null

            return (
              <VectorRenderer
                key={vec.id}
                vector={vec}
                originPos={originPos}
                dynamicVec={dynamicVec}
                visible={showVectors}
              />
            )
          })}
      </Canvas>
    </div>
  )
}

