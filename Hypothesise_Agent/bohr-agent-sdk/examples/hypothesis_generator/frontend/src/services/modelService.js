/* ══════════════════════════════════════════════════════════════
   MODEL SERVICE — Hypothesise Agent
   Sequential LM Studio 3-Model Runtime & Diagnostic Telemetry
   ══════════════════════════════════════════════════════════════ */

import { API_BASE } from './apiClient'

/**
 * Fetch detailed diagnostic status of LM Studio 3-model manager (Part 10.5).
 * Returns server_online, roles (prompt_refiner, vision_analyzer, main_reasoner),
 * loaded_instances, active_role_key, and single_active_model_policy.
 */
export async function getModelStatus() {
  try {
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), 4000)
    const res = await fetch(`${API_BASE}/api/models/status`, { signal: controller.signal })
    clearTimeout(timeout)
    if (!res.ok) {
      // Fallback to visualization model-status endpoint
      const fbRes = await fetch(`${API_BASE}/api/visualization/model-status`)
      if (fbRes.ok) return await fbRes.json()
      throw new Error(`HTTP ${res.status}`)
    }
    return await res.json()
  } catch (err) {
    return {
      runtime: 'lm_studio',
      server_online: false,
      single_active_model_policy: true,
      active_role_key: null,
      loaded_instances: {},
      roles: [
        {
          role_key: 'prompt_refiner',
          expected_family: 'qwen3_thinking',
          configured_model_id: 'qwen/qwen3-4b-thinking-2507',
          loaded: false,
          health_status: 'standby',
        },
        {
          role_key: 'vision_analyzer',
          expected_family: 'qwen3_vl',
          configured_model_id: 'qwen3-vl-4b-thinking',
          loaded: false,
          health_status: 'standby',
        },
        {
          role_key: 'main_reasoner',
          expected_family: 'deepseek_r1_distill',
          configured_model_id: 'deepseek/deepseek-r1-0528-qwen3-8b',
          loaded: false,
          health_status: 'standby',
        },
      ],
      error: err.message,
    }
  }
}

/**
 * Poller helper with cleanup
 */
export function pollModelStatus(callback, intervalMs = 3000) {
  let active = true
  const tick = async () => {
    if (!active) return
    const data = await getModelStatus()
    if (active) callback(data)
  }
  tick()
  const timer = setInterval(tick, intervalMs)
  return () => {
    active = false
    clearInterval(timer)
  }
}
