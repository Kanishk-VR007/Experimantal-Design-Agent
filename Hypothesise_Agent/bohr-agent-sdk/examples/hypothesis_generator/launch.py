#!/usr/bin/env python3
"""
Launch Script for Experimental Design Agent UI
===============================================
Starts both backend server and frontend React app.
"""

import os
import sys
import time
import subprocess
import signal
from pathlib import Path

# Get project directories
ROOT_DIR = Path(__file__).parent
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"
MEMORY_AGENT_DIR = ROOT_DIR / "memory_agent"

processes = []

def print_section(title):
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")

def cleanup():
    """Cleanup all spawned processes"""
    print("\n🛑 Shutting down servers...")
    for proc in processes:
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except:
            proc.kill()
    print("✅ Servers stopped\n")

def check_ollama():
    """Check if Ollama is running"""
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=3)
        if response.status_code == 200:
            return True
    except:
        pass
    return False

def check_dependencies():
    """Check if required dependencies are installed"""
    print_section("1️⃣  CHECKING DEPENDENCIES")
    
    # Check Python dependencies
    print("Checking Python packages...")
    try:
        import fastapi
        import uvicorn
        import requests
        print("✅ Python dependencies installed")
    except ImportError as e:
        print(f"❌ Missing Python package: {e}")
        print("\nInstall with:")
        print(f"  pip install -r {BACKEND_DIR}/requirements.txt")
        return False
    
    # Check Node.js
    print("\nChecking Node.js...")
    try:
        result = subprocess.run(
            ["node", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print(f"✅ Node.js {result.stdout.strip()}")
        else:
            print("❌ Node.js not found")
            return False
    except:
        print("❌ Node.js not found")
        print("\nInstall from: https://nodejs.org/")
        return False
    
    # Check Ollama
    print("\nChecking Ollama...")
    if check_ollama():
        print("✅ Ollama is running")
    else:
        print("⚠️  Ollama is not running")
        print("\nStart Ollama with:")
        print("  ollama serve")
        print("\nThe app will still start but won't generate designs.")
    
    return True

def install_frontend_deps():
    """Install frontend dependencies if needed"""
    if not (FRONTEND_DIR / "node_modules").exists():
        print_section("2️⃣  INSTALLING FRONTEND DEPENDENCIES")
        print("Installing Node.js packages (this may take a few minutes)...")
        
        try:
            subprocess.run(
                ["npm", "install"],
                cwd=FRONTEND_DIR,
                check=True
            )
            print("✅ Frontend dependencies installed")
        except subprocess.CalledProcessError:
            print("❌ Failed to install frontend dependencies")
            return False
    else:
        print_section("2️⃣  FRONTEND DEPENDENCIES")
        print("✅ Already installed")
    
    return True

def start_backend():
    """Start FastAPI backend server"""
    print_section("3️⃣  STARTING BACKEND SERVER")
    print("Starting FastAPI server on http://localhost:8000")
    
    try:
        # Set UTF-8 encoding for Windows compatibility
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        
        proc = subprocess.Popen(
            [sys.executable, "server.py"],
            cwd=BACKEND_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace',
            bufsize=1,
            env=env
        )
        processes.append(proc)
        
        # Wait for server to start
        print("⏳ Waiting for backend to start...")
        time.sleep(3)
        
        if proc.poll() is not None:
            print("❌ Backend failed to start")
            output = proc.stdout.read()
            print(output)
            return False
        
        print("✅ Backend server started")
        return True
        
    except Exception as e:
        print(f"❌ Failed to start backend: {e}")
        return False

def start_memory_agent():
    """Start Memory Agent FastAPI server"""
    print_section("3.5️⃣  STARTING MEMORY AGENT")
    print("Starting Memory Agent on http://localhost:8001")
    
    try:
        # Set UTF-8 encoding for Windows compatibility
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        
        proc = subprocess.Popen(
            [sys.executable, "main.py"],
            cwd=MEMORY_AGENT_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace',
            bufsize=1,
            env=env
        )
        processes.append(proc)
        
        # Wait for server to start
        print("⏳ Waiting for memory agent to start...")
        time.sleep(3)
        
        if proc.poll() is not None:
            print("❌ Memory agent failed to start")
            output = proc.stdout.read()
            print(output)
            return False
        
        print("✅ Memory agent started")
        return True
        
    except Exception as e:
        print(f"❌ Failed to start memory agent: {e}")
        return False

def start_frontend():
    """Start React frontend"""
    print_section("4️⃣  STARTING FRONTEND")
    print("Starting React app on http://localhost:3000")
    
    try:
        # Use shell=True on Windows for npm
        proc = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=FRONTEND_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace',
            bufsize=1,
            shell=True
        )
        processes.append(proc)
        
        print("⏳ Waiting for frontend to start...")
        time.sleep(3)
        
        if proc.poll() is not None:
            print("❌ Frontend failed to start")
            return False
        
        print("✅ Frontend started")
        return True
        
    except Exception as e:
        print(f"❌ Failed to start frontend: {e}")
        return False

def main():
    print("\n" + "="*70)
    print("🚀 EXPERIMENTAL DESIGN AGENT - LAUNCH SCRIPT")
    print("="*70)
    
    # Register cleanup handler
    signal.signal(signal.SIGINT, lambda s, f: (cleanup(), sys.exit(0)))
    signal.signal(signal.SIGTERM, lambda s, f: (cleanup(), sys.exit(0)))
    
    try:
        # Check dependencies
        if not check_dependencies():
            print("\n❌ Dependency check failed. Please fix the issues above.")
            return 1
        
        # Install frontend dependencies
        if not install_frontend_deps():
            return 1
        
        # Start backend
        if not start_backend():
            return 1
            
        # Start memory agent
        if not start_memory_agent():
            cleanup()
            return 1
        
        # Start frontend
        if not start_frontend():
            cleanup()
            return 1
        
        # Success
        print_section("🎉 ALL SYSTEMS RUNNING")
        print("Backend API:  http://localhost:8000")
        print("API Docs:     http://localhost:8000/docs")
        print("Memory Agent: http://localhost:8001")
        print("Frontend UI:  http://localhost:3000")
        print("\n" + "="*70)
        print("Press Ctrl+C to stop all servers")
        print("="*70 + "\n")
        
        # Keep running
        while True:
            time.sleep(1)
            # Check if processes are still alive
            for proc in processes:
                if proc.poll() is not None:
                    print("\n⚠️  A server process died unexpectedly")
                    cleanup()
                    return 1
    
    except KeyboardInterrupt:
        cleanup()
        return 0
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        cleanup()
        return 1

if __name__ == "__main__":
    sys.exit(main())
