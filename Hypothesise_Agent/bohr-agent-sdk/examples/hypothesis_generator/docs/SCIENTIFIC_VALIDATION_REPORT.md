# Scientific Validation Report — Hypothesise Agent Simulation Engine

**Date:** 2026-11-18  
**Scope:** Deterministic Domain Engines (7 Domains, 57 Registered Canonical Experiments), `ScientificValidator`, Registry-Synchronized 3D Visualization Pipeline, and LM Studio 3-Model Sequential Orchestration.

---

## 1. Validation Status Taxonomy

Every simulation output is evaluated by `simulation_agent/validation/scientific_validator.py` **before** finalizing status or generating a 3D scene:

| Status / Level | Meaning |
| :--- | :--- |
| `success` (`validated_within_assumptions`) | Deterministic domain solver completed, all numerical/physical conservation & invariant checks passed within tolerance. |
| `partial` (`validated_within_assumptions`) | Core equilibrium/kinematic quantities solved exactly, while secondary outputs (e.g. beam deflection without explicit $E$ and $I$) were intentionally withheld rather than fabricated. |
| `illustrative` (`implemented`) | Parametric analytical surrogate (e.g. ML learning-curve surrogate `model_comparison`) transparently marked `is_simulation_backed = false` and never represented as empirical dataset training. |
| `validation_failed` (`failed`) | Solver ran but violated one or more physical, mathematical, or finiteness invariants. |
| `unsupported` | Request is outside the 57 registered deterministic experiments; returns empty `plot_data`, `visualization_spec = null`, `confidence_score = null`, zero fabricated fallback data. |
| `failed` | Invalid physical inputs (e.g. negative length, non-assemblable linkage, negative edge weights in Dijkstra, cyclic DAG in topological sort, or missing critical required parameters). |

---

## 2. Measured Quantitative Benchmark Results

All values below were measured directly by executing the upgraded deterministic solvers on this workspace (`pytest tests/simulation_agent/ -v` + live benchmark runner):

| Benchmark | Reference Analytical / Exact Value | Measured Solver Output | Measured Residual / Error | Validation Level |
| :--- | :--- | :--- | :--- | :--- |
| **B1: Civil SS Beam — Central Point Load** ($L=5\text{ m}, P=10\text{ kN}, E=200\text{ GPa}, I=10^{-4}\text{ m}^4$) | $R_A=5.0\text{ kN}, R_B=5.0\text{ kN}, M_{\max}=12.5\text{ kN}\cdot\text{m}, \delta=1.3021\text{ mm}$ | $R_A=5.0, R_B=5.0, M_{\max}=12.5, \delta=1.302083\text{ mm}$ | Force eq. residual `0.0e+00 kN`, $\|\Delta \delta\| = 3.33 \times 10^{-7}\text{ mm}$ | Validated within assumptions |
| **B1b: Civil SS Beam — Point Load (No $E, I$)** ($L=5\text{ m}, P=10\text{ kN}$) | $R_A=5.0, R_B=5.0, M_{\max}=12.5$; deflection omitted | `deflection_computed=False`, `max_deflection_mm=None`, `status="partial"` | Force/moment eq. residual `0.0e+00` | Validated within assumptions |
| **B2: Civil SS Beam — UDL** ($L=5\text{ m}, w=10\text{ kN/m}, E=200\text{ GPa}, I=10^{-4}\text{ m}^4$) | $R_A=25.0, R_B=25.0, M_{\max}=31.25\text{ kN}\cdot\text{m}, \delta=4.0690\text{ mm}$ | $R_A=25.0, R_B=25.0, M_{\max}=31.25, \delta=4.06901\text{ mm}$ | Force eq. residual `0.0e+00 kN`, $\|\Delta \delta\| = 4.17 \times 10^{-7}\text{ mm}$ | Validated within assumptions |
| **B3: Mechanical Four-Bar Linkage** ($d=3, a=1, b=2.5, c=2\text{ m}, 30\text{ RPM}$) | Grashof crank-rocker, zero vector-loop closure error | Grashof Crank-Rocker, 120 valid closed frames | Max loop closure `1.11e-15 m`, max link-length error `8.88e-16 m` | Validated within assumptions |
| **B4: Mechanical Spur Gear Train** ($N_1=20, N_2=60, 1800\text{ RPM}, 5\text{ kW}$) | $i = 3.0$, $\text{RPM}_{\text{out}} = 600.0$ | $i = 3.0$, $\text{RPM}_{\text{out}} = 600.0$, $T_{\text{out}} = 77.1901\text{ N}\cdot\text{m}$ ($\eta=0.97$) | $\|\Delta i\| = 0.0$, $\|\Delta \text{RPM}\| = 0.0$ | Validated within assumptions |
| **B5: Electronics Series RLC** ($R=10\ \Omega, L=0.1\text{ H}, C=1\text{ mF}, V=5\text{ V}$) | $f_0 = 15.9155\text{ Hz}, \zeta = 0.5000$ (underdamped) | $f_0 = 15.91549\text{ Hz}, \zeta = 0.5000$ | RK45 vs analytical max error `2.23e-10 A`, finite-diff KVL `0.0018 V` (0.036% of 5V) | Validated within assumptions |
| **B6: Chemistry Weak-Acid Titration** ($25\text{ mL } 0.1\text{ M CH}_3\text{COOH}, \text{p}K_a=4.76 + 0.1\text{ M NaOH}$) | $\text{pH}_0 \approx 2.88$, $\text{pH}_{1/2} = 4.76$, $V_{\text{eq}} = 25\text{ mL}$, $\text{pH}_{\text{eq}} \approx 8.72$ | $\text{pH}_0 = 2.8829$, $\text{pH}_{1/2} = 4.7605$, $V_{\text{eq}} = 25.0\text{ mL}$, $\text{pH}_{\text{eq}} = 8.7295$ | Exact cubic charge-balance residual `1.10e-14 M` | Validated within assumptions |
| **B7: Biology Michaelis-Menten** ($V_{\max}=100, K_m=5\ \mu\text{M}$) | $v(0)=0$, $v(K_m)=50.0$, $v([S]\gg K_m) \to 100$ | $v(0)=0.0$, $v(K_m)=50.0$, $v(500)=99.009901$ | $\|v(K_m) - V_{\max}/2\| = 0.00 \times 10^{0}$ | Validated within assumptions |
| **B8: Computer Science BFS Traversal** (7 nodes, 1 disconnected `Z`) | FIFO order `['A','B','C','D','E','F']`, unreached `['Z']` | `['A','B','C','D','E','F']`, unreached `['Z']` | Exact FIFO & level match (18 instrumented ops) | Validated within assumptions |
| **B9: Physics Undamped Nonlinear Pendulum** ($L=1.5\text{ m}, \theta_0=0.1\text{ rad}$) | Zero mechanical energy drift | $T_0 = 2.45692\text{ s}$, $T_{\text{nl}} = 2.45846\text{ s}$ | Energy drift `0.0000e+00 %` | Validated within assumptions |
| **B10: Civil 2D Pratt Truss (Direct Stiffness)** ($L=10\text{ m}, H=3\text{ m}, 4\text{ panels}, P=20\text{ kN}$) | Global + nodal joint equilibrium = 0 | $T_{\max} = 25.0\text{ kN}$, $C_{\max} = 39.0512\text{ kN}$ | Max nodal joint residual `2.73e-11 N`, global eq. `0.0e+00 kN` | Validated within assumptions |

---

## 3. Eliminated Scientific & Architectural Defects (Baseline -> Upgraded)

1. **Random Sine-Wave Fallback Eliminated:** `llm_fallback.py` no longer fabricates random sine waves or hardcoded `confidence_score = 0.5`; unrecognized experiments return `status = "unsupported"` with empty `plot_data` and `visualization_spec = None`.
2. **Fabricated Confidence & Invalid Student-t CIs Eliminated:** `output_formatter.py` sets `confidence_score = None` by default and computes honest deterministic descriptive summaries (min, max, mean, std, range, RMS, derivative sensitivity) instead of Student-t 95% confidence intervals over deterministic ODE arrays.
3. **Civil Point-Load vs UDL Confusion Fixed:** Separate canonical solvers (`simply_supported_beam_point_load` vs `simply_supported_beam_udl` vs eccentric/cantilever variants) verified against exact analytical reactions, shear/moment diagrams, and Euler-Bernoulli deflection formulas.
4. **Mechanical Four-Bar Otto-Cycle Hijack Fixed:** Dedicated Freudenstein vector-loop kinematics solver + synchronized 3D linkage scene directly consuming solved joint coordinates (`kinematic_trajectory`).
5. **Chemistry Top-Level `experiment_type` Bug Fixed:** `chem_sim.py` now reads `procedure["experiment_type"]` directly; weak-acid titration solves exact 4-regime charge-balance cubic root-finding (`scipy.optimize.brentq`) instead of Henderson-Hasselbalch approximations across all regimes.
6. **Biology Registered End-to-End:** `bio_sim` explicitly registered in `router.DOMAIN_MAP`, `agent.USER_DOMAIN_NORMALIZATION`, `EXPERIMENT_REGISTRY`, and synchronized 3D templates (`enzyme_kinetics`, `population_growth`).
7. **Computer Science Real Algorithm Execution:** Instrumented executors for BFS, DFS, Dijkstra (with negative-weight rejection), Connected Components, Kahn's Topological Sort (with cycle detection), 6 sorting algorithms (verified with seeded property-based tests), and Linear/Binary Search — cleanly separated from theoretical Big-O complexity and parametric ML surrogates.
8. **3D Visualization Synchronization Enforced:** `scene_generator.py` maps strictly via `(domain, experiment_id) -> EXPERIMENT_REGISTRY[experiment_id].visualization_template -> builder` and `scene_validator.py` rejects mismatched templates (`RLC` never gets pendulum; `truss`/`shaft` never get beam; `titration`/`kinetics` never get molecule; `BFS` never gets Dijkstra).
9. **LM Studio 3-Model Sequential Pipeline Verified Live:** Updated to exact discovered model keys (`qwen/qwen3-4b-thinking-2507`, `qwen3-vl-4b-thinking`, `deepseek/deepseek-r1-0528-qwen3-8b`), capability-aware discovery, cross-process GPU lock, ownership tracking, and live sequential single-active-model residency test verified on local LM Studio (`http://localhost:1234`).

---

## 4. Known Scope & Limitations

- All built-in solvers are 1D/2D deterministic analytical, ODE, linear-algebra (2D truss DSM), or instrumented discrete-algorithm models within documented assumptions (e.g. Euler-Bernoulli small-deflection beams, ideal dilute aqueous solutions at 298.15 K, ideal passive RLC elements, planar rigid-body mechanisms).
- ML comparison experiments (`model_comparison`, `dropout_effect`, `neural_network_training`) remain deterministic parametric learning-curve surrogates and are explicitly labeled `illustrative` / non-empirical.
- Arbitrary 3D FEA, CFD, quantum field theory, or nonlinear transient multi-body dynamics are outside the built-in registry and are transparently reported as `unsupported`.
