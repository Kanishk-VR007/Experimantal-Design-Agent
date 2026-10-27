# Simulation Agent Installation & Usage Guide

## 📦 Installation

### 1. Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
```

**Required packages:**
- numpy
- scipy
- pydantic
- fastapi
- uvicorn

**Optional packages (for enhanced functionality):**
```bash
# For chemistry simulations
pip install rdkit-pypi

# For biology simulations
pip install biopython

# For LLM fallback (if not using Ollama)
pip install anthropic
```

### 2. Frontend Dependencies

```bash
cd frontend
npm install
```

This will install:
- react-plotly.js (for interactive plots)
- plotly.js (graphing library)

## 🚀 Usage

### Starting the System

1. **Start Ollama** (if not already running):
```bash
ollama serve
```

2. **Start Backend**:
```bash
cd backend
python server.py
```

3. **Start Frontend**:
```bash
cd frontend
npm run dev
```

4. **Access the UI**:
Open http://localhost:5173 in your browser

### Workflow

1. **Generate Experimental Design**:
   - Enter your research topic
   - Click "Generate Design"
   - Wait for Ollama to stream the experimental design

2. **Run Simulation**:
   - After the design is complete, click "▶️ Run Simulation"
   - The system will:
     - Parse the experimental design
     - Detect the domain (chemistry/biology/physics)
     - Route to the appropriate simulation engine
     - Generate numerical results and plots

3. **View Results**:
   - Interactive plots (zoom, pan, hover)
   - Numerical results
   - Observations and insights
   - Confidence scores
   - Detailed simulation logs

## 🧪 Supported Domains

### Chemistry
- Reaction kinetics (Arrhenius model)
- Molecular property analysis (requires RDKit)
- Titration curves
- **Parameters**: temperature, concentration, activation energy

### Biology
- Bacterial growth (logistic model)
- Gene expression dynamics
- Population dynamics
- **Parameters**: growth rate, carrying capacity, time

### Physics
- Pendulum motion (damped oscillation)
- RLC circuits
- Projectile motion
- **Parameters**: length, damping, voltage, resistance

### General
- Uses LLM fallback (Ollama/Claude)
- Generates synthetic simulation data
- Works for any domain

## 🔧 Configuration

### Environment Variables
Create a `.env` file in the backend directory:

```env
# Ollama Configuration
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3

# Optional: Claude API for fallback
ANTHROPIC_API_KEY=your_key_here
```

### Customizing Simulation Parameters

Edit `simulation_agent/agent.py` → `extract_procedure_from_text()` to modify default parameters for each domain.

## 📊 Output Files

Simulations are saved to:
```
output/simulation_<topic>_<timestamp>.json
```

Contains:
- Full simulation results
- Plot data
- Numerical metrics
- Confidence scores
- Logs

## 🐛 Troubleshooting

### "Module not found" errors
```bash
# Ensure all dependencies installed
pip install -r requirements.txt
npm install
```

### RDKit import errors (chemistry)
```bash
# Chemistry simulations work without RDKit, but with limited features
# To enable full chemistry support:
pip install rdkit-pypi
```

### Plots not rendering
```bash
# Ensure plotly packages installed
npm install react-plotly.js plotly.js
```

### Ollama connection errors
- Ensure Ollama is running: `ollama serve`
- Check `OLLAMA_URL` in `.env`
- Test with: `curl http://localhost:11434/api/tags`

## 🌟 Advanced Usage

### Custom Simulation Engines

Add new engines in `simulation_agent/engines/`:

```python
# my_custom_engine.py
def run(procedure: dict) -> dict:
    return {
        "numerical_results": {...},
        "plot_data": [...],
        "observations": [...],
        "confidence_score": 0.85,
        "simulation_log": [...]
    }
```

Register in `router.py`:
```python
from .engines import my_custom_engine

DOMAIN_MAP = {
    "custom_domain": my_custom_engine.run,
    # ...
}
```

## 📝 API Endpoints

### POST /api/run-simulation
```json
{
  "topic": "your research topic",
  "design": "experimental design text from Ollama",
  "domain": "chemistry"  // optional, auto-detected
}
```

**Response:**
```json
{
  "success": true,
  "simulation": {
    "status": "success",
    "engine_used": "chem_sim",
    "plot_data": [...],
    "numerical_results": {...},
    ...
  }
}
```

## 🎯 Next Steps

- **Layer 4**: Add Analysis Agent for statistical analysis
- **Export**: Add PDF/LaTeX report generation
- **Validation**: Compare simulations with real experimental data
- **Optimization**: Parameter optimization for experiments
