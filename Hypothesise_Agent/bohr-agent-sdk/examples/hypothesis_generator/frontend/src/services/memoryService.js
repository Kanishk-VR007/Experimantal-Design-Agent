/* ══════════════════════════════════════════════════════════════
   MEMORY SERVICE — Hypothesise Agent
   Continuous Memory Agent Integration (SQLite & EMA Weights)
   ══════════════════════════════════════════════════════════════ */

import { MEMORY_API_BASE } from './apiClient'

/**
 * Fetch memory agent overall accuracy report
 */
export async function getAccuracyReport() {
  try {
    const res = await fetch(`${MEMORY_API_BASE}/improve/accuracy-report`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    return await res.json()
  } catch (err) {
    console.warn('[memoryService] accuracy-report fetch error:', err.message)
    return null
  }
}

/**
 * Fetch layer feedback scores (EMA weights)
 */
export async function getFeedbackScores() {
  try {
    const res = await fetch(`${MEMORY_API_BASE}/improve/feedback-scores`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    return await res.json()
  } catch (err) {
    console.warn('[memoryService] feedback-scores fetch error:', err.message)
    return null
  }
}

/**
 * Fetch accuracy history trends
 */
export async function getAccuracyHistory() {
  try {
    const res = await fetch(`${MEMORY_API_BASE}/improve/accuracy-history`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    return await res.json()
  } catch (err) {
    console.warn('[memoryService] accuracy-history fetch error:', err.message)
    return null
  }
}

/**
 * Fetch domain breakdown statistics
 */
export async function getDomainBreakdown() {
  try {
    const res = await fetch(`${MEMORY_API_BASE}/improve/domain-breakdown`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    return await res.json()
  } catch (err) {
    console.warn('[memoryService] domain-breakdown fetch error:', err.message)
    return null
  }
}

/**
 * Submit feedback to Memory Agent
 */
export async function submitFeedback(payload) {
  const res = await fetch(`${MEMORY_API_BASE}/improve/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return await res.json()
}

/**
 * Run improvement cycle to recalculate weights
 */
export async function runImprovementCycle() {
  const res = await fetch(`${MEMORY_API_BASE}/improve/run-cycle`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return await res.json()
}
