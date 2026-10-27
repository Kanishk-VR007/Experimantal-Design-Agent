"""
Memory Agent — FastAPI Service
================================
Runs on port 8001 (independent of the existing backend on port 8000).

Start:
    cd memory_agent
    uvicorn main:app --reload --port 8001

Or use the helper script:
    python main.py
"""

import sys
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ── Make sure `core/` and `routers/` are importable when running from this dir ──
sys.path.insert(0, os.path.dirname(__file__))

from core.feedback   import init_feedback_db
from core.embedder   import get_embedder
from core            import chromadb_store as cloud_db
from routers         import improve


# ── Lifespan ───────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[Memory Agent] Starting up...")

    # Warm up embedder (stub by default — replace core/embedder.py for real one)
    get_embedder()

    # Initialise SQLite feedback tables (idempotent)
    init_feedback_db()
    print("[Memory Agent] OK: Feedback DB initialised")

    # Optional: cloud vector store
    if cloud_db.cloud_available():
        print("[Memory Agent] OK: Cloud vector store connected")
    else:
        print("[Memory Agent] WARN: Cloud vector store not configured — local-only mode")

    yield

    print("[Memory Agent] Shutting down...")


# ── App ────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title       = "Memory Agent — Iterative Improvement Service",
    description = (
        "Stores feedback scores for recalled memories, tracks per-layer "
        "pipeline accuracy over time, reweights retrieval, and generates "
        "improvement plans."
    ),
    version     = "1.0.0",
    lifespan    = lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────────

app.include_router(improve.router)


# ── Root health-check ──────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
async def root():
    return {
        "service" : "Memory Agent — Iterative Improvement",
        "status"  : "running",
        "docs"    : "/docs",
        "endpoints": [
            "POST /improve/feedback",
            "POST /improve/record-run-accuracy",
            "GET  /improve/accuracy-report",
            "GET  /improve/accuracy-history",
            "GET  /improve/domain-breakdown",
            "GET  /improve/feedback-scores",
            "POST /improve/run-cycle",
            "POST /improve/reweight",
            "GET  /improve/improvement-plan",
            "POST /improve/prune-memories",
        ],
    }


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
