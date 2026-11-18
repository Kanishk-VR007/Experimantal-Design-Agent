import { useState, useEffect, useRef, useCallback } from 'react'
import { fetchHealth } from '../services/apiClient'

/**
 * Polls /health (every 5s while disconnected, every 30s when healthy)
 * and exposes `refresh` / `checkHealth` for manual refresh.
 */
export function useBackendHealth() {
  const [status, setStatus] = useState({
    loading: true,
    healthy: false,
    backendHealthy: false,
    llmHealthy: false,
    memoryHealthy: false,
  })
  const timerRef = useRef(null)

  const checkHealth = useCallback(async () => {
    const result = await fetchHealth()
    setStatus(result)
    return result
  }, [])

  useEffect(() => {
    let cancelled = false
    const poll = async () => {
      const result = await checkHealth()
      if (!cancelled) {
        const nextMs = result?.backendHealthy ? 30000 : 5000
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
