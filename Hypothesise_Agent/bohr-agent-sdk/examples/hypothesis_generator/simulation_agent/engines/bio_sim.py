"""
Biology Simulation Engine
Handles: growth curves, gene expression, population dynamics
Produces: sample-testing visual data (96-well microplate layout) for the frontend
"""

import math
import numpy as np
from scipy.integrate import solve_ivp

# BioPython is optional
try:
    from Bio import Entrez, SeqIO
    from Bio.Blast import NCBIWWW, NCBIXML
    BIO_AVAILABLE = True
except ImportError:
    BIO_AVAILABLE = False
    print("[WARNING] BioPython not available - BLAST features disabled")


def _enzyme_kinetics(params: dict, procedure: dict):
    """
    Enzyme catalyzed substrate conversion kinetics with competitive,
    non-competitive, or uncompetitive allosteric inhibition.
    Models Michaelis-Menten kinetics and Lineweaver-Burk double reciprocal transformation.
    """
    Vmax = float(params.get("Vmax") or params.get("v_max") or params.get("V_max") or 100.0)
    Km = float(params.get("Km") or params.get("K_m") or params.get("michaelis_constant") or 5.0)
    Ki = float(params.get("Ki") or params.get("K_i") or params.get("inhibition_constant") or 2.5)
    raw_I = params.get("I") or params.get("inhibitor_conc") or 2.5
    I_val = float(raw_I[0] if isinstance(raw_I, list) and raw_I else raw_I)
    
    # Substrate concentration range [S] (uM)
    S_range = np.linspace(0.5, 60.0, 120)
    
    # Uninhibited control: v = Vmax * [S] / (Km + [S])
    v_control = (Vmax * S_range) / (Km + S_range)
    
    # Non-competitive allosteric inhibition:
    # Vmax_app = Vmax / (1 + [I] / Ki), Km unchanged
    Vmax_app1 = Vmax / (1.0 + (I_val / Ki))
    v_inhibited1 = (Vmax_app1 * S_range) / (Km + S_range)
    
    # High inhibitor: [I]_high = 2 * I_val
    I_high = 2.0 * I_val
    Vmax_app2 = Vmax / (1.0 + (I_high / Ki))
    v_inhibited2 = (Vmax_app2 * S_range) / (Km + S_range)
    
    # Lineweaver-Burk reciprocal coordinates (1/[S] vs 1/v)
    lb_inv_S = np.linspace(0.02, 1.0, 100)
    lb_S = 1.0 / lb_inv_S
    lb_v_ctrl = (Vmax * lb_S) / (Km + lb_S)
    lb_inv_v_ctrl = 1.0 / lb_v_ctrl
    
    lb_v_inh1 = (Vmax_app1 * lb_S) / (Km + lb_S)
    lb_inv_v_inh1 = 1.0 / lb_v_inh1
    
    lb_v_inh2 = (Vmax_app2 * lb_S) / (Km + lb_S)
    lb_inv_v_inh2 = 1.0 / lb_v_inh2
    
    # Inhibitor concentration sweep (0 to 10 uM) for Vmax_app curve
    I_sweep = np.linspace(0.0, 10.0, 80)
    vmax_app_curve = Vmax / (1.0 + (I_sweep / Ki))
    
    numerical = {
        "enzyme_kinetics": {
            "Vmax_uninhibited":        round(Vmax, 2),
            "Km_uM":                   round(Km, 2),
            "Ki_uM":                   round(Ki, 2),
            "inhibitor_conc_uM":       round(I_val, 2),
            "Vmax_app_uM_per_min":     round(Vmax_app1, 2),
            "catalytic_efficiency":    round(Vmax / max(Km, 1e-6), 2),
            "inhibition_pct":          round((1.0 - (Vmax_app1 / Vmax)) * 100.0, 1),
            "x_intercept_LB":          round(-1.0 / max(Km, 1e-6), 3),
        }
    }
    
    plots = [
        {
            "plot_type": "line",
            "title": "Michaelis-Menten Kinetics — Initial Velocity vs [S]",
            "x_label": "Substrate Concentration [S] (µM)",
            "y_label": "Initial Reaction Velocity v (µmol/(L·min))",
            "x": S_range.tolist(),
            "y": v_control.tolist(),
            "series_name": "Control ([I] = 0 µM)",
            "extra_series": [
                {"y": v_inhibited1.tolist(), "name": f"Inhibited ([I] = {I_val} µM)", "color": "#f59e0b"},
                {"y": v_inhibited2.tolist(), "name": f"High Inhibited ([I] = {I_high} µM)", "color": "#ef4444"},
            ],
        },
        {
            "plot_type": "line",
            "title": "Lineweaver-Burk Double Reciprocal Plot (1/v vs 1/[S])",
            "x_label": "Reciprocal Substrate 1/[S] (µM⁻¹)",
            "y_label": "Reciprocal Velocity 1/v (L·min/µmol)",
            "x": lb_inv_S.tolist(),
            "y": lb_inv_v_ctrl.tolist(),
            "series_name": "Control 1/v",
            "extra_series": [
                {"y": lb_inv_v_inh1.tolist(), "name": f"Inhibited 1/v ([I] = {I_val} µM)", "color": "#f59e0b"},
                {"y": lb_inv_v_inh2.tolist(), "name": f"High Inhibited 1/v ([I] = {I_high} µM)", "color": "#ef4444"},
            ],
        },
        {
            "plot_type": "line",
            "title": "Apparent Maximum Velocity Vmax_app vs [I]",
            "x_label": "Inhibitor Concentration [I] (µM)",
            "y_label": "Apparent Vmax (µmol/(L·min))",
            "x": I_sweep.tolist(),
            "y": vmax_app_curve.tolist(),
            "series_name": "Vmax_app([I])",
        },
    ]
    
    # 96-well microplate layout tailored to enzyme assay
    ROWS = list("ABCDEFGH")
    COLS = list(range(1, 13))
    rng = np.random.default_rng(seed=42)
    wells = []
    for ri, row in enumerate(ROWS):
        s_local = 0.5 + ri * (50.0 / 7.0)
        for ci, col in enumerate(COLS):
            well_id = f"{row}{col}"
            if col in (1, 2, 3, 4):
                v_expected = (Vmax * s_local) / (Km + s_local)
                sample_type = "control"
            elif col in (5, 6, 7, 8):
                v_expected = (Vmax_app1 * s_local) / (Km + s_local)
                sample_type = "inhibited_low"
            else:
                v_expected = (Vmax_app2 * s_local) / (Km + s_local)
                sample_type = "inhibited_high"
            
            noise = float(rng.normal(0, 0.015))
            od = round(float(np.clip((v_expected / Vmax) * 1.4 + 0.08 + noise, 0.05, 1.8)), 3)
            wells.append({
                "well": well_id,
                "row": row,
                "col": col,
                "type": sample_type,
                "od600": od,
                "normalized": round(float(np.clip(od / 1.8, 0.0, 1.0)), 3),
            })
    
    visual_data = {
        "plate_format": "96-well",
        "rows": 8,
        "cols": 12,
        "wells": wells,
        "legend": {
            "control": "Enzyme + Substrate (Columns 1-4)",
            "inhibited_low": f"Enzyme + Substrate + [I]={I_val}µM (Columns 5-8)",
            "inhibited_high": f"Enzyme + Substrate + [I]={I_high}µM (Columns 9-12)",
        },
    }
    
    observations = [
        f"Enzyme catalyzed substrate conversion kinetics evaluated across [S] = 0.5 to 50 µM",
        f"Uninhibited control achieves Vmax = {Vmax:.1f} µmol/(L·min) with Michaelis constant Km = {Km:.2f} µM",
        f"Non-competitive allosteric inhibition ([I] = {I_val} µM, Ki = {Ki:.2f} µM) reduces apparent Vmax to {Vmax_app1:.1f} µmol/(L·min) (-{numerical['enzyme_kinetics']['inhibition_pct']}%)",
        f"Michaelis constant Km remains invariant at {Km:.2f} µM across all inhibitor levels",
        f"Lineweaver-Burk double reciprocal analysis displays common x-axis intercept at -1/Km = {-1.0/Km:.3f} µM⁻¹",
    ]
    
    return numerical, plots, visual_data, observations


def run(procedure: dict) -> dict:
    """Biology simulation: growth curves, gene expression, protein folding."""
    log = ["[bio_sim] Starting biology simulation"]
    params   = procedure.get("parameters", {})
    exp_type = procedure.get("experiment_type") or "growth_curve"
    results  = {}
    plots    = []

    comb = (procedure.get("hypothesis", "") + " " + exp_type).lower()
    if any(w in comb for w in ("enzyme", "michaelis", "menten", "allosteric", "substrate", "cataly", "lineweaver")):
        results, plots, visual_data, observations = _enzyme_kinetics(params, procedure)
        log.append("[bio_sim] Enzyme kinetics & Lineweaver-Burk simulation computed")
        log.append("[bio_sim] 96-well microplate enzyme assay layout generated")
        return {
            "numerical_results": results,
            "plot_data": plots,
            "visual_data": visual_data,
            "visualization_type": "sample_testing",
            "observations": observations,
            "confidence_score": 0.95,
            "simulation_log": log,
        }

    if exp_type not in ("gene_expression", "blast") or exp_type == "growth_curve" or "growth" in procedure.get("domain", "").lower():
        # ── Bacterial growth (logistic model) ──────────────────
        N0 = params.get("initial_population", 100)
        K = params.get("carrying_capacity", 1e6)
        r = params.get("growth_rate", 0.5)
        t_end = params.get("time_hours", 24)

        def logistic(t, N):
            return [r * N[0] * (1 - N[0] / K)]

        t_eval = np.linspace(0, t_end, 400)
        sol = solve_ivp(logistic, (0, t_end), [N0], t_eval=t_eval)
        N = sol.y[0]

        results["growth"] = {
            "final_population": float(N[-1]),
            "doubling_time_h": float(np.log(2) / r),
            "time_to_carrying_cap_h": float(t_eval[np.argmin(np.abs(N - 0.95 * K))]),
            "growth_rate_r": r,
        }
        plots.append({
            "plot_type": "line",
            "title": "Bacterial Growth — Logistic Model",
            "x_label": "Time (hours)",
            "y_label": "Population (cells)",
            "x": t_eval.tolist(),
            "y": N.tolist(),
            "series_name": "Cell Count",
        })
        log.append(f"[bio_sim] Growth sim: doubling time={results['growth']['doubling_time_h']:.2f}h")

    elif exp_type == "gene_expression":
        # ── mRNA / protein expression model ────────────────────
        t_eval = np.linspace(0, 48, 400)
        k_tx = params.get("transcription_rate", 0.8)
        k_tl = params.get("translation_rate", 0.5)
        d_m = params.get("mRNA_degradation", 0.3)
        d_p = params.get("protein_degradation", 0.1)

        def odes(t, y):
            mRNA, protein = y
            return [k_tx - d_m * mRNA,
                    k_tl * mRNA - d_p * protein]

        sol = solve_ivp(odes, (0, 48), [0, 0], t_eval=t_eval)
        results["expression"] = {
            "steady_state_mRNA": float(k_tx / d_m),
            "steady_state_protein": float((k_tl * k_tx) / (d_m * d_p)),
            "peak_mRNA_time_h": float(t_eval[np.argmax(sol.y[0])]),
        }
        plots.append({
            "plot_type": "line",
            "title": "Gene Expression Dynamics",
            "x_label": "Time (hours)",
            "y_label": "Concentration (AU)",
            "x": t_eval.tolist(),
            "y": sol.y[1].tolist(),
            "series_name": "Protein Level",
        })

    elif exp_type == "blast" and BIO_AVAILABLE:
        # ── BLAST sequence alignment (real API call) ───────────
        sequence = params.get("sequence", "")
        log.append("[bio_sim] Running BLAST alignment via NCBI...")
        Entrez.email = params.get("entrez_email", "research@agent.ai")
        result_handle = NCBIWWW.qblast("blastp", "nr", sequence, hitlist_size=5)
        blast_records = NCBIXML.read(result_handle)
        hits = []
        for aln in blast_records.alignments[:5]:
            hsp = aln.hsps[0]
            hits.append({
                "title": aln.title[:60],
                "score": hsp.score,
                "e_value": hsp.expect,
                "identity": hsp.identities / hsp.align_length,
            })
        results["blast_hits"] = hits
        log.append(f"[bio_sim] BLAST returned {len(hits)} hits")

    # ── Build 96-well sample-testing visual ────────────────────────────────
    visual_data = _build_sample_testing_visual(results, params, procedure)
    log.append("[bio_sim] 96-well sample plate layout generated")

    doubling_h = results.get("growth", {}).get("doubling_time_h", "N/A")
    return {
        "numerical_results": results,
        "plot_data": plots,
        "visual_data": visual_data,
        "visualization_type": "sample_testing",
        "observations": [
            "Growth follows logistic dynamics with nutrient-limited plateau",
            f"Doubling time: {doubling_h}h",
            "Sample distribution shown across 96-well microplate",
            "Wells A1–A3: negative controls (media only)",
            "Wells B1–H12: experimental samples in duplicate",
        ],
        "confidence_score": 0.84,
        "simulation_log": log,
    }


# ─── Sample-testing visual builder ────────────────────────────────────────────

def _build_sample_testing_visual(results: dict, params: dict, procedure: dict) -> dict:
    """
    Generate a 96-well microplate layout with simulated OD600 readings.
    Rows A–H, Columns 1–12.  Wells are color-coded by optical density.
    """
    ROWS = list("ABCDEFGH")          # 8 rows
    COLS = list(range(1, 13))        # 12 columns

    N0   = params.get("initial_population", 100)
    K    = params.get("carrying_capacity", 1e6)
    r    = params.get("growth_rate", 0.5)
    t_end = params.get("time_hours", 24)

    # Simulate OD600 at t_end for each well with mild noise
    rng = np.random.default_rng(seed=42)
    od_max = 1.5   # typical OD600 saturation in a well

    wells = []
    for ri, row in enumerate(ROWS):
        for ci, col in enumerate(COLS):
            # First 3 wells of row A are negative controls
            is_control = (ri == 0 and ci < 3)
            is_blank   = (ri == 7 and ci >= 9)  # H10–H12 blanks

            if is_control:
                od = round(float(rng.uniform(0.03, 0.07)), 3)
                sample_type = "control"
                label = "Control"
            elif is_blank:
                od = round(float(rng.uniform(0.0, 0.02)), 3)
                sample_type = "blank"
                label = "Blank"
            else:
                # Logistic growth with biological noise
                noise = float(rng.normal(0, 0.04))
                t_sample = t_end * (0.6 + ri * 0.05)
                N_t = K / (1 + ((K - N0) / N0) * math.exp(-r * t_sample))
                od_raw = od_max * (N_t / K) + noise
                od = round(max(0.02, min(od_raw, 1.8)), 3)
                sample_type = "positive" if od > 0.2 else "negative"
                label = f"S{ri * 12 + ci}"

            wells.append({
                "id":   f"{row}{col}",
                "row":  ri,
                "col":  ci,
                "od600": od,
                "sample_type": sample_type,
                "label": label,
                "time_h": round(t_end * (0.6 + ri * 0.05), 1),
            })

    # Aggregate stats
    exp_wells = [w for w in wells if w["sample_type"] == "positive"]
    neg_wells = [w for w in wells if w["sample_type"] == "negative"]
    ctrl_ods  = [w["od600"] for w in wells if w["sample_type"] == "control"]
    sample_ods = [w["od600"] for w in wells if w["sample_type"] not in ("control", "blank")]

    return {
        "lab_type": "sample_testing",
        "title":    f"96-Well Microplate — Bacterial Growth Assay (t={t_end}h)",
        "width":    760,
        "height":   480,
        "plate": {
            "rows":  len(ROWS),
            "cols":  len(COLS),
            "label": "96-Well Microplate",
            "wells": wells,
        },
        "stats": {
            "total_wells":      len(wells),
            "positive_wells":   len(exp_wells),
            "negative_wells":   len(neg_wells),
            "control_wells":    sum(1 for w in wells if w["sample_type"] == "control"),
            "blank_wells":      sum(1 for w in wells if w["sample_type"] == "blank"),
            "mean_od600":       round(float(np.mean(sample_ods)), 3) if sample_ods else 0,
            "max_od600":        round(float(np.max(sample_ods)), 3)  if sample_ods else 0,
            "control_mean_od":  round(float(np.mean(ctrl_ods)), 3)   if ctrl_ods  else 0,
        },
        "legend": [
            {"color": "#1a472a", "label": "High growth (OD600 > 1.0)"},
            {"color": "#2d6a4f", "label": "Moderate growth (0.5–1.0)"},
            {"color": "#52b788", "label": "Low growth (0.2–0.5)"},
            {"color": "#b7e4c7", "label": "Minimal growth (0.05–0.2)"},
            {"color": "#f1f5f9", "label": "Control / Blank (< 0.05)"},
        ],
    }

