/* ══════════════════════════════════════════════════════════════
   API CLIENT — Hypothesise Agent
   Centralized API service layer
   ══════════════════════════════════════════════════════════════ */

export const API_BASE = 'http://localhost:8000'
export const MEMORY_API_BASE = 'http://localhost:8001'

/**
 * Fetch backend health status
 */
export async function fetchHealth() {
  try {
    const response = await fetch(`${API_BASE}/health`)
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }
    const data = await response.json()
    const isLlmHealthy = data.status === 'healthy' || Boolean(data.llm_available || data.ollama_available)
    return {
      loading: false,
      healthy: true,
      backendHealthy: true,
      ollamaAvailable: isLlmHealthy,
      llmHealthy: isLlmHealthy,
      provider: data.provider || 'lmstudio',
      activeModel: data.active_model || (data.models && data.models[0]) || '',
      refinerAvailable: Boolean(data.refiner_available),
      refinerModel: data.refiner_model || '',
      refinerProvider: data.refiner_provider || 'lmstudio',
      models: data.models || [],
    }
  } catch (error) {
    return {
      loading: false,
      healthy: false,
      backendHealthy: false,
      ollamaAvailable: false,
      llmHealthy: false,
      error: 'Cannot connect to backend server',
    }
  }
}

/**
 * Search for research papers
 */
export async function searchPapers(topic, maxPapers = 3, useMockData = false) {
  try {
    const response = await fetch(`${API_BASE}/api/search-papers`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic, max_papers: maxPapers, use_mock_data: useMockData }),
    })
    if (!response.ok) throw new Error(`Server returned HTTP ${response.status}`)
    return await response.json()
  } catch (error) {
    throw new Error(`Paper search failed: ${error.message}`)
  }
}

/**
 * Generate experimental design (returns raw Response for SSE streaming)
 */
export async function generateDesign(topic, maxPapers = 3, useMockData = false, domain = null) {
  const response = await fetch(`${API_BASE}/api/generate-design`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ topic, max_papers: maxPapers, use_mock_data: useMockData, domain }),
  })
  if (!response.ok) {
    throw new Error(`Server returned HTTP ${response.status}`)
  }
  return response
}

/**
 * Run a simulation based on experimental design
 */
export async function runSimulation(topic, design, domain = null, refinement = null) {
  try {
    const response = await fetch(`${API_BASE}/api/run-simulation`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic, design, domain, refinement }),
    })
    if (!response.ok) throw new Error(`Server returned HTTP ${response.status}`)
    const data = await response.json()
    if (data.success && data.simulation) {
      return data.simulation
    }
    return null
  } catch (error) {
    throw new Error(`Simulation failed: ${error.message}`)
  }
}

/**
 * Update visualization parameters
 */
export async function updateVisualization(simulationId, params) {
  try {
    const response = await fetch(`${API_BASE}/api/visualization/update`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ simulation_id: simulationId, ...params }),
    })
    if (!response.ok) throw new Error(`Server returned HTTP ${response.status}`)
    return await response.json()
  } catch (error) {
    throw new Error(`Visualization update failed: ${error.message}`)
  }
}

/**
 * Fetch all evaluation reports
 */
export async function fetchEvalReports() {
  try {
    const response = await fetch(`${API_BASE}/api/eval-reports`)
    if (!response.ok) throw new Error(`Server returned HTTP ${response.status}`)
    return await response.json()
  } catch (error) {
    throw new Error(`Failed to fetch evaluation reports: ${error.message}`)
  }
}

/**
 * Fetch a single evaluation report by run ID
 */
export async function fetchEvalReport(runId) {
  try {
    const response = await fetch(`${API_BASE}/api/eval-reports/${runId}`)
    if (!response.ok) throw new Error(`Server returned HTTP ${response.status}`)
    return await response.json()
  } catch (error) {
    throw new Error(`Failed to fetch evaluation report: ${error.message}`)
  }
}

/**
 * Submit feedback for a report to Memory Agent
 */
export async function submitFeedback(feedbackData) {
  try {
    const response = await fetch(`${MEMORY_API_BASE}/improve/feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(feedbackData),
    })
    if (!response.ok) throw new Error(`Server returned HTTP ${response.status}`)
    return await response.json()
  } catch (error) {
    throw new Error(`Failed to submit feedback: ${error.message}`)
  }
}

/**
 * Fetch accuracy report from Memory Agent
 */
export async function fetchAccuracyReport() {
  try {
    const response = await fetch(`${MEMORY_API_BASE}/improve/accuracy-report`)
    if (!response.ok) throw new Error(`Server returned HTTP ${response.status}`)
    return await response.json()
  } catch (error) {
    throw new Error(`Failed to fetch accuracy report: ${error.message}`)
  }
}

/**
 * Fetch accuracy history from Memory Agent
 */
export async function fetchAccuracyHistory() {
  try {
    const response = await fetch(`${MEMORY_API_BASE}/improve/accuracy-history`)
    if (!response.ok) throw new Error(`Server returned HTTP ${response.status}`)
    return await response.json()
  } catch (error) {
    throw new Error(`Failed to fetch accuracy history: ${error.message}`)
  }
}

/**
 * Fetch domain breakdown from Memory Agent
 */
export async function fetchDomainBreakdown() {
  try {
    const response = await fetch(`${MEMORY_API_BASE}/improve/domain-breakdown`)
    if (!response.ok) throw new Error(`Server returned HTTP ${response.status}`)
    return await response.json()
  } catch (error) {
    throw new Error(`Failed to fetch domain breakdown: ${error.message}`)
  }
}

/**
 * Trigger an iterative improvement cycle
 */
export async function runImprovementCycle() {
  try {
    const response = await fetch(`${MEMORY_API_BASE}/improve/run-cycle`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    })
    if (!response.ok) throw new Error(`Server returned HTTP ${response.status}`)
    return await response.json()
  } catch (error) {
    throw new Error(`Failed to run improvement cycle: ${error.message}`)
  }
}

/**
 * Fetch local LM Studio model residency and scheduler telemetry
 */
export async function fetchModelStatus() {
  try {
    const response = await fetch(`${API_BASE}/api/visualization/model-status`)
    if (!response.ok) throw new Error(`Server returned HTTP ${response.status}`)
    return await response.json()
  } catch (error) {
    return {
      status: 'offline',
      loaded_instances: {},
      available_models: [],
      error: error.message,
    }
  }
}

/**
 * Fetch supported open-access scientific diagram repositories
 */
export async function fetchReferenceSources() {
  try {
    const response = await fetch(`${API_BASE}/api/visualization/reference-sources`)
    if (!response.ok) throw new Error(`Server returned HTTP ${response.status}`)
    return await response.json()
  } catch (error) {
    return {
      providers: [],
      curated_domains: [],
      error: error.message,
    }
  }
}

/**
 * Run multi-model vision-assisted 3D visualization pipeline
 */
export async function runVisualizationPipeline(topic, domain = null, userRefUrl = null) {
  try {
    const response = await fetch(`${API_BASE}/api/visualization/pipeline-run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        topic,
        domain: domain || undefined,
        user_reference_url: userRefUrl || undefined,
      }),
    })
    if (!response.ok) throw new Error(`Server returned HTTP ${response.status}`)
    return await response.json()
  } catch (error) {
    throw new Error(`Visualization pipeline failed: ${error.message}`)
  }
}

/**
 * Stream multi-model visualization pipeline progress events
 */
export async function streamVisualizationPipeline(topic, domain = null, userRefUrl = null) {
  const response = await fetch(`${API_BASE}/api/visualization/pipeline-stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      topic,
      domain: domain || undefined,
      user_reference_url: userRefUrl || undefined,
    }),
  })
  if (!response.ok) {
    throw new Error(`Server returned HTTP ${response.status}`)
  }
  return response
}

