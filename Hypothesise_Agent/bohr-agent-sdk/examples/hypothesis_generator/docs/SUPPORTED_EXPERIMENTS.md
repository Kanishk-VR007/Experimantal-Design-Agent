# Supported Deterministic Experiments Registry

This catalog is generated directly from `simulation_agent/experiment_registry.py` (`EXPERIMENT_REGISTRY`).
Every registered experiment maps 1:1 to a deterministic domain solver, physical validation checks, and a synchronized 3D visualization template.

- **Total Registered Experiments:** 57
- **Covered Scientific & Engineering Domains:** 7 (`biology, chemistry, civil, computer_science, electronics, mechanical, physics`)
- **Unsupported Policy:** Any experiment outside this registry (or missing critical required parameters without documented defaults) returns an honest `status: "unsupported"` or `status: "failed"` response with zero fabricated plots or synthetic confidence scores.

## Domain: `biology` (4 experiments)

| Experiment ID | Engine | Solver Method | Governing Equations | Required Parameters | 3D Visualization Template |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `exponential_growth` | `bio_sim` | Malthusian Exponential Population Growth Analytical & ODE Solution | `dN/dt = r * N`; `N(t) = N_0 * exp(r * t)` | `initial_population`, `growth_rate` | `population_growth` |
| `gene_expression` | `bio_sim` | Coupled Linear Transcription-Translation ODE System | `dm/dt = k_tx - d_m * m`; `dp/dt = k_tl * m - d_p * p` | _none_ | `population_growth` |
| `logistic_growth` | `bio_sim` | Verhulst Logistic Population ODE & Exact Analytical Solution | `dN/dt = r * N * (1 - N / K)`; `N(t) = K / (1 + ((K - N_0)/N_0) * exp(-r * t))` | `initial_population`, `carrying_capacity`, `growth_rate` | `population_growth` |
| `michaelis_menten` | `bio_sim` | Exact Michaelis-Menten Steady-State Enzyme Kinetics & Inhibition Models | `v = (V_max * [S]) / (K_m + [S])`; `Competitive: K_m_app = K_m * (1 + [I]/K_i)` | `Vmax`, `Km` | `enzyme_kinetics` |

- **`exponential_growth`** — *Assumptions:* Constant per-capita growth rate r. *Limitations:* Unbounded growth is physically valid only before resource limitation.
- **`gene_expression`** — *Assumptions:* Deterministic mass-action kinetics; no transcriptional burst noise. *Limitations:* Not a stochastic Gillespie model.
- **`logistic_growth`** — *Assumptions:* Homogeneous well-mixed population with instantaneous density regulation. *Limitations:* Lag phase, death phase, and stochastic extinction not modeled.
- **`michaelis_menten`** — *Assumptions:* Single-substrate irreversible catalysis under Briggs-Haldane QSSA. *Limitations:* Does not model cooperative Hill kinetics or substrate depletion over long times.

## Domain: `chemistry` (5 experiments)

| Experiment ID | Engine | Solver Method | Governing Equations | Required Parameters | 3D Visualization Template |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `acid_base_titration` | `chem_sim` | Exact Charge-Balance & Water-Autoprotolysis Cubic Equilibrium Solver (All 4 Regimes) | `[H+]^3 + (Ka + Cb_eff)*[H+]^2 + (Ka*(Cb_eff - Ca_eff) - Kw)*[H+] - Ka*Kw = 0`; `V_eq = (Ca * Va) / Cb` | `acid_concentration_M`, `acid_volume_mL`, `base_concentration_M` | `titration_apparatus` |
| `chemical_equilibrium` | `chem_sim` | Exact Law of Mass Action ICE Solver (A + B <-> C + D or A <-> B) | `K_eq = ([C]*[D]) / ([A]*[B])`; `Mass balance: [A] + [C] = [A]_0 + [C]_0` | `K_eq`, `A0_M` | `reaction_kinetics` |
| `chemical_thermodynamics` | `chem_sim` | Gibbs Free Energy & van 't Hoff Temperature Dependence | `Delta_G = Delta_H - T * Delta_S`; `K_eq(T) = exp(-Delta_G / (R * T))` | `delta_H_kJ_mol`, `delta_S_J_mol_K` | `reaction_kinetics` |
| `molecular_properties` | `chem_sim` | Molecular Formula / RDKit Descriptor & 3D Geometry Catalogue | `MW = sum(n_i * m_i)` | _none_ | `molecular_geometry` |
| `reaction_kinetics` | `chem_sim` | Arrhenius Rate Law & 0th/1st/2nd Order ODE Integration with Analytical Verification | `k(T) = A * exp(-Ea / (R * T))`; `1st order: d[A]/dt = -k*[A], [A](t) = [A]_0 * exp(-k*t), t_1/2 = ln(2)/k` | `temperature_K`, `initial_concentration_M` | `reaction_kinetics` |

- **`acid_base_titration`** — *Assumptions:* Ideal dilute solution (activity coefficients = 1); Isothermal T = 298.15 K; Additive volumes. *Limitations:* Debye-Huckel ionic strength corrections and polyprotic species not included.
- **`chemical_equilibrium`** — *Assumptions:* Ideal activities equal molar concentrations. *Limitations:* Single equilibrium reaction; no activity coefficients.
- **`chemical_thermodynamics`** — *Assumptions:* Heat capacity difference Delta_Cp = 0. *Limitations:* Kirchhoff heat-capacity temperature corrections omitted.
- **`molecular_properties`** — *Assumptions:* Gas-phase reference equilibrium bond lengths and angles. *Limitations:* Requires RDKit for arbitrary SMILES descriptors.
- **`reaction_kinetics`** — *Assumptions:* Ideal solution; constant temperature; no reverse reaction. *Limitations:* Complex multi-step mechanisms require coupled ODE networks.

## Domain: `civil` (9 experiments)

| Experiment ID | Engine | Solver Method | Governing Equations | Required Parameters | 3D Visualization Template |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `building_blueprint` | `civil_sim` | Geometric architectural floor-plan & preliminary gravity load estimation | `A_floor = W * D`; `A_total = floors * A_floor` | _none_ | `building_blueprint` |
| `cantilever_beam_point_load` | `civil_sim` | Euler-Bernoulli analytical cantilever point-load solution | `R_fixed = P, M_fixed = -P * a`; `delta_tip = P * a^2 * (3*L - a) / (6 * E * I)` | `span_m`, `point_load_kN` | `beam_deformation` |
| `cantilever_beam_udl` | `civil_sim` | Euler-Bernoulli analytical cantilever UDL solution | `R_fixed = w * L, M_fixed = -w * L^2 / 2`; `delta_tip = w * L^4 / (8 * E * I)` | `span_m`, `load_kN_per_m` | `beam_deformation` |
| `simply_supported_beam_eccentric_point_load` | `civil_sim` | Euler-Bernoulli analytical static equilibrium & Macaulay deflection | `R_A = P * b / L, R_B = P * a / L (a + b = L)`; `M_max = P * a * b / L at x = a` | `span_m`, `point_load_kN`, `load_position_m` | `beam_deformation` |
| `simply_supported_beam_moment` | `civil_sim` | Euler-Bernoulli analytical applied couple moment solution | `R_A = -M_0 / L, R_B = +M_0 / L`; `M(x) step discontinuity of M_0 at x = a` | `span_m`, `applied_moment_kNm` | `beam_deformation` |
| `simply_supported_beam_multiple_loads` | `civil_sim` | Euler-Bernoulli linear superposition of concentrated loads | `R_B = sum(P_i * a_i) / L; R_A = sum(P_i) - R_B`; `V(x), M(x), y(x) by exact superposition` | `span_m`, `point_loads` | `beam_deformation` |
| `simply_supported_beam_point_load` | `civil_sim` | Euler-Bernoulli analytical static equilibrium & beam deflection | `R_A = R_B = P / 2`; `M_max = P * L / 4` | `span_m`, `point_load_kN` | `beam_deformation` |
| `simply_supported_beam_udl` | `civil_sim` | Euler-Bernoulli analytical UDL solution | `R_A = R_B = w * L / 2`; `M_max = w * L^2 / 8` | `span_m`, `load_kN_per_m` | `beam_deformation` |
| `truss_analysis` | `civil_sim` | 2D Direct Stiffness Method (Linear Elastic Matrix Structural Analysis) | `K_global * u = F`; `k_local = (E*A/L) * [[c^2, cs, -c^2, -cs], ...]` | `span_m`, `height_m`, `point_load_kN` | `truss_structure` |

- **`building_blueprint`** — *Assumptions:* Simplified uniform live+dead area load of 5 kN/m^2 for preliminary estimation. *Limitations:* Not a structural finite-element building design.
- **`cantilever_beam_point_load`** — *Assumptions:* Euler-Bernoulli linear elastic beam theory. *Limitations:* Small deflection theory.
- **`cantilever_beam_udl`** — *Assumptions:* Euler-Bernoulli linear elastic beam theory. *Limitations:* Small deflection theory.
- **`simply_supported_beam_eccentric_point_load`** — *Assumptions:* Euler-Bernoulli linear elastic beam theory; Pin at x=0, roller at x=L. *Limitations:* Single concentrated vertical load; shear deformation neglected.
- **`simply_supported_beam_moment`** — *Assumptions:* Concentrated clockwise moment M_0 applied at x=a. *Limitations:* Linear elastic range only.
- **`simply_supported_beam_multiple_loads`** — *Assumptions:* Linear elasticity permits exact superposition of individual point-load responses. *Limitations:* Does not include geometric nonlinearity.
- **`simply_supported_beam_point_load`** — *Assumptions:* Euler-Bernoulli plane sections remain plane and perpendicular to neutral axis; Shear deformation neglected (slender beam L/h >= 5); Self-weight neglected unless added explicitly; Deflection requires explicit E and I; omitted if E or I is missing. *Limitations:* Does not model plastic yielding, buckling, or shear-thick beams.
- **`simply_supported_beam_udl`** — *Assumptions:* Euler-Bernoulli beam theory; Uniform cross-section along span. *Limitations:* Linear elastic range only.
- **`truss_analysis`** — *Assumptions:* Frictionless pin joints; Axial-only member forces; Buckling of compression members not checked. *Limitations:* 2D linear-elastic static analysis only; no dynamic or nonlinear buckling.

## Domain: `computer_science` (17 experiments)

| Experiment ID | Engine | Solver Method | Governing Equations | Required Parameters | 3D Visualization Template |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `algorithm_complexity` | `cs_sim` | Theoretical Asymptotic Complexity Comparison (Separate from Algorithm Execution) | `O(log n), O(n), O(n log n), O(n^2)` | _none_ | `sorting_array` |
| `binary_search` | `cs_sim` | Instrumented Binary Search Execution (Requires Sorted Input) | `Time: O(log n)`; `Space: O(1)` | _none_ | `sorting_array` |
| `breadth_first_search` | `cs_sim` | Exact Queue-Based Breadth-First Search (FIFO deque) with Step Trace | `Time: O(V + E)`; `Space: O(V)` | _none_ | `graph_traversal` |
| `bubble_sort` | `cs_sim` | Instrumented Bubble Sort Execution | `Time: O(n^2) worst/avg, O(n) best`; `Space: O(1)` | _none_ | `sorting_array` |
| `connected_components` | `cs_sim` | Exact BFS/DFS Connected Components Decomposition | `Time: O(V + E)`; `Space: O(V)` | _none_ | `graph_traversal` |
| `depth_first_search` | `cs_sim` | Exact Stack-Based Depth-First Search with Step Trace | `Time: O(V + E)`; `Space: O(V)` | _none_ | `graph_traversal` |
| `dijkstra_shortest_path` | `cs_sim` | Exact Binary-Heap Priority Queue Dijkstra Algorithm with Relaxation Trace | `Time: O((V + E) log V)`; `Space: O(V)` | _none_ | `graph_traversal` |
| `dropout_effect` | `cs_sim` | Parametric Dropout Regularization Response Model | `acc(p) = A_base * exp(-6 * (p - p_opt)^2)` | _none_ | `neural_network_3d` |
| `heap_sort` | `cs_sim` | Instrumented Max-Heap Heap Sort Execution | `Time: O(n log n)`; `Space: O(1)` | _none_ | `sorting_array` |
| `insertion_sort` | `cs_sim` | Instrumented Insertion Sort Execution | `Time: O(n^2) worst, O(n) best`; `Space: O(1)` | _none_ | `sorting_array` |
| `linear_search` | `cs_sim` | Instrumented Linear Search Execution | `Time: O(n)`; `Space: O(1)` | _none_ | `sorting_array` |
| `merge_sort` | `cs_sim` | Instrumented Divide-and-Conquer Merge Sort Execution | `Time: O(n log n)`; `Space: O(n)` | _none_ | `sorting_array` |
| `model_comparison` | `cs_sim` | Parametric Analytical Learning-Curve Model (Illustrative CNN vs ViT Convergence) | `acc(t) = A_max * (1 - exp(-k * t))`; `loss(t) = L_0 * exp(-alpha * t) + L_inf` | _none_ | `neural_network_3d` |
| `neural_network_training` | `cs_sim` | Parametric Neural Network Loss/Accuracy Convergence Model | `loss(t) = L_0 * exp(-k * t) + L_inf` | _none_ | `neural_network_3d` |
| `quick_sort` | `cs_sim` | Instrumented Lomuto-Partition Quick Sort Execution | `Time: O(n log n) avg, O(n^2) worst`; `Space: O(log n)` | _none_ | `sorting_array` |
| `selection_sort` | `cs_sim` | Instrumented Selection Sort Execution | `Time: O(n^2)`; `Space: O(1)` | _none_ | `sorting_array` |
| `topological_sort` | `cs_sim` | Exact Kahn's Algorithm (In-Degree Queue Topological Sort with Cycle Detection) | `Time: O(V + E)`; `Space: O(V)` | _none_ | `graph_traversal` |

- **`algorithm_complexity`** — *Assumptions:* Unit-cost RAM model. *Limitations:* Theoretical Big-O curves, not empirical runtime execution.
- **`binary_search`** — *Assumptions:* Sorts input with warning if unsorted. *Limitations:* Requires random-access sorted array.
- **`breadth_first_search`** — *Assumptions:* Unweighted shortest hop traversal via FIFO queue. *Limitations:* Does not handle weighted edge costs (use Dijkstra).
- **`bubble_sort`** — *Assumptions:* In-place comparison sort. *Limitations:* Quadratic time for large arrays.
- **`connected_components`** — *Assumptions:* Symmetrizes edges if input adjacency is one-sided. *Limitations:* Undirected connectivity (not strongly connected components).
- **`depth_first_search`** — *Assumptions:* Deterministic neighbor ordering. *Limitations:* Does not guarantee shortest path in unweighted graphs.
- **`dijkstra_shortest_path`** — *Assumptions:* Directed or undirected weighted graph with non-negative weights. *Limitations:* Invalid for negative edge weights (requires Bellman-Ford).
- **`dropout_effect`** — *Assumptions:* Illustrative Gaussian optimum model. *Limitations:* Not empirical SGD training.
- **`heap_sort`** — *Assumptions:* In-place binary max-heap. *Limitations:* Not stable.
- **`insertion_sort`** — *Assumptions:* Stable in-place insertion sort. *Limitations:* Quadratic worst case.
- **`linear_search`** — *Assumptions:* Sequential scan from index 0. *Limitations:* Linear time.
- **`merge_sort`** — *Assumptions:* Stable out-of-place merge. *Limitations:* Requires O(n) auxiliary space.
- **`model_comparison`** — *Assumptions:* Analytical exponential convergence model (not actual GPU training). *Limitations:* Does not train real neural weights on CIFAR-10.
- **`neural_network_training`** — *Assumptions:* Smooth exponential convergence. *Limitations:* Not actual backpropagation on dataset.
- **`quick_sort`** — *Assumptions:* Deterministic last-element pivot Lomuto partition. *Limitations:* Worst-case O(n^2) on already sorted inputs.
- **`selection_sort`** — *Assumptions:* In-place comparison sort. *Limitations:* Always performs n(n-1)/2 comparisons.
- **`topological_sort`** — *Assumptions:* Lexicographical tie-breaking for deterministic output. *Limitations:* Returns cycle detected failure if graph is not a DAG.

## Domain: `electronics` (11 experiments)

| Experiment ID | Engine | Solver Method | Governing Equations | Required Parameters | 3D Visualization Template |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `ac_circuit` | `electronics_sim` | Steady-State Sinusoidal Phasor Impedance Analysis | `Z = R + j*(omega*L - 1/(omega*C))`; `I_rms = V_rms / |Z|` | `voltage_rms_V`, `frequency_Hz`, `resistance_ohm` | `rlc_circuit` |
| `arduino_led` | `electronics_sim` | DC LED Forward-Drop Limiting Resistor & Square-Wave Drive | `R = (V_supply - V_f) / I_LED`; `P_R = I_LED^2 * R` | _none_ | `arduino_circuit` |
| `current_divider` | `electronics_sim` | Parallel Resistive Current Divider with KCL Verification | `I_1 = I_total * R_2 / (R_1 + R_2)`; `I_2 = I_total * R_1 / (R_1 + R_2)` | `total_current_A`, `r1_ohm`, `r2_ohm` | `ohms_law_circuit` |
| `led_resistor` | `electronics_sim` | Series Battery-Resistor-LED Kirchhoff Loop | `I = (V_supply - V_f) / R`; `V_R = I * R` | _none_ | `arduino_circuit` |
| `ohms_law` | `electronics_sim` | Linear Resistive Circuit Law (I = V/R, P = V*I) | `I = V / R`; `P = V * I = I^2 * R = V^2 / R` | `resistance_ohm`, `supply_voltage_V` | `ohms_law_circuit` |
| `rc_circuit` | `electronics_sim` | First-Order RC Step-Response Analytical & ODE Solution | `tau = R * C`; `V_C(t) = V_0 * (1 - exp(-t / tau))` | `resistance_ohm`, `capacitance_F`, `voltage_V` | `rlc_circuit` |
| `rl_circuit` | `electronics_sim` | First-Order RL Step-Response Analytical Solution | `tau = L / R`; `I(t) = (V_0 / R) * (1 - exp(-t / tau))` | `resistance_ohm`, `inductance_H`, `voltage_V` | `rlc_circuit` |
| `series_parallel_circuit` | `electronics_sim` | Exact Series/Parallel Equivalent Resistance & Branch KCL/KVL Analysis | `R_series = sum(R_i)`; `1/R_parallel = sum(1/R_i)` | `supply_voltage_V` | `ohms_law_circuit` |
| `series_rlc` | `electronics_sim` | Series RLC Second-Order ODE (RK45 rtol=1e-9) + Analytical Resonance & KVL Verification | `L * d^2q/dt^2 + R * dq/dt + q / C = V_0`; `f_0 = 1 / (2*pi*sqrt(L*C)), zeta = R / (2*sqrt(L/C))` | `resistance_ohm`, `inductance_H`, `capacitance_F`, `voltage_V` | `rlc_circuit` |
| `transformer` | `electronics_sim` | Ideal Coupled-Magnetic Transformer Turns-Ratio Law | `V_s / V_p = N_s / N_p`; `I_p / I_s = N_s / N_p` | `primary_voltage_V`, `turns_primary`, `turns_secondary` | `rlc_circuit` |
| `voltage_divider` | `electronics_sim` | Resistive Voltage Divider with KVL & Power Verification | `V_out = V_in * R_2 / (R_1 + R_2)`; `I = V_in / (R_1 + R_2)` | `supply_voltage_V`, `r1_ohm`, `r2_ohm` | `voltage_divider_circuit` |

- **`ac_circuit`** — *Assumptions:* Pure single-frequency sinusoid; linear components. *Limitations:* Does not include harmonics or turn-on transient.
- **`arduino_led`** — *Assumptions:* Piecewise-constant LED forward voltage drop. *Limitations:* Ideal digital pin output impedance ignored.
- **`current_divider`** — *Assumptions:* Ideal current source. *Limitations:* Two-branch DC steady state.
- **`led_resistor`** — *Assumptions:* Constant forward voltage model. *Limitations:* Shockley exponential diode curve approximated by fixed Vf.
- **`ohms_law`** — *Assumptions:* Constant resistance independent of temperature. *Limitations:* Ignores thermal self-heating and power rating failure.
- **`rc_circuit`** — *Assumptions:* Ideal linear R and C components. *Limitations:* Ignores capacitor ESR and leakage resistance.
- **`rl_circuit`** — *Assumptions:* Ideal linear R and L. *Limitations:* Ignores core saturation and winding capacitance.
- **`series_parallel_circuit`** — *Assumptions:* Ideal voltage source and ideal conductors. *Limitations:* Purely resistive DC steady state.
- **`series_rlc`** — *Assumptions:* Linear time-invariant passive components. *Limitations:* Ignores parasitic capacitance and core nonlinearity.
- **`transformer`** — *Assumptions:* Zero winding resistance, zero core loss, infinite magnetizing inductance. *Limitations:* Real transformer efficiency, hysteresis, and eddy losses omitted.
- **`voltage_divider`** — *Assumptions:* Infinite output load impedance. *Limitations:* Output loading shifts V_out if finite R_load is attached.

## Domain: `mechanical` (9 experiments)

| Experiment ID | Engine | Solver Method | Governing Equations | Required Parameters | 3D Visualization Template |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `brayton_cycle` | `mech_sim` | Air-Standard Ideal Brayton Gas-Turbine Cycle | `eta_brayton = 1 - r_p^((1 - gamma) / gamma)` | `pressure_ratio` | `thermo_cycle` |
| `carnot_cycle` | `mech_sim` | Ideal Reversible Carnot Cycle (2 Isotherms + 2 Adiabats) | `eta_carnot = 1 - T_cold / T_hot`; `Isothermal P*V = const; Adiabatic P*V^gamma = const` | `T_hot_K`, `T_cold_K` | `thermo_cycle` |
| `diesel_cycle` | `mech_sim` | Air-Standard Ideal Diesel Cycle (Constant-Pressure Heat Addition) | `eta_diesel = 1 - (1 / r^(gamma-1)) * ((r_c^gamma - 1) / (gamma * (r_c - 1)))` | `compression_ratio` | `thermo_cycle` |
| `four_bar_linkage` | `mech_sim` | Planar Vector-Loop Closure (Freudenstein / Circle-Circle Intersection) & Velocity Analysis | `a*cos(th2) + b*cos(th3) - c*cos(th4) - d = 0`; `a*sin(th2) + b*sin(th3) - c*sin(th4) = 0` | `ground_length_m`, `crank_length_m`, `coupler_length_m`, `rocker_length_m` | `four_bar_linkage` |
| `gear_train` | `mech_sim` | Involute Spur Gear Kinematics, Torque Multiplication & Lewis Bending Stress | `i = N_2 / N_1`; `omega_out = omega_in / i` | `teeth_driver`, `teeth_driven` | `gear_train` |
| `otto_cycle` | `mech_sim` | Air-Standard Ideal Otto Cycle Thermodynamics | `eta_otto = 1 - r^(1 - gamma)`; `P2 = P1 * r^gamma, T2 = T1 * r^(gamma - 1)` | `compression_ratio` | `thermo_cycle` |
| `rotational_dynamics` | `mech_sim` | Rigid-Body Rotational Newton-Euler Equation | `I * alpha = tau_net - b_rot * omega`; `K_rot = 0.5 * I * omega^2` | `moment_of_inertia_kgm2`, `applied_torque_Nm` | `gear_train` |
| `shaft_design` | `mech_sim` | Circular Shaft Torsion & Combined Bending (von Mises Distortion Energy Criterion) | `J = pi * d^4 / 32, I = pi * d^4 / 64`; `tau_max = T * r / J, sigma_b = M * r / I` | `torque_Nm`, `diameter_mm` | `shaft_torsion` |
| `spring_mass_damper` | `mech_sim` | SciPy RK45 ODE Integration & Exact Analytical Modal Parameters | `m * x'' + c * x' + k * x = F(t)`; `omega_n = sqrt(k / m), zeta = c / (2 * sqrt(k * m))` | `mass_kg`, `stiffness_N_per_m` | `spring_mass_damper` |

- **`brayton_cycle`** — *Assumptions:* Isentropic compressor & turbine; constant-pressure heat exchangers. *Limitations:* Ignores compressor/turbine isentropic inefficiencies.
- **`carnot_cycle`** — *Assumptions:* Zero entropy generation (ideal theoretical upper bound). *Limitations:* Theoretical limit; cannot be achieved in real heat engines.
- **`diesel_cycle`** — *Assumptions:* Isobaric heat addition, isochoric heat rejection. *Limitations:* Ideal cold air-standard approximation.
- **`four_bar_linkage`** — *Assumptions:* Planar rigid-body kinematics; zero joint clearance and link elasticity. *Limitations:* Pure kinematic (position & velocity) analysis; inertia/joint reaction forces not included.
- **`gear_train`** — *Assumptions:* Constant mesh efficiency; Lewis form factor approximation for tooth root bending. *Limitations:* Does not include AGMA dynamic/pitting factors or thermal lubrication limits.
- **`otto_cycle`** — *Assumptions:* Reversible adiabatic compression/expansion; Isochoric heat addition/rejection. *Limitations:* Idealized cycle; ignores combustion kinetics, heat loss, and pumping work.
- **`rotational_dynamics`** — *Assumptions:* Constant moment of inertia; linear viscous bearing drag. *Limitations:* 1-DOF fixed-axis rotation only.
- **`shaft_design`** — *Assumptions:* Steady static loading; stress concentration factors Kt = 1.0. *Limitations:* Fatigue/endurance life and keyway stress risers not modeled.
- **`spring_mass_damper`** — *Assumptions:* Constant mass, stiffness, and damping coefficient. *Limitations:* No nonlinear dry friction or spring saturation.

## Domain: `physics` (2 experiments)

| Experiment ID | Engine | Solver Method | Governing Equations | Required Parameters | 3D Visualization Template |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `pendulum` | `physics_sim` | SciPy RK45 Nonlinear/Damped/Driven Pendulum ODE with Analytical Comparison | `Nonlinear: theta'' + (b/m)*theta' + (g/L)*sin(theta) = (A_drive/(m*L))*cos(omega_d*t)`; `Small-angle: T_0 = 2*pi*sqrt(L/g)` | `length_m` | `simple_pendulum` |
| `projectile_motion` | `physics_sim` | Analytical Ballistic Kinematics (Vacuum) or RK45 ODE (Quadratic Air Drag) | `Vacuum: x(t) = v0*cos(th)*t, y(t) = y0 + v0*sin(th)*t - 0.5*g*t^2`; `Drag: m*dv/dt = m*g - 0.5*rho*Cd*A*|v|*v` | `initial_velocity_ms`, `launch_angle_deg` | `projectile_motion` |

- **`pendulum`** — *Assumptions:* Small-angle mode explicitly restricted to |theta| < 0.25 rad (~14 deg). *Limitations:* Ignores air drag nonlinearity (quadratic drag) and pivot friction.
- **`projectile_motion`** — *Assumptions:* Vacuum (no air resistance) when drag_coeff == 0; quadratic aerodynamic drag when drag_coeff > 0. *Limitations:* Coriolis effect, wind, and Magnus spin lift neglected.
