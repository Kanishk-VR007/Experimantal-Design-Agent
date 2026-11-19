/* ══════════════════════════════════════════════════════════════
   EXPERIMENT SERVICE — Hypothesise Agent
   Hypothesis Formulation, Design Generation & Evaluation Reports
   ══════════════════════════════════════════════════════════════ */

import { API_BASE } from './apiClient'

/**
 * Search academic literature (arXiv & Semantic Scholar)
 */
export async function searchPapers(topic, maxPapers = 3, useMockData = false) {
  const response = await fetch(`${API_BASE}/api/search-papers`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ topic, max_papers: maxPapers, use_mock_data: useMockData }),
  })
  if (!response.ok) throw new Error(`Paper search failed: HTTP ${response.status}`)
  return await response.json()
}

/**
 * Initiate streaming experimental design generation (returns raw Response for SSE)
 */
export async function generateDesign(topic, maxPapers = 3, useMockData = false, domain = null) {
  const response = await fetch(`${API_BASE}/api/generate-design`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ topic, max_papers: maxPapers, use_mock_data: useMockData, domain }),
  })
  if (!response.ok) {
    throw new Error(`Design generation failed: HTTP ${response.status}`)
  }
  return response
}

/**
 * Refine prompt via Qwen3-4B-Thinking
 */
export async function refinePrompt(topic, domain = null) {
  const response = await fetch(`${API_BASE}/api/visualization/refine-prompt`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt: topic, domain }),
  })
  if (!response.ok) throw new Error(`Prompt refinement failed: HTTP ${response.status}`)
  return await response.json()
}

/**
 * List all saved evaluation reports from output directory
 */
export async function getEvalReports() {
  const response = await fetch(`${API_BASE}/api/eval-reports`)
  if (!response.ok) throw new Error(`Failed to list eval reports: HTTP ${response.status}`)
  return await response.json()
}

/**
 * Fetch a single evaluation report by run ID
 */
export async function getEvalReport(runId) {
  const response = await fetch(`${API_BASE}/api/eval-reports/${runId}`)
  if (!response.ok) throw new Error(`Failed to get eval report ${runId}: HTTP ${response.status}`)
  return await response.json()
}
