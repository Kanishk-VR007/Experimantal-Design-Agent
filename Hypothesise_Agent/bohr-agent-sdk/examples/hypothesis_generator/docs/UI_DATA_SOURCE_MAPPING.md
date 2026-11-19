# HYPOTHESISE AGENT — UI DATA SOURCE MAPPING REPORT
**Generated:** 2026-11-19  
**System:** Bohr Agent SDK / Hypothesise Agent v4.2  
**Architecture Principle:** ONE EXPERIMENT RUN → ONE AUTHORITATIVE DATA SOURCE → SYNCHRONIZED UI COMPONENTS → VERIFIED DISPLAYED VALUES  

---

## 1. Authoritative Backend Data Sources & Schemas

The table below maps every displayed frontend UI element directly to its authoritative backend source, schema, and database/storage entity.

| UI Element / Field | UI Location | Authoritative Backend Source | Schema / Object Model | Database / Storage Entity | Update Mechanism |
|---|---|---|---|---|---|
| **System Health & Connectivity** | TopBar, Sidebar, DiagnosticDrawer | `GET /api/health` | `HealthResponse` | In-memory server state | Periodic Polling (10s) |
| **LM Studio Model Telemetry** | TopBar, ModelRuntimeStatus, AgentPipeline | `GET /api/models/status` & `GET /api/visualization/model-status` | `ModelDiagnosticStatus`, `ModelSpec` | LM Studio REST API (`/v1/models`) | 3s Polling + SSE stage events |
| **Active Pipeline Stage** | TopBar, AgentPipeline, ExperimentPipelineStatus | `POST /api/generate-design` & `/api/visualization/pipeline-stream` | SSE Event (`{ type: "status", stage, message }`) | Process lifecycle state | Real-time SSE Stream |
| **Literature Search Papers** | ExperimentComposer, ReferenceSearchPanel | `POST /api/search-papers` | `List[Dict[str, Any]]` (arXiv / Semantic Scholar) | External APIs / Fallback cache | REST on query change / SSE event |
| **Refined Prompt & Tokens** | ExperimentComposer, InspectorPanel | `POST /api/visualization/refine-prompt` | `RefinedPromptOutput` | In-memory formulation | SSE `refinement` event |
| **Experimental Protocol Text** | ProtocolStream, ExperimentOutput | `POST /api/generate-design` | SSE Event (`{ type: "chunk", text }`) | `output/design_*.txt` | Real-time SSE Stream |
| **Completeness Audit Report** | ProtocolStream, EvaluationOverview | `POST /api/generate-design` | SSE Event (`{ type: "complete", design_completeness }`) | `output/design_*.txt` | SSE `complete` event |
| **Numerical Simulation Results** | SimulationWorkspace, ParameterInspector | `POST /api/run-simulation` | `SimulationOutput.numerical_results` | `output/simulation_*.json` | REST Promise / SSE pipeline complete |
| **2D Analytical Curves** | ScientificPlotlyChart | `POST /api/run-simulation` | `SimulationOutput.plot_data` | `output/simulation_*.json` | Per-run result store update |
| **3D WebGL Scene Objects** | Experiment3DViewer, SceneControls | `POST /api/visualization/generate` | `SceneSpecification` (Three.js allowlist) | Scene Factory in-memory | Per-run result store update |
| **Interactive Parameter Re-solve** | SimulationWorkspace, ParameterControls | `POST /api/visualization/update` | `VisualizationUpdateRequest` → `SimulationOutput` | Deterministic ODE solver recalculation | Immediate async POST update |
| **Scientific Validation Checks** | ScientificValidationPanel, EvaluationOverview | `POST /api/run-simulation` | `ValidationSummary` (`simulation.validation`) | `output/simulation_*.json` | Store update with result |
| **Governing Differential System** | SimulationWorkspace | `POST /api/run-simulation` | `ValidationSummary.governing_equations` | Engine metadata | Store update with result |
| **Execution Event Trace** | AgentPipeline, ExperimentExecutionLog | `useExperimentStore.agentEvents` | Client SSE Event Log | Client runtime array (max 200) | Append on each SSE event |
| **Historical Audited Reports** | ReportHistory, EvaluationOverview | `GET /api/eval-reports` | `List[ReportSummary]` | `output/eval_*.json` | REST on tab activation |
| **Single Evaluation Report** | ReportHistory (Detail view) | `GET /api/eval-reports/{run_id}` | Full Evaluation Report JSON | `output/eval_{run_id}.json` | REST on item select |
| **Memory Vector Store Metrics** | MemoryDashboard, TopBar | `GET /improve/accuracy-report` | `AccuracyReport` | `memory_feedback.db` (SQLite) | Polling (15s) + post-feedback reload |
| **Layer Feedback Scores (EMA)** | MemoryDashboard, LayerCard | `GET /improve/feedback-scores` | `FeedbackScores` | `memory_feedback.db` (SQLite) | Polling (15s) + post-feedback reload |
| **User Feedback Submission** | MemoryDashboard, EvaluationDetails | `POST /improve/feedback` | `FeedbackSubmission` | `memory_feedback.db` (SQLite) | Async POST on user rating |
| **Iterative Improvement Cycle** | MemoryDashboard | `POST /improve/run-cycle` | `ImprovementCycleResult` | `memory_feedback.db` (SQLite) | Async POST on trigger |

---

## 2. Single Source of Truth Lifecycle (One Experiment Run)

Every experiment execution follows an immutable lifecycle keyed by an unambiguous **Run ID**:

```
[User Formulates Hypothesis in ExperimentComposer]
                      │
                      ▼
         Generate unique currentRunId
            (e.g. RUN-20261119-7482)
                      │
                      ▼
     POST /api/generate-design (SSE Stream)
       ├── event: "start"  ──> set generating=true, clear previous run data
       ├── event: "papers" ──> store.papers updated (ReferenceSearchPanel)
       ├── event: "refinement" ──> store.refinement updated (RefinementPanel)
       ├── event: "chunk"  ──> store.design appended (ProtocolStream)
       └── event: "complete" ──> store.design_completeness updated
                      │
                      ▼
       POST /api/run-simulation (REST)
       ├── Returns SimulationOutput
       ├── Authoritative numerical_results (SimulationWorkspace)
       ├── Authoritative plot_data (ScientificPlotlyChart)
       ├── Authoritative validation (ScientificValidationPanel)
       └── Authoritative scene_spec (Experiment3DViewer)
                      │
                      ▼
       POST /api/visualization/update (On Slider Change)
       ├── Re-runs deterministic domain ODE solver
       └── Synchronously updates 2D plots, 3D meshes, and validation metrics together
```

---

## 3. Stale Data Rejection & Event Isolation

To prevent race conditions where events from a previous experiment run overwrite or pollute the active experiment:
1. Every SSE stream event is stamped with the originating `run_id`.
2. `useExperimentStore` validates that incoming chunks or completion payloads match `store.currentRunId`.
3. If `event.run_id !== store.currentRunId`, the payload is silently dropped and logged to diagnostic telemetry.
4. When a new experiment is initiated, `resetOutput()` clears all previous simulation plots, validation reports, and telemetry.
