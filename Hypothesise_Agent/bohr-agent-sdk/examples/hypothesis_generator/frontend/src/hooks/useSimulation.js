import { useCallback } from 'react'
import { useExperimentStore } from '../stores/experimentStore'
import { runSimulation as runSimulationApi } from '../services/apiClient'

/**
 * Wraps runSimulation API call with store integration
 */
export function useSimulation() {
  const store = useExperimentStore

  const runSimulation = useCallback(async (topic, designText, refinementData = null, domainOverride = null) => {
    if (!designText || !designText.trim()) return
    store.getState().setSimulating(true)
    const activeDomain = domainOverride || store.getState().domain
    store.getState().addAgentEvent({
      type: 'simulation',
      message: `Starting numerical simulation solver (${activeDomain ? activeDomain.toUpperCase() : 'AUTO'})...`,
      severity: 'info',
    })
    try {
      const simulation = await runSimulationApi(topic, designText, activeDomain, refinementData)
      if (simulation) {
        store.getState().setSimulation(simulation)
        store.getState().addAgentEvent({
          type: 'simulation',
          message: 'Simulation generated successfully',
          severity: 'success',
        })
      }
    } catch (err) {
      console.error('Background simulation generation failed:', err)
      store.getState().addAgentEvent({
        type: 'simulation',
        message: `Simulation failed: ${err.message}`,
        severity: 'error',
      })
    } finally {
      store.getState().setSimulating(false)
    }
  }, [])

  return { runSimulation }
}
