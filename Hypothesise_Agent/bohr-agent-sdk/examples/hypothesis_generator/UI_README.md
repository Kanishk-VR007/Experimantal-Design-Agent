# Experimental Design Agent - React UI

A modern, interactive web interface for the Experimental Design Agent built with React and FastAPI.

## Features

- 🔬 **Interactive UI**: Modern React interface with real-time updates
- ⚡ **Live Streaming**: Watch experimental designs generate in real-time
- 📚 **Paper Analysis**: View and analyze research papers from Bohrium
- 🎯 **Smart Generation**: Powered by Ollama's LLM (llama3)
- 💾 **Export Options**: Download or copy generated designs
- 🎨 **Beautiful Design**: Dark theme with smooth animations

## Architecture

```
frontend/          # React + Vite application
  ├── src/
  │   ├── components/
  │   │   ├── ExperimentForm.jsx    # Input form
  │   │   ├── ExperimentOutput.jsx  # Results display
  │   │   └── StatusBar.jsx         # System status
  │   ├── App.jsx
  │   └── main.jsx
  └── package.json

backend/           # FastAPI server
  ├── server.py                     # Main API server
  └── requirements.txt

launch.py          # All-in-one launcher script
```

## Prerequisites

1. **Python 3.8+**
   ```bash
   python --version
   ```

2. **Node.js 18+**
   ```bash
   node --version
   ```

3. **Ollama** (Required for generation)
   ```bash
   # Install from: https://ollama.ai
   ollama serve
   ollama pull llama3
   ```

## Quick Start

### Option 1: Automated Launch (Recommended)

```bash
# Install backend dependencies
pip install -r backend/requirements.txt

# Run the launcher (installs frontend deps automatically)
python launch.py
```

The launcher will:
- ✅ Check all dependencies
- ✅ Install frontend packages (first run)
- ✅ Start backend server (port 8000)
- ✅ Start frontend dev server (port 3000)
- ✅ Open your browser automatically

### Option 2: Manual Launch

**Terminal 1 - Backend:**
```bash
cd backend
pip install -r requirements.txt
python server.py
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## Usage

1. **Open the App**: Navigate to http://localhost:3000

2. **Check Status**: Ensure the status bar shows "System Ready" (green)

3. **Enter Research Topic**: 
   - Type your research question
   - Or click an example topic

4. **Configure Options**:
   - Max Papers: Number of papers to analyze (1-10)
   - Use Mock Data: Enable for faster testing

5. **Generate Design**: 
   - Click "Generate Design"
   - Watch real-time streaming output
   - View analyzed papers and generated design

6. **Export Results**:
   - Copy to clipboard
   - Download as markdown file

## API Endpoints

### Backend Server (http://localhost:8000)

- `GET /health` - Check system health
- `POST /api/search-papers` - Search research papers
- `POST /api/generate-design` - Generate experimental design (SSE stream)

### Interactive API Documentation

Visit http://localhost:8000/docs for Swagger UI documentation.

## Example Topics

- "Effect of dropout on CNN accuracy for image classification"
- "Compare CNN vs Transformer models on CIFAR-10"
- "LSTM vs GRU for time series prediction"
- "Impact of batch normalization on deep learning performance"
- "Comparison of optimization algorithms for neural networks"

## Configuration

### Backend (.env file)

Create a `.env` file in the project root:

```bash
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3
OLLAMA_TEMPERATURE=0.3
```

### Frontend (vite.config.js)

Modify port or proxy settings:

```javascript
export default defineConfig({
  server: {
    port: 3000,  // Change frontend port
    proxy: {
      '/api': 'http://localhost:8000'  // Backend URL
    }
  }
})
```

## Troubleshooting

### "Cannot connect to backend server"
- Ensure backend is running on port 8000
- Check `http://localhost:8000/health`

### "⚠️ Ollama is not running"
- Start Ollama: `ollama serve`
- Check `http://localhost:11434/api/tags`

### "Frontend won't start"
- Delete `node_modules` and run `npm install` again
- Check if port 3000 is available

### "Generation times out"
- Increase timeout in backend/server.py (default: 300s)
- Use a faster model or simpler prompts
- Check Ollama logs

### Port conflicts
- Change backend port in `server.py`: `uvicorn.run(app, port=8001)`
- Change frontend port in `vite.config.js`

## Development

### Frontend Development

```bash
cd frontend
npm run dev      # Start dev server with hot reload
npm run build    # Build for production
npm run preview  # Preview production build
```

### Backend Development

```bash
cd backend
pip install -r requirements.txt
uvicorn server:app --reload  # Auto-reload on changes
```

### Adding Features

**New Frontend Component:**
```javascript
// frontend/src/components/MyComponent.jsx
function MyComponent() {
  return <div>Hello World</div>
}
export default MyComponent
```

**New Backend Endpoint:**
```python
# backend/server.py
@app.get("/api/my-endpoint")
async def my_endpoint():
    return {"message": "Hello"}
```

## Technology Stack

### Frontend
- **React 18**: UI framework
- **Vite**: Build tool & dev server
- **React Markdown**: Render markdown output
- **CSS3**: Custom styling with CSS variables

### Backend
- **FastAPI**: Modern Python web framework
- **Uvicorn**: ASGI server
- **Server-Sent Events**: Real-time streaming
- **Requests**: HTTP client for Ollama/Bohrium

### AI/ML
- **Ollama**: Local LLM inference
- **llama3**: Language model
- **Bohrium API**: Research paper database

## Performance

- **Backend**: Handles streaming with minimal overhead
- **Frontend**: Renders chunks progressively as they arrive
- **Generation Time**: 2-3 minutes for detailed designs
- **Memory**: ~500MB for backend, ~100MB for frontend

## Security Notes

- CORS enabled for `localhost:3000` and `localhost:5173`
- No authentication (local development only)
- Don't expose publicly without adding auth

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

MIT License - See LICENSE file for details

## Support

For issues or questions:
- Check troubleshooting section above
- Review API docs at http://localhost:8000/docs
- Check Ollama documentation at https://ollama.ai

## Roadmap

- [ ] User authentication
- [ ] Save/load experiments
- [ ] Compare multiple designs
- [ ] Export to PDF
- [ ] Integration with more paper databases
- [ ] Support for more LLM models

---

**Built with ❤️ using React, FastAPI, and Ollama**
