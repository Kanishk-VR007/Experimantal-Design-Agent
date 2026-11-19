/* ══════════════════════════════════════════════════════════════
   SIMULATION SERVICE — Hypothesise Agent
   Deterministic Simulation Engines & Parameter Re-Solving
   ══════════════════════════════════════════════════════════════ */

import { API_BASE } from './apiClient'

/**
 * Execute Layer 3 deterministic simulation from experimental design.
 */
export async function runSimulation(topic, design, domain = null, refinement = null) {
  const response = await fetch(`${API_BASE}/api/run-simulation`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ topic, design, domain, refinement }),
  })
  if (!response.ok) {
    const errText = await response.text()
    throw new Error(`Simulation failed (HTTP ${response.status}): ${errText}`)
  }
  const data = await response.json()
  return data.simulation || null
}

/**
 * Update parameters and rerun authoritative deterministic simulation solver.
 * Synchronizes 2D plots, 3D meshes, and scientific validation in one atomic call.
 */
export async function updateParameters(experimentId, domain, parameters, currentProcedure = null) {
  const body = {
    experiment_id: experimentId,
    domain: domain || 'physics',
    parameters: parameters || {},
    current_procedure: currentProcedure,
  }
  const response = await fetch(`${API_BASE}/api/visualization/update`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!response.ok) {
    const errText = await response.text()
    throw new Error(`Parameter update failed (HTTP ${response.status}): ${errText}`)
  }
  return await response.json()
}

/**
 * Generate declarative 3D scene specification
 */
export async function generateSceneSpecification(topic, procedure, numericalResults, plotData, domain) {
  const body = {
    topic,
    procedure: procedure || {},
    numerical_results: numericalResults || {},
    plot_data: plotData || [],
    domain: domain || null,
  }
  const response = await fetch(`${API_BASE}/api/visualization/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!response.ok) {
    throw new Error(`Scene generation failed (HTTP ${response.status})`)
  }
  return await response.json()
}
