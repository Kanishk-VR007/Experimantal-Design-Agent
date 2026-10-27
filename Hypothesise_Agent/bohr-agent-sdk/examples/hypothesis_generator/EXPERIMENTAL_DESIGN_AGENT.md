# 🔬 Experimental Design Agent

## What This Agent Does

The **Experimental Design Agent** is an AI-powered scientific advisor that helps researchers design complete, rigorous experiments from scratch. Unlike simple hypothesis generators, this agent:

1. **Reviews existing literature** from Bohrium Science Navigator
2. **Identifies research gaps** that need investigation  
3. **Designs full experimental protocols** with proper controls
4. **Defines all variables** (independent, dependent, control, confounding)
5. **Outlines step-by-step procedures** for conducting the experiment
6. **Recommends data analysis methods** and statistical tests
7. **Predicts outcomes** and potential limitations

## 🎯 Use Cases

Perfect for:
- **Graduate students** planning thesis experiments
- **Researchers** exploring new research directions
- **Scientists** designing pilot studies
- **Educators** teaching experimental design
- **R&D teams** validating experimental approaches

## 🔄 How It Works

```
User Input (Research Topic)
         ↓
   [Bohrium API Search]
         ↓
   📚 Fetch 3-5 Papers
         ↓
   [Ollama LLM Processing]
         ↓
   🧠 Generate Design
         ↓
   💾 Save JSON + Report
```

## 🚀 Quick Start

### Prerequisites

1. **Install Python dependencies:**
   ```bash
   pip install requests python-dotenv
   ```

2. **Install and run Ollama:**
   ```bash
   # Install from: https://ollama.ai
   ollama serve
   ollama pull llama3
   ```

### Basic Usage

```bash
cd examples/hypothesis_generator
python experimental_design_agent.py
```

You'll be prompted to enter your research topic:
```
🔍 Enter your research topic: Energy efficient neural networks for edge devices
```

### Command Line Usage

```bash
python experimental_design_agent.py "Your research topic here"
```

### Python Module Usage

```python
from experimental_design_agent import ExperimentalDesignAgent

# Initialize agent
agent = ExperimentalDesignAgent()

# Generate experimental design
results = agent.design_experiment(
    topic="Effect of learning rate on transformer convergence",
    max_papers=5,
    save_output=True
)

# Access results
print(results["experimental_design"])
print(f"Found {results['papers_found']} papers")
```

## 📊 Output Format

The agent generates two files in `output/`:

### 1. JSON File (Machine-Readable)
```json
{
  "topic": "Your research topic",
  "timestamp": "2026-02-28T10:30:00",
  "papers_found": 3,
  "papers": [...],
  "experimental_design": "...",
  "processing_time_seconds": 45.2,
  "model_used": "llama3"
}
```

### 2. Text Report (Human-Readable)
```
=====================================
EXPERIMENTAL DESIGN REPORT
=====================================

Topic: Your research topic
Generated: 2026-02-28 10:30:00
Papers Analyzed: 3
Model: llama3

LITERATURE SOURCES:
-------------------------------------
1. Paper Title Here
   Authors: Smith, J., Doe, A.
   Citations: 142
   
EXPERIMENTAL DESIGN:
-------------------------------------

## 1. RESEARCH GAP ANALYSIS
...

## 2. RESEARCH HYPOTHESIS
...

[Full experimental design]
```

## 🔧 Configuration

Create a `.env` file to customize settings:

```bash
# Ollama Configuration
OLLAMA_URL=http://localhost:11434/api/generate
OLLAMA_MODEL=llama3
OLLAMA_TEMPERATURE=0.3

# Optional: Use different models
# OLLAMA_MODEL=mistral
# OLLAMA_MODEL=codellama
# OLLAMA_MODEL=llama2
```

## 📋 Output Sections

The agent generates 9 comprehensive sections:

1. **Research Gap Analysis** - What's missing in current research
2. **Research Hypothesis** - Clear, testable hypothesis
3. **Experimental Variables** - IV, DV, controls, confounds
4. **Experimental Design** - Design type, sample size, groups
5. **Methodology & Procedures** - Step-by-step protocol
6. **Data Analysis Plan** - Statistical tests and metrics
7. **Expected Outcomes** - Predicted results and implications
8. **Limitations & Risks** - Potential issues and mitigation
9. **Ethical Considerations** - Ethics review requirements

## 🆚 Comparison with Other Tools

| Feature | Experimental Design Agent | hypo_agent.py | Basic Hypothesis Generator |
|---------|--------------------------|---------------|---------------------------|
| Literature review | ✅ Bohrium API | ✅ Bohrium + arXiv | ❌ |
| Hypothesis generation | ✅ | ✅ | ✅ |
| Full experimental protocol | ✅ | ❌ | ❌ |
| Variable definition | ✅ Detailed | ⚠️ Basic | ❌ |
| Statistical analysis plan | ✅ | ❌ | ❌ |
| Ethics considerations | ✅ | ❌ | ❌ |
| LLM backend | Ollama (local) | DeepSeek (cloud) | Any |

## 🛠️ Troubleshooting

### "Cannot connect to Ollama"
```bash
# Start Ollama server
ollama serve

# In another terminal, pull model
ollama pull llama3
```

### "No papers found"
- Check internet connection
- Try broader search terms
- The agent will still generate a design without papers

### "Request timeout"
- Increase timeout in code (line 215)
- Use a smaller/faster model
- Check Ollama is responding: `curl http://localhost:11434`

### "Empty response from Ollama"
- Model may not be loaded: `ollama list`
- Try: `ollama pull llama3`
- Restart Ollama service

## 🔬 Example Topics

Try these research topics:

```bash
# Machine Learning
python experimental_design_agent.py "Comparing attention mechanisms in transformer models"

# Biology
python experimental_design_agent.py "Effect of temperature on enzyme activity"

# Materials Science
python experimental_design_agent.py "Tensile strength of carbon fiber composites"

# Psychology
python experimental_design_agent.py "Impact of sleep deprivation on working memory"

# Chemistry
python experimental_design_agent.py "Catalyst optimization for CO2 reduction"
```

## 📚 Technical Details

### API Integration

**Bohrium Science Navigator API:**
- Endpoint: `https://bohrium.com/api/v1/paper/search`
- Method: GET (not POST!)
- Authentication: None required (public API)
- Rate limits: Unknown (use responsibly)

**Ollama API:**
- Endpoint: `http://localhost:11434/api/generate`
- Method: POST
- Streaming: Disabled for complete responses
- Timeout: 120 seconds

### Error Handling

The agent includes comprehensive error handling:
- ✅ Network timeouts
- ✅ Connection errors
- ✅ Malformed responses
- ✅ Missing data fields
- ✅ Empty results
- ✅ LLM failures

All errors are logged with helpful troubleshooting messages.

## 🤝 Contributing

To extend this agent:

1. **Add more paper sources** (e.g., PubMed, IEEE Xplore)
2. **Support cloud LLMs** (OpenAI, Anthropic, DeepSeek)
3. **Add visualization** of experimental design
4. **Export to LaTeX** for academic papers
5. **Integration with lab notebooks** (Jupyter, etc.)

## 📝 License

Part of the Bohrium Agent SDK - see main LICENSE file.

## 🔗 Related Files

- `hypo_agent.py` - Hypothesis generator using DeepSeek
- `dry_run_demo.py` - Test framework without API calls
- `house_price_hypothesis.py` - Specific domain example

---

**Created:** February 2026  
**Last Updated:** February 28, 2026  
**Maintainer:** Hypothesis Agent Team
