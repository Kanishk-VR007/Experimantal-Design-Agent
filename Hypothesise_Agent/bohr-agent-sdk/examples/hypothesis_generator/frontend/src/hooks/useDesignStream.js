import { useCallback, useRef } from 'react'
import { useExperimentStore } from '../stores/experimentStore'
import { generateDesign } from '../services/apiClient'

/**
 * Authoritative SSE stream handler for experimental design generation.
 * Handles: start, status, papers, refinement, chunk, complete, error events.
 * Stamps every event with active currentRunId for strict session isolation.
 */
export function useDesignStream() {
  const accumulatedRef = useRef('')
  const refinementRef = useRef(null)

  const store = useExperimentStore

  const startStream = useCallback(async (formData, onComplete) => {
    const { topic, maxPapers, useMockData, domain } = formData

    // Authoritative new run initialization
    const runId = store.getState().startNewRun(topic, domain)
    store.getState().setGenerating(true)
    store.getState().setSimulating(false)
    store.getState().setDomain(domain || null)

    accumulatedRef.current = ''
    refinementRef.current = null
    let streamErrored = false
    let streamCompleted = false

    const processSseEvent = (line) => {
      if (!line.startsWith('data: ')) return
      try {
        const data = JSON.parse(line.slice(6))

        switch (data.type) {
          case 'start':
          case 'status':
            store.getState().updateOutput({
              run_id: runId,
              stage: data.message || store.getState().stage,
              executionStage: data.stage || 'reasoning',
            })
            store.getState().addAgentEvent({
              run_id: runId,
              type: data.type,
              message: data.message || 'Pipeline stage transition',
              stage: data.stage || 'reasoning',
              severity: 'info',
            })
            break

          case 'papers':
            store.getState().updateOutput({
              run_id: runId,
              papers: data.papers || [],
              stage: `Retrieved ${(data.papers || []).length} research papers from arXiv / Semantic Scholar`,
              executionStage: 'literature_search',
            })
            store.getState().addAgentEvent({
              run_id: runId,
              type: 'papers',
              message: `Fetched ${(data.papers || []).length} research papers`,
              count: (data.papers || []).length,
              severity: 'info',
            })
            break

          case 'refinement':
            refinementRef.current = data.refinement || data.data || null
            store.getState().updateOutput({
              run_id: runId,
              refinement: refinementRef.current,
              executionStage: 'prompt_refinement',
            })
            store.getState().addAgentEvent({
              run_id: runId,
              type: 'refinement',
              message: `Prompt refinement applied: ${data.refinement?.refined_experiment_prompt ? 'Domain priors injected' : 'Parameters grounded'}`,
              severity: 'info',
            })
            break

          case 'chunk':
            accumulatedRef.current += data.text || ''
            store.getState().updateOutput({
              run_id: runId,
              design: accumulatedRef.current,
              executionStage: 'experimental_design',
            })
            break

          case 'complete': {
            streamCompleted = true
            const finalText = (data.full_text || accumulatedRef.current || '').trim()
            if (!finalText) {
              store.getState().setGenerating(false)
              store.getState().updateOutput({
                run_id: runId,
                streaming: false,
                complete: false,
                executionStage: 'error',
                error: 'Model completed without generating experimental context. Please retry.',
              })
              return
            }
            accumulatedRef.current = finalText
            const completeness = data.design_completeness || null
            store.getState().updateOutput({
              run_id: runId,
              design: finalText,
              designCompleteness: completeness,
              streaming: false,
              complete: true,
              stage: 'Experimental design formulated successfully',
              executionStage: 'experimental_design',
            })
            store.getState().setGenerating(false)
            store.getState().addAgentEvent({
              run_id: runId,
              type: 'complete',
              message: `Design generation complete (${completeness ? `${completeness.found_headings}/${completeness.total_required} sections verified` : 'Complete'})`,
              severity: 'success',
            })
            if (onComplete) {
              onComplete(topic, finalText, refinementRef.current)
            }
            break
          }

          case 'error':
            streamErrored = true
            console.error('SSE Stream Error:', data.message)
            store.getState().setGenerating(false)
            store.getState().updateOutput({
              run_id: runId,
              streaming: false,
              executionStage: 'error',
              error: data.message,
            })
            store.getState().addAgentEvent({
              run_id: runId,
              type: 'error',
              message: data.message,
              severity: 'error',
            })
            break
        }
      } catch (e) {
        console.error('SSE parse error:', e)
      }
    }

    try {
      const response = await generateDesign(topic, maxPapers, useMockData, domain)
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          processSseEvent(line.trim())
        }
      }

      if (buffer.trim()) {
        processSseEvent(buffer.trim())
      }

      if (!streamErrored && !streamCompleted) {
        store.getState().setGenerating(false)
        if (accumulatedRef.current.trim()) {
          store.getState().updateOutput({ run_id: runId, streaming: false, complete: true })
          if (onComplete) {
            onComplete(topic, accumulatedRef.current, refinementRef.current)
          }
        } else {
          store.getState().updateOutput({
            run_id: runId,
            streaming: false,
            error: 'Stream ended before generating experimental context.',
          })
        }
      }
    } catch (error) {
      console.error('Generation stream error:', error)
      store.getState().setGenerating(false)
      store.getState().updateOutput({
        run_id: runId,
        streaming: false,
        executionStage: 'error',
        error: error.message,
      })
      store.getState().addAgentEvent({
        run_id: runId,
        type: 'error',
        message: `Generation stream error: ${error.message}`,
        severity: 'error',
      })
    }
  }, [])

  return { startStream }
}
