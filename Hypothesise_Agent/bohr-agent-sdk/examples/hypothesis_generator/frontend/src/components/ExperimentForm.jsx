import { useState } from 'react'

const EXAMPLE_TOPICS = [
  "Effect of dropout on CNN accuracy for image classification",
  "Compare CNN vs Transformer models on CIFAR-10",
  "LSTM vs GRU for time series prediction",
  "Impact of batch normalization on deep learning performance",
  "Comparison of optimization algorithms for neural networks"
]



function ExperimentForm({ onGenerate, generating, disabled }) {
  const [topic, setTopic] = useState('')
  const [maxPapers, setMaxPapers] = useState(3)
  const [useMockData, setUseMockData] = useState(false)
  const handleSubmit = (e) => {
    e.preventDefault()
    if (topic.trim()) {
      onGenerate({
        topic: topic.trim(),
        maxPapers,
        useMockData
      })
    }
  }

  const loadExample = (exampleTopic) => {
    setTopic(exampleTopic)
  }

  return (
    <div className="experiment-form">
      <h2>Design Parameters</h2>

      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="topic">Research Topic *</label>
          <textarea
            id="topic"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="Enter your research question or experiment description..."
            rows={4}
            required
            disabled={disabled || generating}
          />
        </div>

        <div className="form-group">
          <label htmlFor="maxPapers">Max Papers</label>
          <input
            type="number"
            id="maxPapers"
            value={maxPapers}
            onChange={(e) => setMaxPapers(parseInt(e.target.value))}
            min={1}
            max={10}
            disabled={disabled || generating}
          />
          <small>Number of research papers to analyze</small>
        </div>

        <div className="form-group checkbox-group">
          <label>
            <input
              type="checkbox"
              checked={useMockData}
              onChange={(e) => setUseMockData(e.target.checked)}
              disabled={disabled || generating}
            />
            <span>Use mock data (faster, for testing)</span>
          </label>
        </div>

        <button 
          type="submit" 
          className="btn-primary"
          disabled={disabled || generating || !topic.trim()}
        >
          {generating ? (
            <>
              <span className="spinner"></span>
              Generating...
            </>
          ) : (
            <>
              🚀 Generate Design
            </>
          )}
        </button>
      </form>

      <div className="examples">
        <h3>Example Topics</h3>
        <div className="example-list">
          {EXAMPLE_TOPICS.map((example, index) => (
            <button
              key={index}
              className="example-btn"
              onClick={() => loadExample(example)}
              disabled={disabled || generating}
            >
              {example}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

export default ExperimentForm
