import { useState, useEffect, useRef, useCallback } from 'react'
import { fetchHealth } from '../services/apiClient'

/**
 * Polls /health every 30s, returns status object
 */
export function useBackendHealth() {
  const [status, setStatus] = useState({ loading: true })
  const intervalRef = useRef(null)

  const checkHealth = useCallback(async () => {
    const result = await fetchHealth()
    setStatus(result)
  }, [])

  useEffect(() => {
    checkHealth()
    intervalRef.current = setInterval(checkHealth, 30000)
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [checkHealth])

  return { status, checkHealth }
}
