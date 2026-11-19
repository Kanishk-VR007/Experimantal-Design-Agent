import { useState, useEffect } from 'react'
import { getModelStatus, pollModelStatus } from '../services/modelService'
import { useExperimentStore } from '../stores/experimentStore'

/**
 * Hook for live LM Studio 3-model status, sequential residency and GPU lock.
 */
export function useModelStatus(intervalMs = 3000) {
  const [modelStatus, setLocalModelStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const setStoreModelStatus = useExperimentStore((s) => s.setModelStatus)

  useEffect(() => {
    let mounted = true

    const unsubscribe = pollModelStatus((data) => {
      if (!mounted) return
      setLocalModelStatus(data)
      setStoreModelStatus(data)
      setLoading(false)
    }, intervalMs)

    return () => {
      mounted = false
      unsubscribe()
    }
  }, [intervalMs, setStoreModelStatus])

  return {
    modelStatus,
    loading,
    serverOnline: Boolean(modelStatus?.server_online),
    activeRole: modelStatus?.active_role_key || null,
    activeModelId: modelStatus?.active_model_id || null,
    roles: modelStatus?.roles || [],
    singleActivePolicy: Boolean(modelStatus?.single_active_model_policy),
  }
}
