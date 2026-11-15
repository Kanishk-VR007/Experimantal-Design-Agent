/**
 * Client-Side Scene Schema & Validator
 * Enforces allowlists, type safety, and prevents execution of unvalidated code.
 */

export const ALLOWED_OBJECT_TYPES = new Set([
  'box',
  'sphere',
  'cylinder',
  'capsule',
  'torus',
  'arrow',
  'line',
  'plane',
  'group',
])

export function validateSceneSpecification(spec) {
  if (!spec || typeof spec !== 'object') {
    return { valid: false, error: 'Specification is empty or not an object' }
  }

  if (!spec.domain || !spec.scene_template) {
    return { valid: false, error: 'Missing domain or scene_template' }
  }

  const objects = Array.isArray(spec.objects) ? spec.objects : []
  const sanitizedObjects = []

  for (const obj of objects) {
    if (!obj.id || !obj.type) continue

    const type = String(obj.type).toLowerCase()
    if (!ALLOWED_OBJECT_TYPES.has(type)) {
      console.warn(`[3D Validator] Disallowed object type "${obj.type}", skipping id: ${obj.id}`)
      continue
    }

    sanitizedObjects.push({
      id: String(obj.id),
      name: String(obj.name || obj.id),
      type,
      position: Array.isArray(obj.position) && obj.position.length === 3 ? obj.position : [0, 0, 0],
      rotation: Array.isArray(obj.rotation) && obj.rotation.length === 3 ? obj.rotation : [0, 0, 0],
      scale: Array.isArray(obj.scale) && obj.scale.length === 3 ? obj.scale : [1, 1, 1],
      dimensions: typeof obj.dimensions === 'object' && obj.dimensions !== null ? obj.dimensions : {},
      material: {
        color: obj.material?.color || '#3b82f6',
        metalness: typeof obj.material?.metalness === 'number' ? obj.material.metalness : 0.2,
        roughness: typeof obj.material?.roughness === 'number' ? obj.material.roughness : 0.4,
        opacity: typeof obj.material?.opacity === 'number' ? obj.material.opacity : 1.0,
        transparent: Boolean(obj.material?.transparent),
        wireframe: Boolean(obj.material?.wireframe),
        emissive: obj.material?.emissive || '#000000',
        emissiveIntensity: typeof obj.material?.emissive_intensity === 'number' ? obj.material.emissive_intensity : 0.0,
      },
      metadata: typeof obj.metadata === 'object' && obj.metadata !== null ? obj.metadata : {},
    })
  }

  return {
    valid: true,
    spec: {
      ...spec,
      objects: sanitizedObjects,
      parameters: Array.isArray(spec.parameters) ? spec.parameters : [],
      measurement_overlays: Array.isArray(spec.measurement_overlays) ? spec.measurement_overlays : [],
      vectors: Array.isArray(spec.vectors) ? spec.vectors : [],
      animation: spec.animation || { has_animation: false, duration_s: 0, time_array: [], tracks: {} },
      controls: spec.controls || { allow_orbit: true, show_grid: true, show_axes: true },
    },
  }
}

