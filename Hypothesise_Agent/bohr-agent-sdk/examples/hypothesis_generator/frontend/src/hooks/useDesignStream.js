import { useCallback, useRef } from 'react'
import { useExperimentStore } from '../stores/experimentStore'
import { generateDesign } from '../services/apiClient'

/**
 * SSE stream handler preserving EXACT existing logic from App.jsx
 * Handles: start, status, papers, refinement, chunk, complete, error events
 */
export function useDesignStream() {
  const accumulatedRef = useRef('')
  const refinementRef = useRef(null)

  const store = useExperimentStore

  const startStream = useCallback(async (formData, onComplete) => {
    const { topic, maxPapers, useMockData, domain } = formData

    try {
      store.getState().setGenerating(true)
      store.getState().setSimulating(false)
      store.getState().setSimulation(null)
      store.getState().setDomain(domain || null)
      store.getState().updateOutput({
        papers: [],
        design: '',
        stage: 'Fetching & analyzing research papers...',
        refinement: null,
        streaming: true,
        complete: false,
        error: null,
      })

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
                stage: data.message || store.getState().stage,
              })
              store.getState().addAgentEvent({
                type: data.type,
                message: data.message || 'Stream event',
                severity: 'info',
              })
              break

            case 'papers':
              store.getState().updateOutput({
                papers: data.papers || [],
                stage: `Fetched ${(data.papers || []).length} papers — filtering stop words & refining prompt...`,
              })
              store.getState().addAgentEvent({
                type: 'papers',
                message: `Fetched ${(data.papers || []).length} research papers`,
                severity: 'info',
              })
              break

            case 'refinement':
              refinementRef.current = data.refinement || null
              store.getState().updateOutput({
                refinement: refinementRef.current,
              })
              store.getState().addAgentEvent({
                type: 'refinement',
                message: 'Prompt refinement applied',
                severity: 'info',
              })
              break

            case 'chunk':
              accumulatedRef.current += data.text || ''
              store.getState().updateOutput({
                design: accumulatedRef.current,
              })
              break

            case 'complete': {
              streamCompleted = true
              const finalText = (data.full_text || accumulatedRef.current || '').trim()
              if (!finalText) {
                store.getState().setGenerating(false)
                store.getState().updateOutput({
                  streaming: false,
                  complete: false,
                  error: 'Model completed without generating experimental context. Please retry.',
                })
                return
              }
              accumulatedRef.current = finalText
              store.getState().updateOutput({
                design: finalText,
                streaming: false,
                complete: true,
                stage: '',
              })
              store.getState().setGenerating(false)
              store.getState().addAgentEvent({
                type: 'complete',
                message: 'Design generation complete',
                severity: 'success',
              })
              if (onComplete) {
                onComplete(topic, finalText, refinementRef.current)
              }
              break
            }

            case 'error':
              streamErrored = true
              console.error('Error:', data.message)
              store.getState().setGenerating(false)
              store.getState().updateOutput({
                streaming: false,
                error: data.message,
              })
              store.getState().addAgentEvent({
                type: 'error',
                message: data.message,
                severity: 'error',
              })
              break
          }
        } catch (e) {
          console.error('Parse error:', e)
        }
      }

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

      // Guard in case stream closed without explicit complete/error event
      if (!streamErrored && !streamCompleted) {
        store.getState().setGenerating(false)
        if (accumulatedRef.current.trim()) {
          store.getState().updateOutput({ streaming: false, complete: true })
          if (onComplete) {
            onComplete(topic, accumulatedRef.current, refinementRef.current)
          }
        } else {
          store.getState().updateOutput({
            streaming: false,
            error: 'Stream ended before generating experimental context.',
          })
        }
      }
    } catch (error) {
      console.error('Generation error:', error)
      store.getState().setGenerating(false)
      store.getState().updateOutput({
        streaming: false,
        error: error.message,
      })
      store.getState().addAgentEvent({
        type: 'error',
        message: `Generation error: ${error.message}`,
        severity: 'error',
      })
    }
  }, [])

  return { startStream }
}
