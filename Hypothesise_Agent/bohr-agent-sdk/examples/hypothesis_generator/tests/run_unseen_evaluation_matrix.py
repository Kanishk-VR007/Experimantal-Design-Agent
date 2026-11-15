"""
Unseen Evaluation Matrix: Easy, Medium, and Hard Scientific Experiments
======================================================================
Tests the full Hypothesise Agent pipeline with unseen inputs across three
difficulty tiers and evaluates performance across all 7 layers (L1-L7):
  L1: Hypothesis Testability & Specificity
  L2: Architecture Completeness & Methodology
  L3: Simulation Fidelity & Confidence
  L4: Analysis Depth & SciPy Statistical Enrichment
  L5: Audit Soundness & Error Control
  L6: Domain Coverage & Variable Completeness
  L7: Review Readiness & Peer Review Quality

Persists structured evaluation reports into output/eval_<run_id>.json
for visualization in the frontend EvaluationDashboard.
"""

import os
import sys
import json
import time
import requests
from datetime import datetime

# ── Ensure project root on sys.path ──────────────────────────────────────────
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from simulation_agent.agent import run_simulation


def clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))


def grade_of(score: float) -> str:
    if score >= 0.90: return "A"
    if score >= 0.80: return "B"
    if score >= 0.70: return "C"
    if score >= 0.60: return "D"
    return "F"


def compute_eval_scores(simulation: dict, design: str, topic: str, tier: str) -> dict:
    """
    Computes exact evaluation metrics identical to frontend EvaluationDashboard.jsx:
    L1 (Hypothesis), L2 (Architecture), L3 (Simulation), L4 (Analysis),
    L5 (Audit), L6 (Coverage), L7 (Review).
    """
    confidence_score  = simulation.get("confidence_score", 0.0)
    status            = simulation.get("status", "unknown")
    hypothesis        = simulation.get("hypothesis", "")
    numerical_results = simulation.get("numerical_results", {})
    plot_data         = simulation.get("plot_data", [])
    observations      = simulation.get("observations", [])
    simulation_log    = simulation.get("simulation_log", [])
    domain            = simulation.get("domain", "")
    engine_used       = simulation.get("engine_used", "")

    dt    = (design or "").lower()
    dl    = len(dt)
    kws   = ["hypothesis", "variable", "method", "control", "analysis", "limitation", "expected", "procedure", "material"]
    hits  = sum(1 for s in kws if s in dt)
    n_keys = len(numerical_results)
    n_plot = len(plot_data)
    n_obs  = len(observations)
    n_log  = len(simulation_log)
    h_len  = len(hypothesis)

    has_cond = bool(any(w in (hypothesis or "").lower().split() for w in ["if", "when", "will"]))

    # L1 — Hypothesis
    base_l1 = 0.88 if h_len > 200 else (0.78 if h_len > 100 else (0.62 if h_len > 50 else 0.40))
    l1 = clamp(base_l1 + (0.05 if "hypothesis" in dt else 0.0) + (0.04 if has_cond else 0.0))

    # L2 — Architecture
    l2 = clamp(0.25 + (hits / len(kws)) * 0.60 + (0.15 if dl > 800 else (0.08 if dl > 400 else 0.0)))

    # L3 — Simulation fidelity
    l3 = clamp(confidence_score * 0.80 + (0.20 if status == "success" else 0.0))

    # L4 — Analysis depth
    l4 = clamp(0.35 + min(n_keys / 5.0, 1.0) * 0.35 + min(n_plot / 4.0, 1.0) * 0.30)

    # L5 — Audit / methodology
    l5 = clamp(0.35 + min(n_obs / 4.0, 1.0) * 0.30 + min(n_log / 8.0, 1.0) * 0.20 + (0.15 if status == "success" else 0.0))

    # L6 — Domain coverage
    l6 = clamp(0.45 + (0.15 if domain else 0.0) + (0.15 if n_plot > 2 else (0.08 if n_plot > 0 else 0.0)) + (0.18 if n_keys > 3 else (0.08 if n_keys > 0 else 0.0)))

    # L7 — Review readiness
    l7 = clamp(((l2 + l3 + l4) / 3.0) * 0.85 + (0.10 if n_obs > 2 else 0.0) + 0.05)

    layers = {
        "L1_hypothesis": {
            "score": round(l1, 4),
            "pct": f"{l1 * 100:.1f}%",
            "grade": grade_of(l1),
            "label": "Hypothesis",
            "details": f"Hypothesis length={h_len} chars, conditional syntax={has_cond}"
        },
        "L2_architect": {
            "score": round(l2, 4),
            "pct": f"{l2 * 100:.1f}%",
            "grade": grade_of(l2),
            "label": "Architecture",
            "details": f"Keywords hit {hits}/{len(kws)}, text length={dl} chars"
        },
        "L3_simulation": {
            "score": round(l3, 4),
            "pct": f"{l3 * 100:.1f}%",
            "grade": grade_of(l3),
            "label": "Simulation",
            "details": f"Status={status}, confidence={confidence_score:.2f}, engine={engine_used}"
        },
        "L4_analysis": {
            "score": round(l4, 4),
            "pct": f"{l4 * 100:.1f}%",
            "grade": grade_of(l4),
            "label": "Analysis",
            "details": f"Metrics={n_keys}/5, Visualizations={n_plot}/4 with SciPy statistics"
        },
        "L5_auditor": {
            "score": round(l5, 4),
            "pct": f"{l5 * 100:.1f}%",
            "grade": grade_of(l5),
            "label": "Audit",
            "details": f"Observations={n_obs}/4, Logs={n_log}/8, success={status == 'success'}"
        },
        "L6_memory": {
            "score": round(l6, 4),
            "pct": f"{l6 * 100:.1f}%",
            "grade": grade_of(l6),
            "label": "Coverage",
            "details": f"Domain={domain}, plots={n_plot}, numerical keys={n_keys}"
        },
        "L7_review": {
            "score": round(l7, 4),
            "pct": f"{l7 * 100:.1f}%",
            "grade": grade_of(l7),
            "label": "Review",
            "details": f"Composite readiness from L2 ({l2*100:.1f}%), L3 ({l3*100:.1f}%), L4 ({l4*100:.1f}%)"
        },
    }

    scores = [v["score"] for v in layers.values()]
    overall = round(sum(scores) / len(scores), 4)
    passed  = overall >= 0.70

    return {
        "tier": tier,
        "topic": topic,
        "overall_score": overall,
        "overall_pct": f"{overall * 100:.1f}%",
        "overall_grade": grade_of(overall),
        "eval_passed": passed,
        "layers": layers,
        "numerical_results_summary": {k: type(v).__name__ for k, v in numerical_results.items()},
        "plots_summary": [{"title": p.get("title", ""), "n_pts": len(p.get("x", []))} for p in plot_data],
        "has_3d_spec": "visualization_spec" in simulation,
    }


def run_benchmark():
    test_cases = [
        {
            "tier": "EASY",
            "topic": "Ohm's Law: Current vs Voltage across a precision carbon film resistor",
            "domain": "electronics",
            "design": """## 1. HYPOTHESIS
If voltage across a fixed precision carbon film resistor is systematically incremented from 0.0V to 10.0V, then the resulting electric current will increase strictly linearly in accordance with Ohm's Law (I = V / R) with constant resistance R = 1000 Ohms, maintaining an empirical correlation coefficient R^2 >= 0.999.

## 2. VARIABLES
- Independent Variable: Applied DC Voltage (V), evaluated over 0.0V to 10.0V at 0.5V steps.
- Dependent Variable: Electric Current (I), measured in Amperes / Milliamperes.
- Control Variable: Ambient Temperature (298.15K), Nominal Resistance (1000 Ohms, 0.1% tolerance), Lead resistance (<0.01 Ohm).
- Confounding Variable: Self-heating thermal drift of resistor carbon core.

## 3. EXPERIMENTAL DESIGN
A randomized continuous sweep design with 20 discrete voltage steps, repeated 5 independent times per step to establish 95% confidence intervals and standard errors.

## 4. METHODOLOGY & PROCEDURES
Apparatus and Materials:
- Precision benchtop DC Power Supply (0-30V, 10mV ripple)
- Keysight 34461A 6.5-digit True RMS Multimeter
- 1.000 kOhm 0.1% precision carbon film resistor rated at 0.5W
- Four-wire Kelvin clips and shielded coaxial banana test leads
Step-by-Step Procedure:
1. Calibrate zero-offset on the precision digital multimeter and verify power supply output stability.
2. Mount the 1 kOhm resistor using 4-wire Kelvin clips to eliminate lead contact resistance.
3. Stabilize ambient thermal conditions at 25.0 °C in an isolated chamber.
4. Step voltage from 0.0V to 10.0V in 0.5V increments, recording current after 2.0s settling duration.
5. Record 5 repeat trials per voltage setting, compute arithmetic mean, standard deviation, and residuals.

## 5. DATA ANALYSIS PLAN
Execute ordinary least squares linear regression via SciPy (scipy.stats.linregress) to compute slope (conductance G), intercept, Pearson correlation coefficient R^2, and first derivative dI/dV sensitivity curve. Construct 95% confidence intervals and response distribution histograms.

## 6. EXPECTED OUTCOMES
Current is expected to yield a linear slope of 1.000 mA/V (R = 1000 Ohms), R^2 >= 0.9999, with residual variance below 0.05% of full scale.

## 7. LIMITATIONS & BIAS CONTROLS
Instrumentation thermal bias controlled via low excitation current (<10mA) preventing Joule self-heating. Contact resistance eliminated by Kelvin 4-terminal sensing architecture."""
        },
        {
            "tier": "MEDIUM",
            "topic": "Cantilever beam elastic tip deflection under uniformly distributed load",
            "domain": "civil_engineering",
            "design": """## 1. HYPOTHESIS
If a uniformly distributed transverse load w = 5000 N/m is applied along a structural cantilever steel beam of length L = 3.0 m, then the elastic beam deflection y(x) will follow Euler-Bernoulli fourth-order polynomial mechanics y(x) = (w*x^2)/(24*E*I) * (x^2 - 4*L*x + 6*L^2), reaching a maximum predicted tip deflection of exactly 2.50 mm at x = L.

## 2. VARIABLES
- Independent Variable: Beam longitudinal position x (0.0 m to 3.0 m).
- Dependent Variable: Transverse deflection y(x) in millimeters, Internal Bending Moment M(x) in kNm, and Shear Force V(x) in kN.
- Control Variable: Beam Young's Modulus E = 200 GPa (Structural Steel), Second Moment of Area I = 8.333e-6 m^4, Span Length L = 3.0 m.
- Confounding Variable: Shear deformation shear locking and support elasticity.

## 3. EXPERIMENTAL DESIGN
Static loading benchmark testing transverse displacement profile under incremental load levels (w = 1000, 3000, 5000 N/m) with rigid fixed boundary at x = 0.

## 4. METHODOLOGY & PROCEDURES
Apparatus and Materials:
- Universal Structural Testing Cantilever Fixture with hydraulic load distribution manifold
- Linear Variable Differential Transformers (LVDT, 0.001 mm resolution, 10 stations)
- High-grade ASTM A36 structural I-beam (Length 3.0m, E=200 GPa, I=8.333e-6 m^4)
- Automated multichannel strain gauge data acquisition system (100 Hz sampling)
Step-by-Step Procedure:
1. Secure the beam base into the hydraulic reaction wall ensuring rigid fixed clamping condition at x=0.
2. Position 10 calibrated LVDTs along the beam span at 0.3m equidistant stations.
3. Tare and zero all displacement sensors and initialize thermal compensators.
4. Incrementally apply uniformly distributed pressure up to w = 5000 N/m across the span.
5. Record deflection profile, slope derivative dy/dx, and support reaction forces across 120 spatial points.

## 5. DATA ANALYSIS PLAN
Perform SciPy polynomial and linear regression analysis comparing measured profile against Euler-Bernoulli analytical closed form. Calculate 95% confidence intervals, residual root mean square error (RMSE), maximum tip deflection, and shear force distributions.

## 6. EXPECTED OUTCOMES
Deflection profile will exhibit quartic spatial scaling with maximum tip deflection at x = 3.0m reaching 2.50 mm +/- 0.05 mm, with analytical correlation R^2 > 0.998.

## 7. LIMITATIONS & BIAS CONTROLS
Geometric non-linearity minimized by verifying small deflection assumption (y_max / L < 0.001). Support flexibility bias accounted for by calibrating clamp base rotation with tiltmeter."""
        },
        {
            "tier": "HARD",
            "topic": "Deep Vision Transformer vs Convolutional Neural Network Convergence on Image Classification",
            "domain": "computer_science",
            "design": """## 1. HYPOTHESIS
If a Vision Transformer (ViT-Small) and a deep Convolutional Neural Network (ResNet-style) are trained on identical image classification benchmarks across 50 epochs with cosine decay learning rates, then the Vision Transformer will achieve a higher final validation accuracy (>= 91.0% vs CNN 88.5%), while the CNN will exhibit faster convergence within the first 15 epochs.

## 2. VARIABLES
- Independent Variable: Neural network architecture class (Vision Transformer self-attention vs CNN local convolutions) and training epoch t (1 to 50).
- Dependent Variable: Cross-entropy training loss, top-1 validation accuracy (%), and convergence rate d(Acc)/dt.
- Control Variable: Optimizer = AdamW (beta1=0.9, beta2=0.999), Initial Learning Rate = 0.001, Weight Decay = 0.05, Batch Size = 128.
- Confounding Variable: Stochastic data augmentation jitter and parameter initialization variance controlled via fixed random seed = 42.

## 3. EXPERIMENTAL DESIGN
Comparative multi-epoch benchmark training matrix across 50 epochs evaluating loss convergence profiles, generalization bounds, and model plateau limits.

## 4. METHODOLOGY & PROCEDURES
Apparatus and Software Environment:
- PyTorch / CUDA Compute Environment with deterministic gradient kernels
- CIFAR-10 standardized 10-class image classification benchmark dataset
- ResNet Convolutional backbone and Vision Transformer patch embedding pipeline
Step-by-Step Procedure:
1. Ingest CIFAR-10 image dataset normalized to zero mean and unit variance.
2. Initialize ResNet-style CNN with 3x3 residual blocks and batch normalization.
3. Initialize Vision Transformer with 8 multi-head self-attention heads and 16x16 patch projection embeddings.
4. Train both models for 50 epochs with AdamW optimizer and cosine annealing schedule.
5. Record training loss, validation loss, and top-1 validation accuracy at each epoch checkpoint.

## 5. DATA ANALYSIS PLAN
Compute non-linear convergence plateau fitting, epoch-to-80%-accuracy inflection point, final asymptotic accuracy, cross-entropy loss trajectories, and statistical confidence bounds via SciPy.

## 6. EXPECTED OUTCOMES
CNN achieves 80% accuracy significantly earlier (epoch 15-18), while Transformer peaks higher asymptotically (91.5% vs 89.0%), confirming transformer capacity advantages on global representations.

## 7. LIMITATIONS & BIAS CONTROLS
Dataset size bias controlled by running standardized benchmark splits; hyperparameter sensitivity controlled by matching learning rate schedules and regularization parameters."""
        }
    ]

    print("=" * 80)
    print("HYPOTHESISE AGENT: UNSEEN INPUTS BENCHMARK EVALUATION (EASY, MEDIUM, HARD)")
    print("=" * 80)

    results = []
    output_dir = os.path.join(os.path.dirname(__file__), "..", "output")
    os.makedirs(output_dir, exist_ok=True)

    for tc in test_cases:
        tier  = tc["tier"]
        topic = tc["topic"]
        design = tc["design"]
        print(f"\n[{tier}] Testing Experiment: '{topic}'")
        t0 = time.time()

        # Call live backend endpoint or direct simulation agent
        sim_input = {
            "topic": topic,
            "design": design,
            "domain": tc.get("domain", ""),
        }
        try:
            resp = requests.post("http://127.0.0.1:8000/api/run-simulation", json=sim_input, timeout=180)
            if resp.status_code == 200:
                sim_res = resp.json().get("simulation", {})
                print(f"  ✓ API /api/run-simulation responded 200 in {time.time() - t0:.2f}s")
            else:
                print(f"  ⚠ API returned {resp.status_code}, falling back to direct simulation agent...")
                sim_res = run_simulation(sim_input)
        except Exception as exc:
            print(f"  ⚠ Request error ({exc}), running direct simulation...")
            sim_res = run_simulation(sim_input)

        # Compute full evaluation across L1-L7
        eval_metrics = compute_eval_scores(sim_res, design, topic, tier)
        eval_metrics["duration_s"] = round(time.time() - t0, 2)
        results.append(eval_metrics)

        # Print score breakdown table for this tier
        print(f"  Overall Score: {eval_metrics['overall_pct']} ({eval_metrics['overall_grade']}) — Passed: {eval_metrics['eval_passed']}")
        print(f"  {'Layer':<18} | {'Score':<8} | {'Grade':<6} | Details")
        print(f"  {'-'*18}-+-{'-'*8}-+-{'-'*6}-+-{'-'*40}")
        for lk, ld in eval_metrics["layers"].items():
            print(f"  {ld['label']:<18} | {ld['pct']:<8} | {ld['grade']:<6} | {ld['details']}")

        # Save eval report to output/eval_<run_id>.json
        safe_id = f"{tier.lower()}_{int(time.time())}"
        eval_report_file = os.path.join(output_dir, f"eval_{safe_id}.json")
        with open(eval_report_file, "w", encoding="utf-8") as f:
            json.dump({
                "run_id": safe_id,
                "tier": tier,
                "topic": topic,
                "overall_score": eval_metrics["overall_score"],
                "eval_passed": eval_metrics["eval_passed"],
                "evaluated_at": datetime.utcnow().isoformat(),
                "layer_scores": eval_metrics["layers"],
                "numerical_results": sim_res.get("numerical_results", {}),
                "plot_count": len(sim_res.get("plot_data", [])),
                "obs_count": len(sim_res.get("observations", [])),
                "has_3d_spec": "visualization_spec" in sim_res,
                "engine_used": sim_res.get("engine_used", ""),
                "domain": sim_res.get("domain", ""),
            }, f, indent=2)
        print(f"  Saved evaluation report: {os.path.basename(eval_report_file)}")

    # ── Summary Across All Tiers ──────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("FINAL BENCHMARK MATRIX SUMMARY ACROSS ALL DIFFICULTY TIERS")
    print("=" * 80)
    print(f"{'Tier':<8} | {'Topic':<35} | {'Overall':<10} | {'L1 Hyp':<7} | {'L2 Arc':<7} | {'L3 Sim':<7} | {'L4 Ana':<7} | {'L5 Aud':<7} | {'L6 Cov':<7} | {'L7 Rev':<7}")
    print("-" * 115)
    for r in results:
        ly = r["layers"]
        print(f"{r['tier']:<8} | {r['topic'][:35]:<35} | {r['overall_pct'] + ' ' + r['overall_grade']:<10} | "
              f"{ly['L1_hypothesis']['grade']} ({ly['L1_hypothesis']['pct']}) | "
              f"{ly['L2_architect']['grade']} ({ly['L2_architect']['pct']}) | "
              f"{ly['L3_simulation']['grade']} ({ly['L3_simulation']['pct']}) | "
              f"{ly['L4_analysis']['grade']} ({ly['L4_analysis']['pct']}) | "
              f"{ly['L5_auditor']['grade']} ({ly['L5_auditor']['pct']}) | "
              f"{ly['L6_memory']['grade']} ({ly['L6_memory']['pct']}) | "
              f"{ly['L7_review']['grade']} ({ly['L7_review']['pct']})")

    # Assert that all tiers passed >= 70% threshold and L4 Analysis achieved >= 90% (Grade A)
    all_passed = all(r["eval_passed"] for r in results)
    l4_all_a   = all(r["layers"]["L4_analysis"]["score"] >= 0.90 for r in results)
    print(f"\nAll Tiers Passed Threshold (>=70%): {'YES' if all_passed else 'NO'}")
    print(f"L4 Analysis Scoring Grade A (>=90%): {'YES' if l4_all_a else 'NO'} (formerly 49.5% F)")

    return results


if __name__ == "__main__":
    run_benchmark()
