import { useState, useEffect, useRef, useCallback } from 'react'
import { fetchHealth } from '../services/apiClient'

/**
 * Polls /health with latency tracking (every 5s while disconnected, every 15s when healthy)
 * and exposes `refresh` / `checkHealth` for manual refresh.
 */
export function useBackendHealth() {
  const [status, setStatus] = useState({
    loading: true,
    healthy: false,
    backendHealthy: false,
    llmHealthy: false,
    memoryHealthy: false,
    latencyMs: null,
  })
  const timerRef = useRef(null)

  const checkHealth = useCallback(async () => {
    const t0 = performance.now()
    const result = await fetchHealth()
    const t1 = performance.now()
    const latencyMs = Math.round(t1 - t0)
    const enriched = { ...result, latencyMs }
    setStatus(enriched)
    return enriched
  }, [])

  useEffect(() => {
    let cancelled = false
    const poll = async () => {
      const result = await checkHealth()
      if (!cancelled) {
        const nextMs = result?.backendHealthy ? 15000 : 5000
        timerRef.current = setTimeout(poll, nextMs)
      }
    }
    poll()
    return () => {
      cancelled = true
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [checkHealth])

  return { status, checkHealth, refresh: checkHealth }
}
