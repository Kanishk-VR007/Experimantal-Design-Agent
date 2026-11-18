# Simulation Engine Initial Technical Audit (Stage 0)

**Date:** 2026-11-18  
**Scope:** `simulation_agent/` package, `backend/services/`, `backend/visualization/`, and `tests/` inside `examples/hypothesis_generator`.  
**Baseline Test Run:** `pytest tests/ -v` → **30 passed, 2 failed** (`test_cross_domain_analysis_depth`, `test_07_lm_studio_sequential_model_residency`).

---

## 1. Inventory of Existing Files & Architecture

| Module | Path | Current Role |
|---|---|---|
| Entrypoint | `simulation_agent/agent.py` | Keyword-based domain/experiment extraction, regex parameter extraction, routing, dynamic fallback, formatting |
| Router | `simulation_agent/router.py` | Domain-only dispatch dictionary (`DOMAIN_MAP`) with `llm_fallback.run` catch-all |
| I/O Schemas | `simulation_agent/schema.py` | `ExperimentProcedure`, `PlotData`, `SeriesData`, `SimulationOutput` (legacy Pydantic schemas) |
| Formatter | `simulation_agent/output_formatter.py` | Normalizes plots, computes descriptive statistics & 95% CI on deterministic trajectories, calls `generate_scene_specification` |
| Dynamic Sim | `simulation_agent/dynamic_sim.py` | LLM-synthesized NumPy/SciPy code execution in restricted subprocess sandbox |
| LLM Client | `simulation_agent/llm_client.py` | LM Studio primary + Ollama fallback chat/health client |
| Prompt Refiner | `simulation_agent/prompt_refiner.py` | Stop-word filtering + Qwen refinement |
| Physics Engine | `simulation_agent/engines/physics_sim.py` | `pendulum`, `rlc_circuit`, `projectile` |
| Civil Engine | `simulation_agent/engines/civil_sim.py` | `_cantilever_beam`, `_simply_supported_beam` (UDL only), `_truss_analysis` (approx.), `_building_blueprint` |
| Mechanical Engine | `simulation_agent/engines/mech_sim.py` | `_gear_train`, `_shaft_design`, `_thermo_cycle` (Otto/Carnot combined) |
| Electronics Engine | `simulation_agent/engines/electronics_sim.py` | `_arduino_led_circuit`, `_led_resistor_battery`, `_voltage_divider`, `_rlc_series`, `_ohms_law` |
| Chemistry Engine | `simulation_agent/engines/chem_sim.py` | Optional RDKit molecular properties, first-order Arrhenius kinetics, broken titration check |
| Biology Engine | `simulation_agent/engines/bio_sim.py` | `_enzyme_kinetics` (Michaelis-Menten), logistic growth, gene expression, optional BLAST (NOT registered in router!) |
| CS Engine | `simulation_agent/engines/cs_sim.py` | Synthetic exponential ML curves (`_model_comparison`, `_dropout_effect`, `_neural_network_training`) & theoretical `_algorithm_complexity` |
| Fallback Engine | `simulation_agent/engines/llm_fallback.py` | Claude/Ollama JSON generation + random sine-wave `get_minimal_fallback` |
| Scene Generator | `simulation_agent/visualization/scene_generator.py` | Domain + broad keyword dispatch to 3D templates |
| Model Manager | `backend/services/local_model_manager.py` | Sequential LM Studio loader (currently referencing stale model keys `qwen3-vl-2b-instruct` and `oreal-deepseek-r1-distill-qwen-7b`) |

---

## 2. Existing Solvers, Equations, Inputs & Defaults

| Domain | Experiment | Governing Equations Currently Used | Inputs & Defaults |
|---|---|---|---|
| Physics | `pendulum` | $\ddot{\theta} = -(g/L)\sin\theta - (b/m)\dot{\theta}$ via `solve_ivp` | `gravity=9.81`, `length_m=1.0`, `damping=0.1`, `angle_rad=0.5`, `bob_mass_kg=0.5` |
| Physics | `rlc_circuit` | $\dot{q}=i$, $\dot{i}=(V_0 - R i - q/C)/L$ via `solve_ivp` | `resistance_ohm=10`, `inductance_H=0.1`, `capacitance_F=0.001`, `voltage_V=5.0` |
| Physics | `projectile` | $x=v_0\cos\theta t$, $y=v_0\sin\theta t - \frac{1}{2}gt^2$ (no air drag) | `initial_velocity_ms=20`, `launch_angle_deg=45`, `gravity=9.81`, `mass_kg=1.0` |
| Civil | `cantilever_beam` | UDL only: $R=wL$, $M=-wL^2/2$, $y(x)=\frac{wx^2}{24EI}(x^2-4Lx+6L^2)$ | `span_m=3.0`, `load_kN_per_m=5.0`, `elastic_modulus_GPa=200.0`, `moment_of_inertia_m4=8.333e-6` |
| Civil | `beam_analysis` | UDL only: $R_A=R_B=wL/2$, $M_{\max}=wL^2/8$, $\delta_{\max}=\frac{5wL^4}{384EI}$ | `span_m=6.0`, `load_kN_per_m=10.0`, `elastic_modulus_GPa=200.0`, `moment_of_inertia_m4=8.33e-6` |
| Civil | `truss_analysis` | Heuristic approx. forces (`R_A * span / (2*height)`), NOT matrix stiffness | `span_m=10.0`, `height_m=3.0`, `panels=4`, `point_load_kN=20.0` |
| Civil | `building_blueprint` | Geometric floor area & grid layout | `floors=2`, `width_m=12.0`, `depth_m=8.0` |
| Mechanical | `gear_train` | $i=N_2/N_1$, $\omega_{out}=\omega_{in}/i$, $T_{out}=0.97 T_{in} i$, Lewis $\sigma_b=F_t/(bmY)$ | `teeth_driver=20`, `teeth_driven=40`, `module_mm=2.5`, `rpm_input=1500`, `power_kW=5.0` |
| Mechanical | `shaft_design` | $\tau=Tr/J$, $\sigma_b=Mr/I$, $\sigma_{eq}=\sqrt{\sigma_b^2+3\tau^2}$, $\theta=TL/(GJ)$ | `torque_Nm=200`, `bending_moment_Nm=150`, `length_mm=500`, `diameter_mm=40` |
| Mechanical | `thermo_cycle` | $\eta_{Otto}=1-r^{1-\gamma}$, $\eta_{Carnot}=1-T_c/T_h$; always builds Otto PV loop even for Carnot | `cycle="otto"`, `T_hot_K=1200`, `T_cold_K=300`, `compression_ratio=8`, `gamma=1.4` |
| Electronics | `ohms_law`, `voltage_divider`, `arduino_led`, `led_resistor`, `rlc_circuit` | $I=V/R$, $V_{out}=V_{in}R_2/(R_1+R_2)$, ODE for series RLC | Standard defaults (`1000 Ω`, `5V`, `10 Ω / 0.1 H / 0.001 F`) |
| Chemistry | `kinetics` | $k=A e^{-E_a/(RT)}$, $\dot{C}=-kC$ via `solve_ivp` | `temperature_K=298.15`, `activation_energy_kJ=50`, `pre_exponential_factor=1e10`, `initial_concentration_M=1.0` |
| Chemistry | `titration` | Broken Henderson-Hasselbalch `pKa + log10(V/(50-V))` (never triggers) | `pKa=4.74` |
| Biology | `enzyme_kinetics`, `growth_curve`, `gene_expression` | $v=\frac{V_{\max}[S]}{K_m+[S]}$, $\dot{N}=rN(1-N/K)$, linear mRNA/protein ODEs | `Vmax=100`, `Km=5`, `N0=100`, `K=1e6`, `r=0.5` |
| CS | `model_comparison`, `dropout_effect`, `neural_network`, `algorithm_complexity` | Exponential/Gaussian analytic curves & $O(\log n), O(n), O(n\log n), O(n^2)$ | `epochs=50`, `n_max=500` |

---

## 3. Detailed Defect Register (Reproduced in Baseline)

### Defect 1 — Mechanical Fallback Substitutes Thermodynamic Cycle for Unrecognized Mechanisms
- **File:** `simulation_agent/engines/mech_sim.py`
- **Function / Lines:** `run()` lines 445–464
- **Current Behaviour:** Unrecognized `experiment_type` (e.g., `four_bar_linkage`) skips `gear_train` and `shaft_design` and falls into the final `else:` branch executing `_thermo_cycle(params)`. Reproduced: `four_bar_linkage` returned `numerical_results` key `['thermodynamic_cycle']`.
- **Why Incorrect:** A planar four-bar kinematic mechanism is completely unrelated to an Otto/Carnot thermodynamic cycle.
- **Expected Behaviour:** Explicitly route supported mechanical experiments (`four_bar_linkage`, `gear_train`, `shaft_design`, `spring_mass_damper`, `otto_cycle`, `carnot_cycle`, `diesel_cycle`, `brayton_cycle`). Return `status="unsupported"` for unrecognized mechanical experiments. Implement a true vector-loop four-bar kinematics solver.
- **Recommended Correction:** Remove catch-all `else: _thermo_cycle(params)`, register explicit mechanical solvers, and implement Freudenstein / vector-loop four-bar kinematics with Grashof check, assembly branch selection, closure residual verification, and angular velocities.
- **Verification Test:** `tests/simulation_agent/test_mech_sim.py` (four-bar benchmark + regression asserting four-bar never outputs thermodynamic cycle and unknown mechanical experiment returns `unsupported`).

### Defect 2 — Civil Simply Supported Beam Misinterprets Central Point Load as UDL
- **File:** `simulation_agent/engines/civil_sim.py`
- **Function / Lines:** `_simply_supported_beam()` lines 160–196; `run()` lines 683–695
- **Current Behaviour:** Ignores `point_load_kN` completely and always uses `w = params.get("load_kN_per_m", 10.0)` with UDL equations $R=wL/2, M=wL^2/8$. Reproduced with `span_m=5.0, point_load_kN=10.0`: returned `reaction_A_kN=25.0, reaction_B_kN=25.0, max_bending_moment_kNm=31.25` instead of `5.0 kN, 5.0 kN, 12.5 kN·m`. Also `_cantilever_beam` only supports UDL and ignores point loads.
- **Why Incorrect:** Violates static equilibrium ($\sum F_y = 50\text{ kN} \neq 10\text{ kN}$) and yields a $2.5\times$ error in bending moment.
- **Expected Behaviour:** Separate explicit solvers for central point load ($R_A=R_B=P/2$, $M_{\max}=PL/4$, $\delta_{\max}=PL^3/(48EI)$), eccentric point load, UDL, multiple point loads, applied bending moments, and cantilever point/UDL loading. Require explicit $E$ and $I$ (or report missing parameters) for elastic deflection.
- **Recommended Correction:** Implement dedicated beam solvers and true 2D matrix-stiffness truss solver in `civil_sim.py`; wire exact experiment IDs in `experiment_registry.py`.
- **Verification Test:** `tests/simulation_agent/test_civil_sim.py` (5 m, 10 kN point load benchmark vs 5 m, 10 kN/m UDL benchmark + regression).

### Defect 3 — Computer Science Engine Only Plots Complexity Curves Instead of Executing Algorithms
- **File:** `simulation_agent/engines/cs_sim.py`
- **Function / Lines:** `_algorithm_complexity()` lines 126–166; `run()` lines 236–315
- **Current Behaviour:** Requesting BFS executes `_algorithm_complexity()` returning `['complexity_at_n500']` and a hardcoded static Dijkstra/QuickSort `visual_data` dict.
- **Why Incorrect:** Never runs BFS, ignores user graph/start node, and conflates Big-O growth plots with algorithm execution.
- **Expected Behaviour:** Actually execute BFS, DFS, Dijkstra, Connected Components, Topological Sort, Bubble/Selection/Insertion/Merge/Quick/Heap Sort, and Linear/Binary Search with deterministic step-by-step execution traces, visited order, queue/stack/heap state, operation counts, measured runtime, and separate theoretical Big-O metadata.
- **Recommended Correction:** Implement deterministic instrumented algorithm executors in `cs_sim.py` and keep theoretical complexity analysis as a separate experiment type.
- **Verification Test:** `tests/simulation_agent/test_cs_sim.py` (BFS queue traversal order, cycles, disconnected graphs, DFS, Dijkstra, sorting & searching benchmarks).

### Defect 4 — Chemistry Titration Condition Checks Wrong Dict Level & Uses Oversimplified Formula
- **File:** `simulation_agent/engines/chem_sim.py`
- **Function / Lines:** `run()` lines 112–126
- **Current Behaviour:** Checks `params.get("experiment_type") == "titration"` instead of `procedure.get("experiment_type")`. Reproduced: `experiment_type="titration"` ran first-order kinetics and returned `['kinetics', 'thermodynamics']` with no titration output. Even if reached, line 115 used `pKa + log10(V / (50 - V + 1e-9))`, which fails at $V=0$, at equivalence, and past equivalence.
- **Why Incorrect:** Completely drops titration requests into kinetics; Henderson-Hasselbalch is invalid at initial point ($V=0$), equivalence point (hydrolysis of conjugate base $A^-$), and excess strong base.
- **Expected Behaviour:** Route titration explicitly and solve full weak-acid/strong-base charge-balance / equilibrium equations across all 4 regimes (initial weak acid dissociation, buffer region, equivalence-point conjugate base hydrolysis, excess strong base). Separate kinetics, equilibrium, thermodynamics, and molecular properties.
- **Recommended Correction:** Refactor `chem_sim.py` into explicit experiment solvers with exact cubic/quadratic $[H^+]$ equilibrium solver for titration.
- **Verification Test:** `tests/simulation_agent/test_chem_sim.py` (0.1 M acetic acid $pK_a=4.756$, 25 mL + 0.1 M NaOH analytical benchmark at $V=0, 12.5, 25.0, 35.0\text{ mL}$).

### Defect 5 — Biology Engine Excluded from Router & Classifier
- **File:** `simulation_agent/router.py` (lines 6–48) and `simulation_agent/agent.py` (lines 27–43, 81–126)
- **Current Behaviour:** `bio_sim` is not imported or registered in `DOMAIN_MAP`, nor classified in `_classify_domain()`. Reproduced: `biology in router.DOMAIN_MAP == False`; baseline test `test_cross_domain_analysis_depth` failed with `Domain mismatch for Bacterial population logistic growth curve: general`.
- **Why Incorrect:** Supported deterministic biology models (`michaelis_menten`, `logistic_growth`, `exponential_growth`) fall through to LLM fallback.
- **Expected Behaviour:** Register `biology` explicitly in `router.py`, `agent.py`, and `experiment_registry.py`; support exponential growth, logistic growth, and Michaelis-Menten kinetics.
- **Recommended Correction:** Register `bio_sim.run` in `DOMAIN_MAP`, add biology classification keywords, and add explicit exponential growth solver alongside logistic growth and Michaelis-Menten.
- **Verification Test:** `tests/simulation_agent/test_bio_sim.py` (`[S]=K_m \Rightarrow v=V_{\max}/2`, zero/low/high substrate checks, logistic/exponential benchmarks).

### Defect 6 — Misleading Random Sine-Wave Fallback Reported as Simulation Data
- **File:** `simulation_agent/engines/llm_fallback.py`
- **Function / Lines:** `get_minimal_fallback()` lines 123–151
- **Current Behaviour:** Generates `y = np.sin(x) + np.random.normal(0, 0.1, 100)` with `confidence_score: 0.5` and returns it as a plot & numerical results.
- **Why Incorrect:** Fabricates random sinusoidal noise and presents it as simulation output for any failed/unsupported experiment.
- **Expected Behaviour:** Never fabricate random data. Return `status="unsupported"` or `status="failed"` with clear error explanation; label any conceptual fallback strictly as `simulation_type="illustrative"` without fake measurements.
- **Recommended Correction:** Replace `get_minimal_fallback()` to return an honest `unsupported`/`failed` response with zero fabricated plots or metrics.
- **Verification Test:** `tests/simulation_agent/test_router.py` & `test_simulation_pipeline.py`.

### Defect 7 — Arbitrary Fabricated Confidence Scores & Misapplied Statistical CIs
- **File:** `simulation_agent/output_formatter.py` (lines 91–170, 314) and all engine files (`confidence_score: 0.84..0.97`)
- **Current Behaviour:** Engines hardcode arbitrary `confidence_score` values (0.84, 0.88, 0.91, 0.93, 0.94, 0.95, 0.96, 0.97). `output_formatter.py` computes a 95% Student-t confidence interval across deterministic simulation time-series points as if they were i.i.d. experimental samples.
- **Why Incorrect:** Deterministic ODE/analytical trajectories are autocorrelated deterministic evaluations, not random i.i.d. experimental samples; fixed confidence scores are uncalibrated and misleading.
- **Expected Behaviour:** Report structured `simulation_status`, `solver` metadata (`name`, `version`, `method`), deterministic `validation` evidence, `assumptions`, `limitations`, `uncertainties`, and `warnings`. Compute deterministic descriptive summaries (min, max, mean, range, RMS) without claiming an experimental 95% CI unless genuine replicate sample data is provided.
- **Recommended Correction:** Refactor `output_formatter.py` and integrate `ScientificValidator`.
- **Verification Test:** `tests/simulation_agent/test_output_formatter.py`.

### Defect 8 — Independent Keyword-Based 3D Scene Selection Causes Severe Visual Mismatches
- **File:** `simulation_agent/visualization/scene_generator.py`
- **Function / Lines:** `generate_scene_specification()` lines 31–97
- **Current Behaviour:** Selects scenes primarily by `domain` with broad fallbacks. Reproduced:
  - `physics` + `rlc_circuit` → `simple_pendulum` (line 49)
  - `civil_engineering` + `truss_analysis` → `beam_deformation` (line 53)
  - `mechanical_engineering` + `shaft_design` → `beam_deformation` (line 62)
  - `chemistry` + `kinetics` → `molecular_geometry` (line 74)
  - `computer_science` + `bfs` → static Dijkstra graph scene (`cs_templates.py`)
- **Why Incorrect:** Visualized 3D apparatus contradicts the numerically simulated experiment.
- **Expected Behaviour:** Map `(domain, experiment_id) -> validated visualization template` via central registry. Synchronize geometry and animation directly from numerical solver output (e.g., actual four-bar joint positions, actual BFS traversal sequence, actual truss node coordinates, actual RLC circuit components, actual titration burette/beaker pH color). Reject mismatched templates during scene validation.
- **Recommended Correction:** Rebuild `scene_generator.py` around `EXPERIMENT_REGISTRY`, add missing scene builders (`truss_structure`, `shaft_torsion`, `rlc_circuit`, `titration_apparatus`, `reaction_kinetics`, `enzyme_kinetics`, `population_growth`, `graph_traversal`, `sorting_array`), and enforce experiment/template compatibility in `scene_validator.py`.
- **Verification Test:** `tests/simulation_agent/test_scene_generator.py`.

### Defect 9 — Stale LM Studio Model Keys & Missing Capability Validation
- **Files:** `.env`, `backend/services/local_model_manager.py`, `backend/services/vision_service.py`, `backend/visualization/visualization_pipeline.py`, `simulation_agent/llm_client.py`
- **Current Behaviour:** Configured keys are `VISION_MODEL=qwen3-vl-2b-instruct` and `MAIN_MODEL=oreal-deepseek-r1-distill-qwen-7b`, which do not exist in LM Studio (causes HTTP 404 in `test_07_lm_studio_sequential_model_residency`). Actual installed LM Studio catalog (`GET /api/v1/models`):
  - `qwen/qwen3-4b-thinking-2507` (`vision=false`, `trained_for_tool_use=true`, 4B Q4_K_M)
  - `qwen3-vl-4b-thinking` (`vision=true`, `trained_for_tool_use=true`, 4B Q4_K_M)
  - `deepseek/deepseek-r1-0528-qwen3-8b` (`vision=false`, `trained_for_tool_use=false`, 8B Q4_K_M)
  Also `local_model_manager.py` silently unloads ANY loaded model (even user-owned external instances) and lacks cross-process lock coordination and startup capability validation.
- **Recommended Correction:** Update `.env`, `local_model_manager.py`, `llm_client.py`, `vision_service.py`, and `visualization_pipeline.py` to discover and validate exact LM Studio model keys, track owned `instance_id`s, detect/report external user-loaded model conflicts without silently unloading them, enforce role capabilities, and treat DeepSeek-R1-0528-Qwen3-8B strictly as reasoning-only (no tool calls).
- **Verification Test:** `tests/test_vision_assisted_pipeline.py` + `tests/simulation_agent/test_simulation_pipeline.py`.

---

## 4. Missing High-Priority Solvers & Validation Framework
1. **Central Experiment Registry** (`simulation_agent/experiment_registry.py`) — absent.
2. **Canonical Pydantic Experiment Schema & SI Unit System** (`simulation_agent/experiment_schema.py`) — absent.
3. **Scientific Validation Engine** (`simulation_agent/validation/scientific_validator.py`) — absent (no dimensional, equilibrium, Kirchhoff, closure, or convergence checks).
4. **Four-Bar Linkage Kinematics Solver** — absent in `mech_sim.py`.
5. **Civil Beam Load Cases (Central Point, Eccentric Point, Multiple Point, Applied Moment, Cantilever Point) & Matrix-Stiffness Truss Solver** — absent in `civil_sim.py`.
6. **Actual CS Algorithm Execution (BFS, DFS, Dijkstra, Connected Components, Topological Sort, 6 Sorting & 2 Searching algorithms)** — absent in `cs_sim.py`.
7. **Electrical Circuits (Series/Parallel, Current Divider, RC, RL, AC, Transformer & KCL/KVL/Power checks)** — incomplete in `electronics_sim.py`.
8. **Mechanical Solvers (Spring-Mass-Damper, Rotational Dynamics, Separate Carnot/Otto/Diesel/Brayton cycles)** — incomplete in `mech_sim.py`.
9. **Chemistry Equilibrium & Accurate 4-Regime Titration Solver** — broken/missing in `chem_sim.py`.
10. **Biology Exponential Growth & Explicit Parameter Validation** — incomplete in `bio_sim.py`.
