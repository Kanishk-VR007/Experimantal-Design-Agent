/**
 * Animation Controller
 * Decouples physical numerical time from client frame rate.
 * Performs smooth interpolation across discrete simulation time steps.
 */

export class AnimationController {
  constructor(animationConfig) {
    this.config = animationConfig || { has_animation: false, duration_s: 0, time_array: [], tracks: {} }
    this.duration = this.config.duration_s || 0
    this.timeArray = Array.isArray(this.config.time_array) ? this.config.time_array : []
    this.tracks = this.config.tracks || {}
  }

  /**
   * Find bounding time indices [i0, i1] and alpha in [0, 1] for current time t.
   */
  findTimeIndices(t) {
    if (this.timeArray.length === 0) return { i0: 0, i1: 0, alpha: 0 }
    if (this.timeArray.length === 1 || t <= this.timeArray[0]) {
      return { i0: 0, i1: 0, alpha: 0 }
    }
    const lastIdx = this.timeArray.length - 1
    if (t >= this.timeArray[lastIdx]) {
      return { i0: lastIdx, i1: lastIdx, alpha: 0 }
    }

    // Binary search for efficiency
    let low = 0
    let high = lastIdx
    while (low <= high) {
      const mid = Math.floor((low + high) / 2)
      if (this.timeArray[mid] <= t && t < this.timeArray[mid + 1]) {
        const t0 = this.timeArray[mid]
        const t1 = this.timeArray[mid + 1]
        const alpha = t1 > t0 ? (t - t0) / (t1 - t0) : 0
        return { i0: mid, i1: mid + 1, alpha }
      } else if (this.timeArray[mid] > t) {
        high = mid - 1
      } else {
        low = mid + 1
      }
    }
    return { i0: 0, i1: 0, alpha: 0 }
  }

  /**
   * Linearly interpolate 3D vectors: [x, y, z]
   */
  interpolateVec3(v0, v1, alpha) {
    if (!v0) return v1 || [0, 0, 0]
    if (!v1) return v0
    return [
      v0[0] + (v1[0] - v0[0]) * alpha,
      v0[1] + (v1[1] - v0[1]) * alpha,
      v0[2] + (v1[2] - v0[2]) * alpha,
    ]
  }

  /**
   * Retrieve evaluated transformations for an object at time t.
   */
  getObjectTransform(objectId, t) {
    const track = this.tracks[objectId]
    if (!track) return null

    const { i0, i1, alpha } = this.findTimeIndices(t)
    const result = {}

    if (Array.isArray(track.position) && track.position.length > 0) {
      const p0 = track.position[Math.min(i0, track.position.length - 1)]
      const p1 = track.position[Math.min(i1, track.position.length - 1)]
      result.position = this.interpolateVec3(p0, p1, alpha)
    }

    if (Array.isArray(track.rotation) && track.rotation.length > 0) {
      const r0 = track.rotation[Math.min(i0, track.rotation.length - 1)]
      const r1 = track.rotation[Math.min(i1, track.rotation.length - 1)]
      result.rotation = this.interpolateVec3(r0, r1, alpha)
    }

    if (Array.isArray(track.scale) && track.scale.length > 0) {
      const s0 = track.scale[Math.min(i0, track.scale.length - 1)]
      const s1 = track.scale[Math.min(i1, track.scale.length - 1)]
      result.scale = this.interpolateVec3(s0, s1, alpha)
    }

    if (Array.isArray(track.emissive_intensity) && track.emissive_intensity.length > 0) {
      const e0 = track.emissive_intensity[Math.min(i0, track.emissive_intensity.length - 1)]
      const e1 = track.emissive_intensity[Math.min(i1, track.emissive_intensity.length - 1)]
      result.emissiveIntensity = e0 + (e1 - e0) * alpha
    }

    return result
  }

  /**
   * Sample dynamic measurement value at time t.
   */
  getDynamicMeasurement(series, t) {
    if (!Array.isArray(series) || series.length === 0) return null
    const { i0, i1, alpha } = this.findTimeIndices(t)
    const v0 = series[Math.min(i0, series.length - 1)]
    const v1 = series[Math.min(i1, series.length - 1)]
    return typeof v0 === 'number' && typeof v1 === 'number'
      ? v0 + (v1 - v0) * alpha
      : v0
  }
}

