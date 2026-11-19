import { useCallback } from 'react'
import { useExperimentStore } from '../stores/experimentStore'
import { runSimulation as runSimulationApi } from '../services/apiClient'

/**
 * Wraps runSimulation API call with store integration and elapsed time measurement
 */
export function useSimulation() {
  const store = useExperimentStore

  const runSimulation = useCallback(async (topic, designText, refinementData = null, domainOverride = null) => {
    if (!designText || !designText.trim()) return
    store.getState().setSimulating(true)
    store.getState().setExecutionStage('ode_simulation')
    const activeDomain = domainOverride || store.getState().domain
    const runId = store.getState().currentRunId

    store.getState().addAgentEvent({
      run_id: runId,
      type: 'simulation',
      stage: 'ode_simulation',
      message: `Starting deterministic numerical solver (${activeDomain ? activeDomain.toUpperCase() : 'AUTO'})...`,
      severity: 'info',
    })

    const startTime = performance.now()

    try {
      const simulation = await runSimulationApi(topic, designText, activeDomain, refinementData)
      const elapsedSeconds = ((performance.now() - startTime) / 1000).toFixed(2)

      if (simulation) {
        store.getState().setSimulation(simulation)
        store.getState().updateOutput({
          run_id: runId,
          runElapsedTime: elapsedSeconds,
          executionStage: 'complete',
        })
        store.getState().addAgentEvent({
          run_id: runId,
          type: 'simulation',
          stage: 'complete',
          message: `Deterministic simulation completed in ${elapsedSeconds}s · Solver: ${simulation.solver?.name || 'SciPy ODE'} · Validation: ${simulation.validation?.overall_valid ? 'VALIDATED' : 'FLAGGED'}`,
          severity: 'success',
        })
      }
    } catch (err) {
      console.error('Simulation execution failed:', err)
      store.getState().updateOutput({
        run_id: runId,
        executionStage: 'error',
      })
      store.getState().addAgentEvent({
        run_id: runId,
        type: 'simulation',
        stage: 'error',
        message: `Simulation error: ${err.message}`,
        severity: 'error',
      })
    } finally {
      store.getState().setSimulating(false)
    }
  }, [])

  return { runSimulation }
}
