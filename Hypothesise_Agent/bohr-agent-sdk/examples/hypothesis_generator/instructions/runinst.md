# How to Run the Hypothesise Agent Project

This guide outlines the steps to run the complete Hypothesise Agent system, including the backend, frontend, and memory agent. 

## Prerequisites

1. **Python 3.10+** (with a virtual environment activated)
2. **Node.js 18+** and **npm**
3. **Ollama** installed and running on your system with the `llama3.2` model.

## 1. Start the Backend API

The backend server is built with FastAPI and runs on port `8000`. It handles the core generation and simulations.

1. Open a new terminal.
2. Navigate to the `backend` directory:
   ```powershell
   cd "backend"
   ```
3. Run the server using `uvicorn`:
   ```powershell
   python -m uvicorn server:app --port 8000
   ```

*The backend will now be available at `http://localhost:8000/`. You can view the API documentation at `http://localhost:8000/docs`.*

## 2. Start the Frontend UI

The frontend is a React application built with Vite. By default, it tries to start on port `3000`. If ports `3000`, `3001`, and `3002` are in use, it will automatically start on `3003`. 

*(Note: The backend CORS settings have been updated to accept requests from ports `3000-3003`.)*

1. Open a second terminal.
2. Navigate to the `frontend` directory:
   ```powershell
   cd "frontend"
   ```
3. Start the Vite development server:
   ```powershell
   npm run dev
   ```

*Check your terminal output for the exact URL, which will typically be `http://localhost:3003/`.*

## 3. (Optional) Start the Memory Agent

The memory agent is a microservice running on port `8001` that records feedback scores, tracks accuracy, and dynamically reweights retrieval.

1. Open a third terminal.
2. Navigate to the `memory_agent` directory:
   ```powershell
   cd "memory_agent"
   ```
3. Start the memory agent:
   ```powershell
   python main.py
   ```

*The memory agent will be available at `http://localhost:8001/`.*

## Troubleshooting

- **Ollama Error: 404**: Ensure that your `.env` file specifies the correct model that you have installed locally (e.g., `OLLAMA_MODEL=llama3.2`). 
- **Cannot Connect to Backend**: Ensure that your frontend is running on one of the allowed CORS ports (`3000`, `3001`, `3002`, `3003`, or `5173`).
