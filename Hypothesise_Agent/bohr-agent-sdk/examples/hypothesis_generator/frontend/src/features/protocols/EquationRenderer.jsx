import { useEffect, useRef } from 'react'
import katex from 'katex'
import 'katex/dist/katex.min.css'

function EquationRenderer({ math, block = false, className = '' }) {
  const containerRef = useRef(null)

  useEffect(() => {
    if (containerRef.current && math) {
      try {
        katex.render(math, containerRef.current, {
          displayMode: block,
          throwOnError: false,
          output: 'htmlAndMathml',
        })
      } catch (err) {
        console.warn('KaTeX rendering error:', err)
        containerRef.current.innerText = math
      }
    }
  }, [math, block])

  return <span ref={containerRef} className={`equation-rendered ${className}`} />
}

export default EquationRenderer

