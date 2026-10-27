# Launch Experimental Design Agent UI
# This PowerShell script starts both backend and frontend servers

Write-Host ""
Write-Host "======================================================================"
Write-Host "  🚀 EXPERIMENTAL DESIGN AGENT - LAUNCHER"
Write-Host "======================================================================"
Write-Host ""

$ErrorActionPreference = "Stop"

# Check Python
Write-Host "Checking Python..." -NoNewline
try {
    $pythonVersion = python --version 2>&1
    Write-Host " ✅ $pythonVersion"
} catch {
    Write-Host " ❌ Python not found"
    Write-Host "Install Python from: https://python.org"
    exit 1
}

# Check Node.js
Write-Host "Checking Node.js..." -NoNewline
try {
    $nodeVersion = node --version 2>&1
    Write-Host " ✅ Node.js $nodeVersion"
} catch {
    Write-Host " ❌ Node.js not found"
    Write-Host "Install Node.js from: https://nodejs.org"
    exit 1
}

# Check Ollama
Write-Host "Checking Ollama..." -NoNewline
try {
    $ollamaCheck = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
    Write-Host " ✅ Ollama is running"
} catch {
    Write-Host " ⚠️  Ollama not running"
    Write-Host ""
    Write-Host "Start Ollama with:"
    Write-Host "  ollama serve"
    Write-Host ""
    Write-Host "The app will start but won't generate designs without Ollama."
    Write-Host ""
    $continue = Read-Host "Continue anyway? (y/n)"
    if ($continue -ne "y") {
        exit 1
    }
}

Write-Host ""
Write-Host "======================================================================"
Write-Host "  📦 INSTALLING DEPENDENCIES"
Write-Host "======================================================================"
Write-Host ""

# Install backend dependencies
Write-Host "Installing Python packages..."
Set-Location backend
pip install -q -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to install backend dependencies"
    exit 1
}
Set-Location ..
Write-Host "✅ Backend dependencies installed"

# Install frontend dependencies
if (!(Test-Path "frontend\node_modules")) {
    Write-Host ""
    Write-Host "Installing Node.js packages (this may take a few minutes)..."
    Set-Location frontend
    npm install
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to install frontend dependencies"
        exit 1
    }
    Set-Location ..
    Write-Host "✅ Frontend dependencies installed"
} else {
    Write-Host "✅ Frontend dependencies already installed"
}

Write-Host ""
Write-Host "======================================================================"
Write-Host "  🚀 STARTING SERVERS"
Write-Host "======================================================================"
Write-Host ""

# Start backend in background
Write-Host "Starting backend server..."
$backendJob = Start-Job -ScriptBlock {
    Set-Location $using:PWD
    Set-Location backend
    python server.py
}
Start-Sleep -Seconds 3

# Check if backend started
if ($backendJob.State -ne "Running") {
    Write-Host "❌ Backend failed to start"
    Receive-Job $backendJob
    exit 1
}
Write-Host "✅ Backend running on http://localhost:8000"

# Start frontend in background
Write-Host "Starting frontend server..."
$frontendJob = Start-Job -ScriptBlock {
    Set-Location $using:PWD
    Set-Location frontend
    npm run dev
}
Start-Sleep -Seconds 5

# Check if frontend started
if ($frontendJob.State -ne "Running") {
    Write-Host "❌ Frontend failed to start"
    Receive-Job $frontendJob
    Stop-Job $backendJob
    Remove-Job $backendJob
    exit 1
}
Write-Host "✅ Frontend running on http://localhost:3000"

Write-Host ""
Write-Host "======================================================================"
Write-Host "  🎉 ALL SYSTEMS RUNNING!"
Write-Host "======================================================================"
Write-Host ""
Write-Host "  Backend API:   http://localhost:8000"
Write-Host "  API Docs:      http://localhost:8000/docs"
Write-Host "  Frontend UI:   http://localhost:3000"
Write-Host ""
Write-Host "======================================================================"
Write-Host "  Press Ctrl+C to stop all servers"
Write-Host "======================================================================"
Write-Host ""

# Open browser
Start-Process "http://localhost:3000"

# Keep script running and monitor jobs
try {
    while ($true) {
        Start-Sleep -Seconds 1
        
        if ($backendJob.State -ne "Running") {
            Write-Host ""
            Write-Host "⚠️  Backend server stopped"
            break
        }
        
        if ($frontendJob.State -ne "Running") {
            Write-Host ""
            Write-Host "⚠️  Frontend server stopped"
            break
        }
    }
} finally {
    Write-Host ""
    Write-Host "🛑 Stopping servers..."
    Stop-Job $backendJob, $frontendJob -ErrorAction SilentlyContinue
    Remove-Job $backendJob, $frontendJob -ErrorAction SilentlyContinue
    Write-Host "✅ Servers stopped"
    Write-Host ""
}
