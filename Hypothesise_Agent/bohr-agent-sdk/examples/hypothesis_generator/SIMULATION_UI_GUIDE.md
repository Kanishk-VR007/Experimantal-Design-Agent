# Simulation UI Guide

## Overview
The simulation interface has been restructured to provide a better user experience with separated concerns:
- **SimulationRunner**: Handles the execution process with real-time feedback
- **SimulationResults**: Displays final results with interactive visualizations

## Architecture

### Three-View System

1. **Experimental Design View** (Default)
   - Shows research papers and generated experimental design
   - Contains "Run Simulation" button when design is complete
   - Always accessible via toggle button

2. **Simulation Execution (Modal Overlay)**
   - Appears when "Run Simulation" is clicked
   - Shows real-time progress (0-100%)
   - Displays simulation logs as they occur
   - Status indicators: Initializing → Running → Success/Error
   - Can be closed manually with "Close" button

3. **Simulation Report View**
   - Accessible via toggle button after simulation completes
   - Interactive Plotly charts
   - Numerical results table
   - Confidence scores
   - Collapsible execution logs

## User Flow

```
1. User generates experimental design
   ↓
2. User clicks "Run Simulation" button
   ↓
3. SimulationRunner overlay appears
   - Shows progress bar
   - Streams real-time logs
   - Displays current status
   ↓
4. On completion:
   - User closes SimulationRunner
   - View automatically switches to "Simulation Report"
   ↓
5. User can toggle between views:
   - "📄 Experimental Design" 
   - "🔬 Simulation Report"
```

## Component Details

### App.jsx
**State Management:**
- `showSimulationRunner`: Boolean controlling modal visibility
- `simulation`: Stores simulation results
- `activeView`: Switches between 'design' and 'simulation' views

**Key Functions:**
- `handleRunSimulation()`: Opens SimulationRunner modal, switches to simulation view
- `handleSimulationComplete(data)`: Stores results from SimulationRunner
- `handleCloseSimulationRunner()`: Closes the modal

### SimulationRunner.jsx (Modal Overlay)
**Features:**
- Glassmorphism dark overlay (rgba(0, 0, 0, 0.85))
- Animated progress bar with gradient
- Real-time log streaming
- Status states: initializing → running → success → error
- Simulation metadata cards (topic, engine, domain, confidence)

**Props:**
- `topic`: Research topic string
- `design`: Experimental design text
- `onSimulationComplete(data)`: Callback with results
- `onClose()`: Close handler

**Styling:** SimulationRunner.css (393 lines)
- Cyan accent color (#00d9ff)
- Smooth animations (fadeIn, slideUp, shimmer)
- Responsive design
- Dark theme integration

### SimulationResults.jsx (Results Display)
**Features:**
- Interactive Plotly.js charts
- Confidence score with color-coded badges
- Numerical results grid
- Collapsible logs section
- Domain detection badge

**Props:**
- `simulation`: Complete simulation object from API

**Styling:** SimulationResults.css
- Matches app theme
- Grid layout for numerical results
- Responsive plot container

### ExperimentOutput.jsx
**Changes:**
- Removed `simulationRunning` prop
- Added `hasSimulation` prop
- Button text changes based on simulation existence:
  - "▶️ Run Simulation" (first run)
  - "🔄 Re-run Simulation" (subsequent runs)

## View Toggle (App.css)
**Styles:**
- `.view-toggle`: Container with glassmorphism effect
- `.toggle-btn`: Flex-grow buttons with hover effects
- `.toggle-btn.active`: 
  - Gradient background
  - Cyan glow
  - Bottom border indicator
  - Text shadow effect

## API Integration

**Endpoint:** `POST /api/run-simulation`

**Request Body:**
```json
{
  "topic": "string",
  "design": "string",
  "domain": null  // Auto-detected
}
```

**Response:**
```json
{
  "simulation": {
    "domain": "string",
    "engine": "string",
    "hypothesis": "string",
    "methodology": "string",
    "plots": [...],
    "numerical_results": {...},
    "logs": [...],
    "confidence": 0.0-1.0
  }
}
```

## Error Handling

### Backend Errors
- NameError fixed: `line_lower` variable properly scoped in agent.py
- Import errors resolved: All simulation engines properly imported

### Frontend Errors
- Network failures: Shows error alert in SimulationRunner
- Server errors (500): Displays in status section with retry option
- JSX syntax errors: Fixed malformed export statement in App.jsx

## Testing Checklist

✅ **Fixed Issues:**
- [x] NameError: line_lower undefined (agent.py line 49)
- [x] JSX syntax error in App.jsx
- [x] Duplicate code in App.jsx export statement
- [x] Missing dependencies (plotly.js, react-plotly.js)
- [x] Python 3.13 compatibility (numpy 2.4.2, scipy 1.17.1)

✅ **Active Components:**
- [x] Backend running on port 8000 (PID 25500)
- [x] Frontend running on port 3000 (PID 16040)
- [x] No TypeScript/ESLint errors
- [x] All imports resolving correctly

🔄 **To Test:**
1. Generate experimental design
2. Click "Run Simulation"
3. Verify SimulationRunner overlay appears
4. Check real-time progress updates
5. Confirm simulation completes without errors
6. Close SimulationRunner
7. Verify automatic switch to "Simulation Report" view
8. Toggle between Design and Report views
9. Test "Re-run Simulation" functionality

## Future Enhancements

**Potential improvements:**
- Pause/resume simulation capability
- Export simulation results to JSON/CSV
- Side-by-side comparison of multiple simulations
- Simulation history panel
- Real-time parameter adjustment
- WebSocket connection for faster log streaming
- Simulation queue for batch processing

## File Structure

```
frontend/src/
├── App.jsx                          # Main component with view management
├── App.css                          # Includes view toggle styles
└── components/
    ├── ExperimentForm.jsx           # Input form
    ├── ExperimentOutput.jsx         # Design display + Run button
    ├── SimulationRunner.jsx         # 🆕 Modal execution overlay
    ├── SimulationRunner.css         # 🆕 Modal styling
    ├── SimulationResults.jsx        # Results visualization
    ├── SimulationResults.css        # Results styling
    └── StatusBar.jsx                # Backend health indicator

backend/
├── server.py                        # FastAPI with /api/run-simulation endpoint
└── simulation_agent/
    ├── agent.py                     # Fixed: line_lower variable scope
    ├── router.py                    # Domain detection & engine routing
    ├── schema.py                    # Pydantic models
    ├── output_formatter.py          # Result normalization
    └── engines/
        ├── chem_sim.py              # Chemistry simulations
        ├── bio_sim.py               # Biology simulations
        ├── physics_sim.py           # Physics simulations
        └── llm_fallback.py          # General-domain LLM fallback
```

## Dependencies

**Python (requirements.txt):**
- fastapi>=0.115.0
- uvicorn>=0.30.0
- numpy>=1.26.0  # Python 3.13 compatible
- scipy>=1.14.0
- pydantic>=2.10.0
- ollama>=0.1.0

**JavaScript (package.json):**
- react: ^18.2.0
- plotly.js: ^2.35.3
- react-plotly.js: ^2.6.0

## Troubleshooting

**Issue:** Internal Server Error 500
**Solution:** Check backend logs for NameError or ImportError (fixed in agent.py)

**Issue:** Simulation button disabled
**Solution:** Ensure experimental design generation completes successfully

**Issue:** Plots not rendering
**Solution:** Verify plotly.js and react-plotly.js installed (`npm list`)

**Issue:** Server not responding
**Solution:** Check ports 8000 and 3000 availability (`netstat -ano | Select-String ":8000|:3000"`)

## Support

For issues or questions:
1. Check browser console for frontend errors
2. Check backend terminal for Python tracebacks
3. Verify all dependencies installed
4. Ensure Ollama service running on localhost:11434
5. Review SIMULATION_AGENT_GUIDE.md for engine details
