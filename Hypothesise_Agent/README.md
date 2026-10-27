# 🔬 Hypothesise Agent: Autonomous Scientific Research & Experimentation Platform

[![Python Version](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue?logo=python)](https://www.python.org/)
[![React Version](https://img.shields.io/badge/React-18.2-61DAFB?logo=react)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![LangChain](https://img.shields.io/badge/LangChain-1.2.10-1C3C3C?logo=langchain)](https://www.langchain.com/)
[![Ollama](https://img.shields.io/badge/Ollama-LLaMA--3-black?logo=ollama)](https://ollama.ai/)
[![Claude Sonnet 4](https://img.shields.io/badge/Anthropic-Claude%20Sonnet%204-purple?logo=anthropic)](https://www.anthropic.com/)
[![DeepSeek](https://img.shields.io/badge/LLM-DeepSeek%20Chat-0066FF)](https://www.deepseek.com/)

> **Hypothesise Agent** is a full-lifecycle, multi-agent AI research platform that automates the scientific method. Given a natural-language research question or topic, the platform autonomously formulates testable hypotheses, conducts literature retrieval from scientific repositories, generates rigorous experimental protocols, executes domain-specific numerical simulations, computes statistical tests, audits for methodology bias, persists feedback-weighted memories, and generates publication-grade PDF and HTML peer-review reports.

---

## 📑 Table of Contents

- [1. Executive Summary & Vision](#1-executive-summary--vision)
- [2. Key Capabilities](#2-key-capabilities)
- [3. System Architecture](#3-system-architecture)
  - [3.1 High-Level Architecture](#31-high-level-architecture)
  - [3.2 Operational Modes](#32-operational-modes)
- [4. The 8-Layer Agent Pipeline (L1–L8)](#4-the-8-layer-agent-pipeline-l1l8)
- [5. Domain Simulation Engines (Layer 3)](#5-domain-simulation-engines-layer-3)
- [6. Frontend Web Application & Visualizers](#6-frontend-web-application--visualizers)
- [7. Self-Learning & Continuous Improvement (Layer 6)](#7-self-learning--continuous-improvement-layer-6)
- [8. Repository File Structure](#8-repository-file-structure)
- [9. Configuration & Environment Variables](#9-configuration--environment-variables)
- [10. Quick Start & Installation Guide](#10-quick-start--installation-guide)
  - [10.1 Prerequisites](#101-prerequisites)
  - [10.2 Automated Launch (Recommended)](#102-automated-launch-recommended)
  - [10.3 Manual Service Startup](#103-manual-service-startup)
  - [10.4 Running the 8-Layer Orchestrator (CLI)](#104-running-the-8-layer-orchestrator-cli)
  - [10.5 Offline & Dry-Run Modes](#105-offline--dry-run-modes)
- [11. REST API Specification](#11-rest-api-specification)
- [12. Key Engineering & Design Decisions](#12-key-engineering--design-decisions)
- [13. Troubleshooting & FAQs](#13-troubleshooting--faqs)
- [14. Roadmap & Future Enhancements](#14-roadmap--future-enhancements)
- [15. Authors & Acknowledgments](#15-authors--acknowledgments)

---

## 1. Executive Summary & Vision

Scientific discovery traditionally requires weeks of literature review, deep domain expertise to design robust experimental controls, and specialized equipment or costly compute to run simulations. 

**Hypothesise Agent** compresses this lifecycle from weeks to seconds by harmonizing:
1. **Real-time scientific literature grounding** (Bohrium Science Navigator, arXiv, Semantic Scholar).
2. **Local and cloud Large Language Models** (Ollama LLaMA-3 for zero-cost protocol generation, DeepSeek Chat for hypothesis synthesis, and Claude Sonnet 4 for high-order reasoning and peer review).
3. **Deterministic mathematical & physics simulation engines** (SciPy, NumPy, RDKit, ODE solvers) across eight scientific disciplines.
4. **Statistical analysis & Monte Carlo robustness auditing** to identify confounding factors and confirmation bias.
5. **Persistent self-learning memory** (SQLite + ChromaDB) that dynamically reweights retrieval based on experiment quality scores.

---

## 2. Key Capabilities

- 💡 **Natural-Language to Scientific Protocol**: Accepts plain-English queries (e.g., *"Does temperature affect enzyme reaction rates?"* or *"Design a simply supported beam under 10 kN/m load"*) and generates full scientific specifications.
- 📚 **Live Literature Retrieval**: Fetches open-access papers from **arXiv** and **Semantic Scholar** with author metadata, abstracts, and citation counts to anchor hypotheses in peer-reviewed research.
- ⚡ **Real-Time Token Streaming (SSE)**: Streams experimental designs character-by-character to a React frontend using Server-Sent Events.
- 🔬 **8 Domain Physics & Math Engines**: Deterministic numerical solvers for Chemistry, Biology, Physics, Computer Science, Civil Engineering, Mechanical Engineering, Electronics, and General LLM fallback.
- 📊 **Interactive CAD & Scientific Visualizers**: Custom React visualizers for circuit schematics, civil beam deflection/shear diagrams, mechanical stress tensors/Mohr's circle, chemistry test-tube racks, and Plotly.js charts.
- 🛡️ **Bias & Robustness Watchdog**: Uses Monte Carlo parameter perturbation (±10% over 20 iterations) to test result stability and flags methodology biases.
- 🔄 **Autonomous Quality Refinement Loop**: Layer 8 independently evaluates every layer's output; if the composite score is below 70%, the orchestrator synthesizes targeted fix instructions and reruns only the failing layers.
- 🧠 **Continuous Self-Improvement**: Tracks run accuracy in SQLite and uses Exponential Moving Average (EMA) to upweight successful memory embeddings in future experiments.
- 📄 **Publication-Ready Exports**: Generates styled PDF reports via ReportLab, interactive HTML dashboards, and Word documentation.

---

## 3. System Architecture

### 3.1 High-Level Architecture

The platform follows a layered, modular architecture where user interaction, backend orchestration, simulation engines, and persistence layers communicate over standard protocols:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             USER BROWSER                                    │
│       React 18 + Vite 5 SPA  (http://localhost:3000)                        │
│  - Live SSE Markdown Streamer       - CAD / Circuit / Beam Visualizers      │
│  - Interactive Plotly.js Charts     - L8 Evaluation Dashboard               │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ HTTP / REST / Server-Sent Events
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                    FASTAPI BACKEND  (http://localhost:8000)                  │
│  ├── POST /api/generate-design  ──► Streams Ollama LLaMA-3 output (SSE)     │
│  ├── POST /api/run-simulation   ──► Routes & invokes Domain Simulation Agent │
│  ├── GET  /api/search-papers    ──► arXiv & Semantic Scholar API Clients    │
│  └── GET  /api/eval-reports     ──► Serves L8 evaluation summaries          │
└──────────────────┬───────────────────────────────────────┬──────────────────┘
                   │ Direct Python Imports                 │ HTTP (Port 8001)
┌──────────────────▼──────────────────┐  ┌─────────────────▼──────────────────┐
│   LANGCHAIN RESEARCH ORCHESTRATOR   │  │        MEMORY AGENT SERVICE        │
│      orchestrator/pipeline.py       │  │       (http://localhost:8001)      │
│                                     │  │                                    │
│  [L1] Hypothesis Agent (DeepSeek)   │  │  - SQLite: memory_feedback.db      │
│  [L2] Architect Agent (LLaMA-3)     │  │  - Feedback scores & run accuracy  │
│  [L3] Simulation Agent (SciPy)      │  │  - EMA dynamic retrieval weights   │
│  [L4] Statistical Analysis (SciPy)  │  │  - Claude LangChain Improvement    │
│  [L5] Bias Auditor (Monte Carlo)    │  └─────────────────┬──────────────────┘
│  [L6] Memory Agent (ChromaDB)       │                    │
│  [L7] Review Agent (ReportLab PDF)  │                    │
│  [L8] Evaluator & Refinement Loop   │                    │
└──────────────────┬──────────────────┘                    │
                   │                                       │
    ┌──────────────┴───────────────┐                       │
    ▼                              ▼                       ▼
┌────────────────────────┐  ┌──────────────────┐  ┌───────────────────────────┐
│ Cloud Foundation LLMs  │  │ Local LLM Server │  │ Persistent Storage        │
│ - Claude Sonnet 4      │  │ - Ollama LLaMA-3 │  │ - ChromaDB Vector Store   │
│ - DeepSeek Chat        │  │   (Port 11434)   │  │ - SQLite (accuracy/scores)│
└────────────────────────┘  └──────────────────┘  └───────────────────────────┘
```

### 3.2 Operational Modes

The project supports three primary interaction patterns:

1. **Interactive Web Application**: Full full-stack experience. Users enter topics on the React UI, watch the experimental design stream live from Ollama, trigger simulations, and inspect interactive charts and blueprints.
2. **Autonomous Research Pipeline (CLI)**: Programmatic 8-layer orchestrator that executes end-to-end scientific workflows, audits results, triggers automated refinement, and outputs formatted PDF reports and HTML dashboards.
3. **Standalone Agent Tools & Dry-Run Mode**: Isolated CLI tools (`hypo_agent.py`, `experimental_design_agent.py`, `dry_run_demo.py`) that can run without network access or cloud API keys using deterministic mock datasets.

---

## 4. The 8-Layer Agent Pipeline (L1–L8)

All pipeline agents share a unified, serializable **`PipelineState`** (Pydantic model). State flows through each layer and can be saved, inspected, or restored at any point:

| Layer | Agent Name | Primary Engine / Model | Core Responsibilities | Key Outputs |
| :---: | :--- | :--- | :--- | :--- |
| **L1** | **Hypothesis Agent** | **DeepSeek Chat** / Claude Sonnet 4 | Searches prior hypotheses in ChromaDB to avoid duplication; fetches real papers from arXiv/Semantic Scholar; synthesizes 3–5 novel, testable hypotheses scored for novelty and testability. | `hypotheses[]`, `selected_hypothesis` |
| **L2** | **Experiment Architect** | **Ollama LLaMA-3** *(Claude fallback)* | Drafts comprehensive experimental methodology: independent/dependent/controlled variables, reagents (with SMILES strings), apparatus, step-by-step procedure, and safety notes. | `procedure{}` dict |
| **L3** | **Simulation Agent** | **SciPy / NumPy / RDKit** *(Claude/Ollama fallback)* | Keyword-routed domain classifier sends procedure to the appropriate physics/math engine. Generates numerical values, time-series data, observation notes, and confidence scores. | `simulation_result{}`, animation frames |
| **L4** | **Statistical Analysis Agent** | **SciPy & NumPy + Claude** | Computes descriptive statistics (mean, std, min, max), D'Agostino-Pearson normality tests, one-sample t-tests, and 95% confidence intervals. Interprets findings in scientific context. | `analysis_report{}`, `statistical_summary` |
| **L5** | **Bias & Robustness Auditor** | **NumPy Monte Carlo + Claude** | Perturbs input parameters ±10% over 20 runs to measure variance (CV < 0.15 = robust). Checks for confirmation bias, selection bias, and missing controls. Retries L2 if score < 0.40. | `audit_report{}`, `audit_score`, `retry_required` |
| **L6** | **Memory & Knowledge Agent** | **ChromaDB + SQLite** | Embeds complete run summaries using `all-MiniLM-L6-v2`. Retrieves semantically related historical experiments to identify recurring anomalies and longitudinal trends. | `recalled_context[]`, `memory_written` |
| **L7** | **Review & Evaluation Agent** | **Claude Sonnet 4 + ReportLab** | Virtual peer reviewer. Scores methodology, novelty, reproducibility, and impact (/10). Issues verdict (*accept*, *minor revision*, *major revision*, *reject*). Compiles publication PDF. | `review_verdict{}`, `pdf_path` |
| **L8** | **Evaluation & Refinement Loop** | **Claude Sonnet 4 + Rules Engine** | Independently evaluates L1–L7 against weighted rubric criteria. If overall score < 70%, generates targeted instruction patches and reruns failing layers (up to 3 cycles). | `eval_report{}`, `eval_passed`, `eval_dashboard.html` |

### Pipeline Quality Control Flowchart

```
[Start: Research Question]
         │
         ▼
[L1: Hypothesis Synthesis]
         │
         ▼
[L2: Experiment Protocol] ◄─────────────────────────────────────────┐
         │                                                           │
         ▼                                                           │
[L3: Domain Numerical Simulation]                                    │ L5 Retry Trigger
         │                                                           │ (if audit_score < 0.4
         ▼                                                           │  or retry_recommended)
[L4: Statistical Tests & Analysis]                                   │
         │                                                           │
         ▼                                                           │
[L5: Monte Carlo Robustness & Bias Audit] ───────────────────────────┘
         │ (Score ≥ 0.40)
         ▼
[L6: Memory Embedding & Recall]
         │
         ▼
[L7: Virtual Peer Review & PDF Generation]
         │
         ▼
[L8: Rubric Evaluation]
         │
         ├── Score < 0.70? ──► [Refinement Engine: Inject Targeted Patches] ──► (Rerun weak layers)
         │
         ▼ (Score ≥ 0.70)
[Complete: Research Report PDF + HTML Dashboard]
```

---

## 5. Domain Simulation Engines (Layer 3)

The simulation engine (`simulation_agent/`) uses deterministic mathematics and physics libraries, avoiding LLM hallucinations for numerical facts. When non-standard domains are encountered, an intelligent LLM fallback engine takes over:

```
                          Domain Router (router.py)
                  [Analyzes procedure text + domain keywords]
                                       │
      ┌───────────┬───────────┬────────┼───────────┬───────────┬───────────┐
      ▼           ▼           ▼        ▼           ▼           ▼           ▼
  Chemistry    Biology     Physics  Comp Sci     Civil       Mech     Electronics
 (chem_sim)   (bio_sim)  (physics)  (cs_sim)  (civil_sim)  (mech_sim) (electronics)
      │           │           │        │           │           │           │
      └───────────┴───────────┴────────┴───────────┴───────────┴───────────┘
                                       │ (No match / Unlisted domain)
                                       ▼
                             General LLM Fallback
                          (Claude Sonnet 4 / Ollama)
```

### Engine Specifications

1. **Chemistry Engine (`chem_sim.py`)**:
   - Solves Arrhenius reaction kinetics using SciPy's Ordinary Differential Equation solver (`solve_ivp`).
   - Integrates **RDKit** (optional) for molecular property calculations: Molecular Weight, LogP, Topological Polar Surface Area (TPSA), and Hydrogen bond donor/acceptor counts.
2. **Biology Engine (`bio_sim.py`)**:
   - Logistic growth models, Monod substrate utilization kinetics, and antibiotic concentration-inhibition curves (IC50 calculations).
3. **Physics Engine (`physics_sim.py` & `dynamic_sim.py`)**:
   - Verlet and Euler integrators for harmonic pendulum motion, 2D ballistic projectile trajectory with air drag, and double-slit optical wave interference.
   - Outputs coordinate frames for dynamic browser animations.
4. **Computer Science Engine (`cs_sim.py`)**:
   - In-process algorithmic benchmarks comparing sorting algorithms (Bubble, Merge, Quick, Heap) across array distributions.
   - Generates simulated deep learning training trajectories (CNN vs. Transformer loss/accuracy curves).
5. **Civil Engineering Engine (`civil_sim.py`)**:
   - Euler-Bernoulli beam deflection under point and distributed loads.
   - Computes maximum bending moments, shear forces, deflection profiles, and structural Factor of Safety (FoS).
6. **Mechanical Engineering Engine (`mech_sim.py`)**:
   - Multi-stage gear train ratios and torque output.
   - Thermodynamic cycles (Otto, Carnot) computing thermal efficiency and net work.
   - Solid shaft torsion stress and von Mises equivalent stress analysis.
7. **Electronics Engine (`electronics_sim.py`)**:
   - Circuit equations: Ohm's law voltage dividers, RC/RL low-pass and high-pass filter frequency response (Bode plots), LED forward IV curves, and simulated Arduino digital pin logic.
8. **General LLM Fallback (`llm_fallback.py`)**:
   - Seamlessly activates for interdisciplinary or novel questions. Leverages Claude Sonnet 4 or Ollama to generate structured qualitative insights and estimated numerical values.

---

## 6. Frontend Web Application & Visualizers

The frontend is a modern single-page application built with **React 18**, **Vite 5**, and custom CSS. It features a sleek dark cyberpunk aesthetic with dedicated domain visualizers:

```
frontend/src/components/
├── BlueprintVisualizer.jsx    # Civil engineering beam deflection & stress contours
├── CircuitVisualizer.jsx      # Electronics schematic diagrams & live components
├── MechVisualizer.jsx         # Mechanical Mohr's circle & gear train visualizer
├── SampleTestVisualizer.jsx   # Chemistry/Biology lab test racks & titration curves
├── SimulationResults.jsx      # Interactive Plotly charts & signature gold observation cards
├── SimulationRunner.jsx       # Modal overlay with real-time progress bars & execution logs
├── EvaluationDashboard.jsx    # Comprehensive Layer 8 scoring radar & refinement cycles
├── ExperimentForm.jsx         # Topic input form with preset scientific domain prompts
├── ExperimentOutput.jsx       # Real-time SSE token stream with syntax-highlighted Markdown
└── StatusBar.jsx              # Real-time health monitor for backend & Ollama connectivity
```

### Signature UI Highlights

- **Signature Amber Observations**: Key scientific findings are rendered in an exclusive amber/gold gradient (`#fef9c3` → `#fde68a` → `#fcd34d`) with hover slide-right animations and left-border accents.
- **Real-Time Streaming Cursor**: Displays an animated typing cursor as Ollama generates protocol tokens via Server-Sent Events.
- **Interactive Plotly Visualizations**: Full support for zooming, panning, hovering, and exporting charts (line, scatter, bar, histogram).
- **Execution Progress Modal**: Displays real-time status transitions (`Initializing` → `Routing Domain` → `Running Simulation` → `Complete`) with live log streaming.

---

## 7. Self-Learning & Continuous Improvement (Layer 6)

The platform does not require costly parameter fine-tuning (such as LoRA or full model retraining). Instead, it implements **In-Context Self-Improvement**:

```
[Experiment Executed] ──► [Record Confidence & User Scores in SQLite]
                                     │
                                     ▼
                [Dynamic Exponential Moving Average (EMA) Reweighting]
                new_weight = 0.6 * old_weight + 0.4 * (0.2 + avg_score * 1.8)
                                     │
                                     ▼
             [ChromaDB Memory Pruning (Removes items with score < 0.25)]
                                     │
                                     ▼
             [Claude LangChain Improvement Engine (Analyzes Weakest Layer)]
                                     │
                                     ▼
                   [Updated Prompt Directives & Weights for Next Run]
```

1. **Feedback Tracking**: Every experiment run logs its simulation confidence score, bias audit score, and user ratings to `memory_feedback.db`.
2. **Dynamic EMA Retrieval Reweighting**: Memory retrieval weights are updated using an Exponential Moving Average formula. High-scoring protocols are prioritized in future similarity searches, while problematic strategies are suppressed.
3. **Automated Memory Pruning**: Memories with average feedback scores below `0.25` are permanently purged from the ChromaDB vector store.
4. **LangChain Improvement Plans**: When queried, the Memory Agent analyzes longitudinal pipeline accuracy, identifies the weakest agent layer, and uses Claude to generate structured corrective prompt patches.

---

## 8. Repository File Structure

```
d:\EXP AGENT\Experiment-design-analysis-main\Hypothesise_Agent\
│
├── generate_report.py                     # Word document project report generator
├── Hypothesise_Agent_Project_Report.docx  # Generated executive report document
│
└── bohr-agent-sdk\examples\hypothesis_generator\
    ├── .env                               # Local API keys and model parameters (gitignored)
    ├── .env.example                       # Reference environment variables template
    ├── launch.py                          # Cross-platform Python launcher (backend + frontend)
    ├── launch.ps1                         # PowerShell one-command launcher for Windows
    │
    ├── backend\                           # FastAPI Backend Service (Port 8000)
    │   ├── server.py                      # Main API: SSE streaming, simulation endpoints
    │   └── requirements.txt               # Backend Python dependencies
    │
    ├── frontend\                          # React 18 + Vite Web Application (Port 3000)
    │   ├── src\
    │   │   ├── components\                # Domain visualizers, dashboards & form controls
    │   │   │   ├── BlueprintVisualizer.jsx
    │   │   │   ├── CircuitVisualizer.jsx
    │   │   │   ├── MechVisualizer.jsx
    │   │   │   ├── SampleTestVisualizer.jsx
    │   │   │   ├── SimulationResults.jsx
    │   │   │   ├── SimulationRunner.jsx
    │   │   │   ├── EvaluationDashboard.jsx
    │   │   │   ├── ExperimentForm.jsx
    │   │   │   └── StatusBar.jsx
    │   │   ├── App.jsx                    # Core application layout and state management
    │   │   └── index.css                  # Global styles and design system variables
    │   ├── package.json
    │   └── vite.config.js
    │
    ├── orchestrator\                      # LangChain 8-Layer Autonomous Pipeline
    │   ├── pipeline.py                    # Master orchestrator: runs L1 through L8
    │   ├── state.py                       # PipelineState shared Pydantic data model
    │   ├── memory.py                      # ChromaDB lazy collection manager
    │   ├── callbacks.py                   # Audit trail and event logging callbacks
    │   ├── refinement_engine.py           # Automated feedback patch and rerun engine
    │   ├── main.py                        # CLI entry point with sample research questions
    │   └── agents\
    │       ├── l1_hypothesis.py           # Layer 1: Hypothesis generator
    │       ├── l2_architect.py            # Layer 2: Protocol architect
    │       ├── l3_simulation.py           # Layer 3: Simulation router bridge
    │       ├── l4_analysis.py             # Layer 4: Statistical analysis
    │       ├── l5_bias_auditor.py         # Layer 5: Monte Carlo bias auditor
    │       ├── l6_memory.py               # Layer 6: Memory persistence & recall
    │       ├── l7_review.py               # Layer 7: Peer review & PDF compiler
    │       └── l8_evaluator.py            # Layer 8: Rubric evaluation & scoring
    │
    ├── simulation_agent\                  # Layer 3 Numerical Simulation Engines
    │   ├── agent.py                       # Main run_simulation() orchestrator
    │   ├── router.py                      # Keyword domain classifier
    │   ├── schema.py                      # Pydantic schemas (ExperimentProcedure, SimulationOutput)
    │   ├── dynamic_sim.py                 # Animated physics trajectory generator
    │   └── engines\
    │       ├── chem_sim.py                # Chemistry (Arrhenius kinetics & RDKit)
    │       ├── bio_sim.py                 # Biology (Logistic growth & IC50)
    │       ├── physics_sim.py             # Physics (Pendulum, projectile, optics)
    │       ├── cs_sim.py                  # Computer Science (Sorting & neural loss)
    │       ├── civil_sim.py               # Civil (Euler-Bernoulli beams & trusses)
    │       ├── mech_sim.py                # Mechanical (Gears, Otto cycle, torsion)
    │       ├── electronics_sim.py         # Electronics (Filters, IV curves, Arduino)
    │       └── llm_fallback.py            # Claude Sonnet 4 / Ollama qualitative fallback
    │
    ├── memory_agent\                      # Layer 6 Microservice (Port 8001)
    │   ├── main.py                        # FastAPI service entry point
    │   ├── memory_feedback.db             # Local SQLite feedback database
    │   └── core\
    │       ├── feedback.py                # Database CRUD operations
    │       ├── improvement_engine.py      # Claude LangChain improvement planner
    │       └── chromadb_store.py          # Vector store adapter
    │
    ├── output\                            # Saved experimental designs and JSON run logs
    └── outputs\                           # Generated peer-review PDF reports
```

---

## 9. Configuration & Environment Variables

Create a `.env` file in `Hypothesise_Agent\bohr-agent-sdk\examples\hypothesis_generator\.env`:

```ini
# =============================================================================
# Ollama Configuration (Local LLM for Layer 2 & Offline Fallback)
# =============================================================================
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3
OLLAMA_TEMPERATURE=0.3

# =============================================================================
# Anthropic Claude API (Primary reasoning LLM for L1, L3–L8)
# =============================================================================
ANTHROPIC_API_KEY=sk-ant-api03-your-anthropic-key-here

# =============================================================================
# DeepSeek API (Optional: used for standalone hypo_agent.py via LiteLLM)
# =============================================================================
DEEPSEEK_API_KEY=sk-your-deepseek-key-here
MODEL=deepseek/deepseek-chat

# =============================================================================
# Vector Store & Storage Settings
# =============================================================================
CHROMA_PERSIST_DIR=./chroma_pipeline_db
```

### LLM Optimization Presets

| Component | Target Model | Max Tokens | Temperature | Top P | Key Tuning Rationale |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `l2_architect.py` | Ollama LLaMA-3 | 4096 | 0.3 | 0.9 | `repeat_penalty=1.1`, timeout=180s to prevent circular protocols |
| `llm_fallback.py` | Claude Sonnet 4 | 4096 | 0.3 | 0.9 | Deterministic outputs, low hallucination rate |
| `hypo_agent.py` | DeepSeek Chat | 4096 | 0.4 | 0.9 | `frequency_penalty=0.1` encourages diverse hypothesis phrasing |
| `improvement_engine.py` | Claude Sonnet 4 | 2048 | 0.0 | 0.95 | Purely deterministic analytical recommendations |
| `l8_evaluator.py` | Claude Sonnet 4 | 4096 | 0.0 | 0.95 | Strict objective scoring against rubrics |

---

## 10. Quick Start & Installation Guide

### 10.1 Prerequisites

1. **Python 3.10+** (tested and verified on Python 3.13)
2. **Node.js 18+** and `npm`
3. **Ollama** installed and running locally:
   ```bash
   # Download from https://ollama.ai
   ollama serve
   ollama pull llama3
   ```
4. *(Optional but recommended)*: Anthropic API Key for Claude Sonnet 4.

---

### 10.2 Automated Launch (Recommended)

The project includes one-command launcher scripts that verify all dependencies, install Node packages if needed, and start all servers concurrently:

#### On Windows (PowerShell):
```powershell
cd "d:\EXP AGENT\Experiment-design-analysis-main\Hypothesise_Agent\bohr-agent-sdk\examples\hypothesis_generator"
.\launch.ps1
```

#### On Linux / macOS / Cross-Platform:
```bash
cd "d:/EXP AGENT/Experiment-design-analysis-main/Hypothesise_Agent/bohr-agent-sdk/examples/hypothesis_generator"
python launch.py
```

The launcher will:
- ✅ Verify Python libraries, Node.js, and Ollama status.
- ✅ Start the **FastAPI Backend** on `http://localhost:8000`.
- ✅ Start the **React Frontend** on `http://localhost:3000`.
- ✅ Automatically open your browser to the web interface.

---

### 10.3 Manual Service Startup

To run services in independent terminal windows for development and debugging:

#### Terminal 1 — Ollama Server
```bash
ollama serve
```

#### Terminal 2 — FastAPI Backend
```bash
cd "d:/EXP AGENT/Experiment-design-analysis-main/Hypothesise_Agent/bohr-agent-sdk/examples/hypothesis_generator/backend"
pip install -r requirements.txt
python -m uvicorn server:app --host 0.0.0.0 --port 8000
```
- API Base: `http://localhost:8000`
- Interactive Swagger Documentation: `http://localhost:8000/docs`

#### Terminal 3 — React Frontend
```bash
cd "d:/EXP AGENT/Experiment-design-analysis-main/Hypothesise_Agent/bohr-agent-sdk/examples/hypothesis_generator/frontend"
npm install
npm run dev
```
- Open browser at: `http://localhost:3000`

#### Terminal 4 — Memory Agent Microservice (Optional)
```bash
cd "d:/EXP AGENT/Experiment-design-analysis-main/Hypothesise_Agent/bohr-agent-sdk/examples/hypothesis_generator/memory_agent"
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8001
```
- Memory API Docs: `http://localhost:8001/docs`

---

### 10.4 Running the 8-Layer Orchestrator (CLI)

To run the complete scientific research pipeline programmatically without the web UI:

```bash
cd "d:/EXP AGENT/Experiment-design-analysis-main/Hypothesise_Agent/bohr-agent-sdk\examples\hypothesis_generator"
python -m orchestrator.main
```

Or invoke the pipeline directly in your own Python script:

```python
from orchestrator.pipeline import run_pipeline

# Run the 8-layer autonomous pipeline
result = run_pipeline("Does increasing temperature increase the rate of enzyme-catalyzed reactions?")

print("Selected Hypothesis :", result.selected_hypothesis)
print("Simulation Engine   :", result.simulation_result.get("engine_used"))
print("Audit Score         :", result.audit_score)
print("Peer Review Verdict :", result.review_verdict.get("verdict"))
print("Generated PDF Report:", result.pdf_path)
print("HTML Eval Dashboard :", result.dashboard_path)
```

---

### 10.5 Offline & Dry-Run Modes

To test without external network access or LLM API keys:

```bash
cd "d:/EXP AGENT/Experiment-design-analysis-main/Hypothesise_Agent/bohr-agent-sdk\examples\hypothesis_generator"

# Quick dry-run simulation demo
python dry_run_demo.py

# Detailed verbose dry-run with mock literature and simulation outputs
python dry_run_verbose.py
```

---

## 11. REST API Specification

### FastAPI Backend (`http://localhost:8000`)

| Endpoint | Method | Request Payload | Response / Format | Description |
| :--- | :---: | :--- | :--- | :--- |
| `/health` | `GET` | None | `{ status, ollama_available, models[] }` | Health check and Ollama model list |
| `/api/search-papers` | `POST` | `{ topic: string, max_papers: int, use_mock_data: bool }` | `{ papers: [...], count: int, source: string }` | Queries arXiv & Semantic Scholar |
| `/api/generate-design` | `POST` | `{ topic: string, max_papers: int, use_mock_data: bool }` | `text/event-stream` (Server-Sent Events) | Streams Ollama LLaMA-3 tokens in real-time |
| `/api/run-simulation` | `POST` | `{ topic: string, design: string, domain?: string }` | `{ success: bool, simulation: {...}, saved_to: string }` | Routes to domain engine and returns results & plot data |
| `/api/eval-reports` | `GET` | None | `{ reports: [ { run_id, overall_score, eval_passed } ] }` | Lists all past evaluation report summaries |
| `/api/eval-reports/{id}` | `GET` | Path parameter: `run_id` | Complete evaluation report JSON | Retrieves full Layer 8 scoring report |

### Memory Agent Microservice (`http://localhost:8001`)

| Endpoint | Method | Request Payload | Description |
| :--- | :---: | :--- | :--- |
| `/feedback` | `POST` | `{ memory_id: string, score: float, user_comment: string }` | Records user feedback score in SQLite |
| `/accuracy` | `GET` | Query params: `limit: int` | Returns historical layer-by-layer accuracy metrics |
| `/improve/plan` | `POST` | `{ run_id: string }` | Triggers Claude to generate an actionable improvement plan |

---

## 12. Key Engineering & Design Decisions

1. **Lazy ChromaDB & Model Loading**:
   - `sentence-transformers` and ChromaDB collections are initialized on first access rather than module import. This ensures sub-second CLI startup and avoids downloading 400MB embedding models during unit tests.
2. **Stateless PipelineState (Pydantic)**:
   - All 8 layers read from and mutate a single `PipelineState` instance. This decouples the agent orchestration logic from the underlying storage mechanism and makes pipeline runs completely inspectable and replayable.
3. **Deterministic Numerical Computation over LLMs**:
   - Numerical calculations (Euler-Bernoulli beams, Arrhenius kinetics, Monte Carlo loops) are computed using **SciPy** and **NumPy**, guaranteeing mathematical precision and reproducibility without hallucination risk.
4. **Hybrid LLM Hierarchy**:
   - High-throughput protocol generation is delegated to **local Ollama LLaMA-3** (zero API expense). High-order reasoning (hypothesis formulation, bias analysis, peer review, and evaluation rubrics) is routed to **Claude Sonnet 4**.
5. **Single-Process Production Uvicorn**:
   - The backend runs Uvicorn without `--reload` in multi-module environments to eliminate multiprocessing C-extension collisions with RDKit and SciPy.

---

## 13. Troubleshooting & FAQs

### Q1: Ollama shows "ollama_unavailable" or fails to connect
- Make sure the Ollama daemon is running:
  ```bash
  ollama serve
  ```
- Verify the LLaMA-3 model is pulled:
  ```bash
  ollama list
  ollama pull llama3
  ```

### Q2: RDKit or BioPython import errors
- `rdkit` and `biopython` are optional. If they are not installed, the chemistry and biology engines automatically fall back to standard SciPy kinetics and mathematical growth models without crashing.
- To install them:
  ```bash
  pip install rdkit biopython
  ```

### Q3: Port 8000 or 3000 is already in use
- On Windows PowerShell, find and terminate the blocking process:
  ```powershell
  Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess | Stop-Process -Force
  ```
- Alternatively, launch with custom ports:
  ```bash
  uvicorn server:app --port 8080
  ```

### Q4: CORS errors when connecting frontend to backend
- The backend is pre-configured with CORS middleware allowing origins `http://localhost:3000`, `http://localhost:3001`, `http://localhost:5173`. Ensure your Vite dev server runs on one of these ports.

---

## 14. Roadmap & Future Enhancements

- 🔀 **LangGraph StateGraph Migration**: Transition orchestrator agents to LangGraph with conditional branching, human-in-the-loop review nodes, and parallel execution for L4 (Analysis) and L5 (Bias Audit).
- 🌐 **Cloud Vector Synchronization**: Support managed Pinecone or Chroma Cloud instances for persistent team-wide memory synchronization.
- 🧪 **Live Bohrium Scientific API Integration**: Connect Layer 1 directly to Bohrium Science Navigator's real-time literature API.
- 👥 **Multi-Tenant Collaboration**: Implement role-based authentication (JWT) and collaborative multi-user research workspaces.

---

## 15.Acknowledgments

- **Framework Foundation**: Built on the **Bohrium Science Agent SDK** (`bohr-agent-sdk`) by DP Technology.

---

<div align="center">
  <sub>Built for accelerating open scientific inquiry through autonomous multi-agent intelligence.</sub>
</div>
