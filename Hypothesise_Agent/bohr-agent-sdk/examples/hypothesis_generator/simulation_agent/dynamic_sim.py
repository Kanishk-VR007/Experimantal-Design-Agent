"""
Dynamic Scientific Simulation & 2D Visualization Synthesizer
============================================================
Used whenever an experiment is novel or outside the built-in fixed templates
(e.g., Wheatstone bridge strain gauges, specific chemical reactions like
Ni + Cl2, RC charging, Michaelis-Menten enzyme kinetics, thermal conduction).

Synthesizes self-contained NumPy/SciPy Python code via the configured local LLM,
executes it in a restricted scientific sandbox with automatic error-feedback retry,
validates all 2D plot arrays (x/y alignment, finite values, non-trivial variation),
and outputs rich multi-perspective Plotly plot specifications.
"""

import os
import sys
import ast
import subprocess
import json
import logging
import re
import math
import inspect
import traceback
import itertools
import functools
import collections
import statistics
import numpy as np
import scipy
import scipy.integrate
import scipy.optimize
import scipy.stats
import scipy.signal
import scipy.special
import scipy.interpolate
from typing import Dict, Any, List, Optional, Tuple
from .llm_client import chat_completion, get_llm_config, strip_thinking_tags

logger = logging.getLogger(__name__)

ALLOWED_IMPORTS = {
    "math": math,
    "numpy": np,
    "np": np,
    "scipy": scipy,
    "scipy.integrate": scipy.integrate,
    "scipy.optimize": scipy.optimize,
    "scipy.stats": scipy.stats,
    "scipy.signal": scipy.signal,
    "scipy.special": scipy.special,
    "scipy.interpolate": scipy.interpolate,
    "statistics": statistics,
    "itertools": itertools,
    "functools": functools,
    "collections": collections,
}

def make_plot(
    title: str,
    x_label: str,
    y_label: str,
    x: Any,
    y: Any,
    series_name: str = "Primary Curve",
    plot_type: str = "line",
    extra: Any = None,
) -> dict:
    """Helper available inside generated scripts to construct aligned 2D plot dicts safely."""
    ptype = str(plot_type or "line").lower()
    if ptype == "bar" and isinstance(x, (list, tuple, np.ndarray)) and any(isinstance(v, str) for v in x):
        x_out = [str(v) for v in x]
    else:
        x_out = np.asarray(x, dtype=float).tolist()
    y_out = np.asarray(y, dtype=float).tolist()
    extra_out = []
    if extra:
        for item in extra:
            if isinstance(item, dict):
                extra_out.append({
                    "y": np.asarray(item.get("y", []), dtype=float).tolist(),
                    "name": str(item.get("name", "Comparison")),
                    "color": item.get("color", "#10b981"),
                })
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                sname = str(item[0])
                sy = item[1]
                scol = item[2] if len(item) >= 3 else "#10b981"
                extra_out.append({
                    "y": np.asarray(sy, dtype=float).tolist(),
                    "name": sname,
                    "color": scol,
                })
    return {
        "plot_type": ptype,
        "title": str(title),
        "x_label": str(x_label),
        "y_label": str(y_label),
        "x": x_out,
        "y": y_out,
        "series_name": str(series_name),
        "extra_series": extra_out or None,
    }


def _build_prefill_header(parameters: dict, domain: str = "general") -> str:
    """Build deterministic NumPy/SciPy import header with experiment scalars and physical constants pre-bound."""
    params = parameters if isinstance(parameters, dict) else {}
    lines = [
        "# Pure vectorized NumPy/SciPy simulation (no matplotlib/plt/os/sys imports)",
        "import math",
        "import numpy as np",
        "from scipy import stats, optimize, signal, interpolate",
        "from scipy.integrate import solve_ivp",
        "",
        "N = 100",
    ]
    for k, v in params.items():
        if isinstance(k, str) and k.isidentifier() and k.isascii():
            if isinstance(v, (int, float, bool, str)):
                lines.append(f"{k} = {repr(v)}")
    if "nominal_resistance_ohm" in params and "R0" not in params:
        lines.append("R0 = float(nominal_resistance_ohm)")
    if "gauge_factor" in params and "GF" not in params:
        lines.append("GF = float(gauge_factor)")
        lines.append("k = float(gauge_factor)")
    if "excitation_voltage_V" in params and "V_ex" not in params:
        lines.append("V_ex = float(excitation_voltage_V)")
    if domain == "chemistry":
        if "R" not in params:
            lines.append("R = 8.314  # J/(mol*K)")
        if "temperature_K" in params and "T" not in params:
            lines.append("T = float(temperature_K)")
    elif domain in ("physics", "mechanical_engineering", "civil_engineering"):
        if "g" not in params and "gravity" not in params:
            lines.append("g = 9.81")
    lines.append('# Helper syntax: plot_1 = make_plot(title="...", x_label="...", y_label="...", x=x_arr, y=y_arr, series_name="Primary Curve", extra=[("Comparison", y2_arr, "#10b981")])')
    lines.append("# Define flat named 1D arrays first (never write literal '...' or np.random noise), then call make_plot(...) (~35 lines):")
    lines.append("")
    return "\n".join(lines)


def _safe_import(name, globals=None, locals=None, fromlist=(), level=0):
    """Allow importing strictly allowlisted scientific math/array modules."""
    root = name.split(".")[0]
    if name in ALLOWED_IMPORTS:
        return ALLOWED_IMPORTS[name]
    if root in ALLOWED_IMPORTS:
        return ALLOWED_IMPORTS[root]
    raise ImportError(f"Module '{name}' is not allowlisted in the scientific sandbox.")


def _extract_python_code(raw: str, prefill_header: str = "") -> str:
    """Cleanly extract executable Python code from an LLM response."""
    cleaned = strip_thinking_tags(raw or "")
    if prefill_header and prefill_header.splitlines()[0] not in cleaned:
        # Remove leading markdown fence if model repeated it before body
        cleaned = re.sub(r"^```(?:python|py)?\s*\n?", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\n?```\s*$", "", cleaned, flags=re.IGNORECASE)
        return (prefill_header + cleaned).strip()
    if not cleaned:
        return ""
    fenced = re.findall(r"```(?:python|py)?\s*\n(.*?)```", cleaned, flags=re.IGNORECASE | re.DOTALL)
    code = fenced[-1] if fenced else cleaned
    code = re.sub(r"^```(?:python|py)?\s*", "", code, flags=re.IGNORECASE)
    code = re.sub(r"```\s*$", "", code, flags=re.IGNORECASE)
    return code.strip()


class LLMSimulationGenerator:
    """
    Prompts the local LLM (LM Studio OREAL-DeepSeek-R1-Distill-Qwen-7B primary)
    with full scientific context to synthesize accurate NumPy/SciPy simulation code
    and structured 2D visualization specs.
    """

    def __init__(self, model: Optional[str] = None):
        cfg = get_llm_config()
        self.model = model or cfg["lmstudio_model"]

    def generate_code(
        self,
        topic: str,
        hypothesis: str,
        parameters: dict,
        domain: str,
        refinement: Optional[dict] = None,
        steps: Optional[List[str]] = None,
        previous_error: Optional[str] = None,
        temperature: float = 0.05,
    ) -> str:
        ref = refinement or {}
        equations = ref.get("equations") or []
        ind_vars = ref.get("independent_vars") or []
        dep_vars = ref.get("dependent_vars") or []
        ctrl_vars = ref.get("control_vars") or []
        refined_obj = ref.get("refined_objective") or hypothesis

        steps_text = "\n".join(f"- {s}" for s in (steps or [])[:6]) or "Standard controlled variation across independent variable range."
        repair_note = ""
        if previous_error:
            repair_note = (
                f"\nPREVIOUS EXECUTION ERROR TO FIX:\n{previous_error[:600]}\n"
                "Fix the root cause completely and ensure every plot array is finite, non-empty, and equal in length.\n"
            )

        prompt = f"""Write a self-contained, scientifically accurate Python simulation script using NumPy and SciPy for this exact experiment.

Topic: {topic}
Domain: {domain}
Refined Objective: {refined_obj}
Hypothesis: {hypothesis}
Independent Variables: {json.dumps(ind_vars)}
Dependent Variables: {json.dumps(dep_vars)}
Control Variables: {json.dumps(ctrl_vars)}
Governing Equations: {json.dumps(equations)}
Baseline Parameters: {json.dumps(parameters, indent=2)}
Procedure Steps:
{steps_text}
{repair_note}
STRICT REQUIREMENTS:
1. All baseline scalars listed above and `N = 100` are ALREADY defined in scope. Continue cleanly using pure NumPy/SciPy ONLY. NEVER import matplotlib, seaborn, plotly, os, sys, or call plt.*.
2. Model the TRUE governing physical, chemical, or engineering equations for "{topic}" (e.g., Wheatstone bridge delta_V vs strain & quarter/half/full bridge + gauge factor sweep; stoichiometric ODE kinetics with solve_ivp + Arrhenius k(T) vs temperature + enthalpy/conversion curves for chemical reactions; RLC/RC differential transient + Bode response; etc.).
3. Generate 3 distinct, scientifically meaningful 2D plots inside `simulation_results["plots"]`, each with `N = 100` vectorized points (via `np.linspace(..., 100)` or `solve_ivp(..., t_eval=np.linspace(..., 100))`, never hardcoded 5-element arrays):
   - Plot 1 (`plot_1`): Primary independent vs dependent relationship (`N = 100` pts) plus 1-2 comparison curves in `extra_series` (exact same length `N = 100`!).
   - Plot 2 (`plot_2`): Time evolution / temperature / spectral / dynamic response (`N = 100` pts).
   - Plot 3 (`plot_3`): Parametric sensitivity or non-linearity comparison curve (or labeled `bar` comparison across discrete configurations/species).
4. CRITICAL SAFETY & ACCURACY RULES:
   - Use ONLY ASCII variable names (never non-ASCII variable names).
   - Explicitly assign EVERY variable/constant BEFORE using it (never reference undefined aliases like `kappa`, `gf`, `R0`, `R_nominal`, `Ea`, or `T0`, and never reference a dict key inside the same dict literal).
   - NEVER use Python ellipsis (`...`) anywhere in expressions or function calls. Always compute named arrays (`t = np.linspace(...)`, `y1 = ...`) BEFORE passing them to `make_plot(...)`.
   - NEVER add `np.random` noise to primary `y` arrays — compute clean, exact deterministic physical/chemical equations! (If showing measurement noise, put it only inside `extra_series`).
   - Convert activation energies in kJ/mol to J/mol (`* 1000.0`) when using `R = 8.314`: e.g. `k = pre_exponential_factor * np.exp(-(activation_energy_kJ * 1000.0) / (R * T))`. For reaction kinetics, prefer closed-form vectorized equations (`C0 * np.exp(-k * t)`) or `solve_ivp(..., method="Radau")`, and NEVER write `while` loops.
   - Assign flat 1D NumPy arrays first, and NEVER call `.tolist()` manually — pass NumPy arrays directly into `make_plot(...)`!
   - Never leave `# Add other plots...` placeholder comments; define all 3 plots completely (~30-45 lines total).
5. ALWAYS pass KEYWORD ARGUMENTS to `make_plot(...)` so labels cannot be swapped:
   plot_1 = make_plot(title="Primary Relationship", x_label="X (unit)", y_label="Y (unit)", x=x1, y=y1, series_name="Primary Curve", extra=[("Comparison", y2, "#10b981")])
   - `x` MUST be ascending (`np.linspace(low, high, N)`) and match `x_label`; `y` MUST match `y_label`.
   - Use `plot_type="line"` for continuous N=100 sweeps (use `plot_type="bar"` ONLY for <= 8 discrete string categories).
6. End cleanly right after defining `simulation_results`:
simulation_results = {{
    "numerical_results": {{
        "primary_metrics": {{...}},
        "operating_parameters": {{...}}
    }},
    "plots": [plot_1, plot_2, plot_3],
    "observations": [...]
}}
"""
        prefill_header = _build_prefill_header(parameters, domain=domain)
        prefill_content = f"<think>\n</think>\n```python\n{prefill_header}"
        raw = chat_completion(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert computational physics, chemistry, and engineering simulation engineer. "
                        "Continue the Python script concisely (~35 lines) using pure ASCII variables and `make_plot(...)` to define `plot_1`, `plot_2`, `plot_3` inside `simulation_results`."
                    ),
                },
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": prefill_content},
            ],
            temperature=temperature,
            max_tokens=1500,
            timeout=90,
            stop=["\n```"],
        )
        return _extract_python_code(raw, prefill_header=prefill_header)


class SandboxExecutionRunner:
    """Executes generated Python simulation code in a restricted scientific namespace."""

    def __init__(self):
        safe_builtins = dict(__builtins__) if isinstance(__builtins__, dict) else dict(vars(__builtins__))
        safe_builtins["__import__"] = _safe_import
        # Block dangerous file/process operations
        for blocked in ("open", "eval", "exec", "compile", "input"):
            safe_builtins.pop(blocked, None)

        self.allowed_globals = {
            "__builtins__": safe_builtins,
            "np": np,
            "numpy": np,
            "scipy": scipy,
            "stats": scipy.stats,
            "optimize": scipy.optimize,
            "signal": scipy.signal,
            "interpolate": scipy.interpolate,
            "integrate": scipy.integrate,
            "math": math,
            "solve_ivp": scipy.integrate.solve_ivp,
            "make_plot": make_plot,
        }

    def convert_to_serializable(self, obj):
        if isinstance(obj, np.ndarray):
            return [self.convert_to_serializable(v) for v in obj.tolist()]
        if isinstance(obj, dict):
            return {str(k): self.convert_to_serializable(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [self.convert_to_serializable(v) for v in obj]
        if isinstance(obj, (np.floating, float)):
            val = float(obj)
            return val if math.isfinite(val) else 0.0
        if isinstance(obj, (np.integer, int)) and not isinstance(obj, bool):
            return int(obj)
        return obj

    def _extract_results(self, scope: dict) -> dict:
        aliases = ["simulation_results", "results", "result", "sim_data", "output", "data"]
        for alias in aliases:
            if alias in scope and isinstance(scope[alias], dict):
                return scope[alias]

        for key, val in list(scope.items()):
            if callable(val) and not key.startswith("__"):
                try:
                    if len(inspect.signature(val).parameters) == 0:
                        res = val()
                        if isinstance(res, dict):
                            return res
                except Exception:
                    pass

        harvested = {}
        for key, val in scope.items():
            if not key.startswith("__") and not callable(val) and type(val).__name__ != "module":
                if isinstance(val, (list, np.ndarray, int, float)):
                    harvested[key] = val

        if harvested:
            return harvested

        raise ValueError("Script executed but did not produce a 'simulation_results' dictionary.")

    def _execute_local(self, code: str) -> dict:
        if not code or len(code) < 20:
            raise ValueError("Generated Python code was empty or incomplete.")
        tree = ast.parse(code)
        if any(isinstance(n, ast.Constant) and n.value is Ellipsis for n in ast.walk(tree)):
            raise ValueError("Generated code contained invalid placeholder ellipsis '...'; assign complete expressions.")
        scope = dict(self.allowed_globals)
        try:
            exec(code, scope)
            results = self._extract_results(scope)
            return self.convert_to_serializable(results)
        except Exception as e:
            frames = [f for f in traceback.extract_tb(e.__traceback__) if f.filename == "<string>"]
            loc = f" (script line {frames[-1].lineno}: {frames[-1].line})" if frames else ""
            raise RuntimeError(f"{type(e).__name__}: {e}{loc}")

    def run(self, code: str, timeout: int = 12) -> dict:
        """Execute generated code in an isolated child Python process with hard OS timeout."""
        if not code or len(code) < 20:
            raise ValueError("Generated Python code was empty or incomplete.")

        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        driver = (
            "import sys, json; "
            "sys.path.insert(0, sys.argv[1]); "
            "from simulation_agent.dynamic_sim import SandboxExecutionRunner; "
            "payload = json.loads(sys.stdin.read());\n"
            "try:\n"
            "    res = SandboxExecutionRunner()._execute_local(payload['code'])\n"
            "    print('__SIM_JSON_RESULT__' + json.dumps(res))\n"
            "except Exception as exc:\n"
            "    print('__SIM_JSON_ERROR__' + str(exc))\n"
            "    sys.exit(2)"
        )
        try:
            proc = subprocess.run(
                [sys.executable, "-c", driver, project_root],
                input=json.dumps({"code": code}),
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(
                f"Execution timed out (>{timeout}s): likely stiff ODE in solve_ivp or an infinite loop. "
                "Use closed-form analytical kinetics or solve_ivp(..., method='Radau'), convert kJ/mol*1000, and avoid while loops."
            )

        for line in reversed(proc.stdout.splitlines()):
            if line.startswith("__SIM_JSON_RESULT__"):
                return json.loads(line[len("__SIM_JSON_RESULT__"):])
            if line.startswith("__SIM_JSON_ERROR__"):
                raise RuntimeError(line[len("__SIM_JSON_ERROR__"):])

        if proc.returncode != 0:
            err_detail = (proc.stderr or proc.stdout or "Unknown subprocess error").strip()
            raise RuntimeError(err_detail[-1500:])

        raise RuntimeError(f"Sandbox subprocess finished without serialized results. Output: {proc.stdout[:400]}")


def _clean_1d_sequence(seq: Any, allow_strings: bool = False) -> List[Any]:
    if not isinstance(seq, (list, tuple)):
        return []
    out: List[Any] = []
    for item in seq:
        if isinstance(item, (int, float)) and not isinstance(item, bool):
            val = float(item)
            out.append(val if math.isfinite(val) else 0.0)
        elif allow_strings and isinstance(item, str):
            out.append(item)
    return out


def _normalize_and_validate_plots(
    results: dict,
    topic: str,
    min_plots: int = 1,
    min_curve_points: int = 5,
) -> Tuple[dict, List[dict], List[str]]:
    """
    Extract, validate, and align numerical metrics, 2D Plotly specs, and observations
    from sandbox results. Rejects empty, sparse, or malformed plots cleanly.
    """
    raw_plots = results.get("plots") or results.get("plot_data") or []
    raw_num = results.get("numerical_results")
    raw_obs = results.get("observations") if isinstance(results.get("observations"), list) else []

    numerical_results: Dict[str, Any] = {}
    if isinstance(raw_num, dict):
        numerical_results.update(raw_num)

    validated_plots: List[dict] = []

    if isinstance(raw_plots, list):
        for idx, p in enumerate(raw_plots):
            if not isinstance(p, dict):
                continue
            ptype = str(p.get("plot_type", "line")).lower()
            if ptype not in ("line", "scatter", "bar"):
                ptype = "line"
            x_seq = _clean_1d_sequence(p.get("x"), allow_strings=(ptype == "bar"))
            y_seq = _clean_1d_sequence(p.get("y"), allow_strings=False)
            n = min(len(x_seq), len(y_seq))
            required_n = 2 if ptype == "bar" else min_curve_points
            if n < required_n:
                continue
            x_seq = x_seq[:n]
            y_seq = y_seq[:n]

            valid_extra = []
            for s in (p.get("extra_series") or []):
                if not isinstance(s, dict):
                    continue
                sy = _clean_1d_sequence(s.get("y"), allow_strings=False)
                if len(sy) >= n:
                    valid_extra.append({
                        "y": sy[:n],
                        "name": str(s.get("name", "Comparison")),
                        "color": s.get("color"),
                    })

            # Normalize strictly descending monotonic x to ascending left-to-right order
            if ptype == "line" and len(x_seq) >= 3 and all(isinstance(v, float) for v in x_seq):
                if all(x_seq[i] > x_seq[i + 1] for i in range(len(x_seq) - 1)):
                    x_seq = list(reversed(x_seq))
                    y_seq = list(reversed(y_seq))
                    for item in valid_extra:
                        item["y"] = list(reversed(item["y"]))

            validated_plots.append({
                "plot_type": ptype,
                "title": str(p.get("title") or f"{topic[:40]} — Curve {idx + 1}"),
                "x_label": str(p.get("x_label") or "Independent Variable"),
                "y_label": str(p.get("y_label") or "Measured Response"),
                "x": x_seq,
                "y": y_seq,
                "series_name": str(p.get("series_name") or "Primary Response"),
                "extra_series": valid_extra or None,
            })

    # Fallback heuristic: reconstruct labeled plots from scalar + equal-length 1D arrays
    arrays: Dict[str, List[float]] = {}
    for k, v in results.items():
        if k in ("plots", "plot_data", "numerical_results", "observations"):
            continue
        if isinstance(v, list) and len(v) >= 4 and all(isinstance(el, (int, float)) for el in v):
            arrays[k] = [float(el) if math.isfinite(float(el)) else 0.0 for el in v]
        elif not isinstance(v, dict) and not isinstance(v, list):
            numerical_results[k] = v
        elif isinstance(v, dict):
            numerical_results[k] = v

    if not validated_plots and arrays:
        # Pick best X-axis candidate based on variable naming rather than blind dict order
        x_priority = ("time", "t", "strain", "force", "load", "temp", "temperature", "freq", "frequency", "voltage", "distance", "x")
        x_key = None
        for cand in x_priority:
            for ak in arrays:
                if cand in ak.lower():
                    x_key = ak
                    break
            if x_key:
                break
        if x_key is None:
            x_key = next(iter(arrays))

        x_val = arrays[x_key]
        other_keys = [k for k in arrays if k != x_key]
        if not other_keys:
            validated_plots.append({
                "plot_type": "line",
                "title": f"{x_key.replace('_', ' ').title()} Profile",
                "x_label": "Sample Index",
                "y_label": x_key.replace("_", " ").title(),
                "x": list(range(len(x_val))),
                "y": x_val,
                "series_name": x_key.replace("_", " ").title(),
            })
        else:
            for y_key in other_keys[:4]:
                y_val = arrays[y_key]
                n = min(len(x_val), len(y_val))
                if n >= 2:
                    validated_plots.append({
                        "plot_type": "line",
                        "title": f"{y_key.replace('_', ' ').title()} vs {x_key.replace('_', ' ').title()}",
                        "x_label": x_key.replace("_", " ").title(),
                        "y_label": y_key.replace("_", " ").title(),
                        "x": x_val[:n],
                        "y": y_val[:n],
                        "series_name": y_key.replace("_", " ").title(),
                    })

    if not validated_plots:
        raise ValueError(
            f"Simulation script produced zero dense 2D plot arrays (expected >= {min_curve_points} points per curve using np.linspace(..., 100))."
        )

    if len(validated_plots) < min_plots:
        raise ValueError(
            f"Generated only {len(validated_plots)} valid 2D plot(s); generate all {min_plots} distinct plots in simulation_results['plots'] (each >= {min_curve_points} points)."
        )

    # Verify at least one plot exhibits genuine physical variation (reject degenerate all-zero outputs)
    has_variation = any((max(p["y"]) - min(p["y"])) > 1e-12 for p in validated_plots if p["y"])
    if not has_variation:
        raise ValueError("All generated 2D plots were constant/flat zero arrays.")

    if not numerical_results:
        first_p = validated_plots[0]
        numerical_results["simulated_summary"] = {
            "peak_response": round(max(first_p["y"]), 5),
            "min_response": round(min(first_p["y"]), 5),
            "sample_points": len(first_p["y"]),
        }

    observations = [str(o) for o in raw_obs if str(o).strip()]
    if not observations:
        p0 = validated_plots[0]
        observations = [
            f"Dynamic Python simulation executed {len(validated_plots)} analytical 2D plots for '{topic}'.",
            f"Primary response '{p0['y_label']}' spans [{min(p0['y']):.4g}, {max(p0['y']):.4g}].",
        ]

    return numerical_results, validated_plots, observations


_SAFE_CALLABLES = {
    "abs": np.abs,
    "exp": np.exp,
    "sin": np.sin,
    "cos": np.cos,
    "tan": np.tan,
    "arcsin": np.arcsin,
    "arccos": np.arccos,
    "arctan": np.arctan,
    "sinh": np.sinh,
    "cosh": np.cosh,
    "tanh": np.tanh,
    "sqrt": np.sqrt,
    "log": np.log,
    "ln": np.log,
    "log10": np.log10,
    "log2": np.log2,
    "power": np.power,
    "minimum": np.minimum,
    "maximum": np.maximum,
    "where": np.where,
    "clip": np.clip,
    "min": np.minimum,
    "max": np.maximum,
    "pow": np.power,
    "round": np.round,
    "floor": np.floor,
    "ceil": np.ceil,
    "linspace": np.linspace,
}

_SAFE_AST_NODES = (
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.BoolOp,
    ast.Compare,
    ast.IfExp,
    ast.Call,
    ast.Name,
    ast.Constant,
    ast.Attribute,
    ast.Subscript,
    ast.Slice,
    ast.List,
    ast.Tuple,
    ast.keyword,
    ast.Load,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.FloorDiv,
    ast.Mod,
    ast.Pow,
    ast.UAdd,
    ast.USub,
    ast.Not,
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    ast.And,
    ast.Or,
)


def _normalize_math_expr(expr: str) -> str:
    """Strip accidental nested quotes, optional LHS=, and unicode/Greek math notation to ASCII Python syntax."""
    cleaned = expr.strip()
    while len(cleaned) >= 2 and (
        (cleaned[0] == '"' and cleaned[-1] == '"') or (cleaned[0] == "'" and cleaned[-1] == "'")
    ):
        cleaned = cleaned[1:-1].strip()
    # Unwrap equations written as 'y(t) = A * exp(-k * t)' to RHS expression cleanly
    if "=" in cleaned and not any(op in cleaned for op in ("==", "!=", "<=", ">=")) and cleaned.count("=") == 1:
        cleaned = cleaned.split("=", 1)[1].strip()
    return (
        cleaned.replace("ε", "epsilon")
        .replace("σ", "sigma")
        .replace("τ", "tau")
        .replace("θ", "theta")
        .replace("ω", "omega")
        .replace("π", "pi")
        .replace("^", "**")
        .replace("−", "-")
        .replace("×", "*")
    )


def _safe_eval_expr(expr: Any, env: Dict[str, Any]) -> Any:
    """Safely evaluate a mathematical expression against NumPy/math and scenario scalars."""
    if isinstance(expr, (int, float)) and not isinstance(expr, bool):
        return float(expr)
    if not isinstance(expr, str) or not expr.strip():
        raise ValueError("Empty mathematical expression.")

    cleaned = _normalize_math_expr(expr)
    tree = ast.parse(cleaned, mode="eval")
    for node in ast.walk(tree):
        if not isinstance(node, _SAFE_AST_NODES):
            raise ValueError(f"Disallowed expression syntax: {type(node).__name__}")
        if isinstance(node, ast.Attribute):
            if not isinstance(node.value, ast.Name) or node.value.id not in ("np", "math"):
                raise ValueError(f"Disallowed attribute access on {ast.dump(node)}")
            if node.attr.startswith("_"):
                raise ValueError("Disallowed private attribute access.")
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id not in _SAFE_CALLABLES:
                    raise ValueError(f"Function '{node.func.id}' is not allowlisted.")
            elif isinstance(node.func, ast.Attribute):
                if not isinstance(node.func.value, ast.Name) or node.func.value.id not in ("np", "math"):
                    raise ValueError("Only np.* and math.* functions are allowed.")
            else:
                raise ValueError("Disallowed dynamic callable invocation.")

    compiled = compile(tree, "<math_expr>", "eval")
    local_env = {"np": np, "math": math, "pi": math.pi, "e": math.e}
    local_env.update(_SAFE_CALLABLES)
    local_env.update(env)
    return eval(compiled, {"__builtins__": {}}, local_env)


def _extract_json_model(raw: str, prefix: str = "") -> dict:
    """Extract and parse a JSON object cleanly from LM Studio completion text."""
    text = strip_thinking_tags(raw or "")
    if prefix and not text.lstrip().startswith("{"):
        text = prefix + text
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE)
    # Strip single-line and inline // comments outside URLs, accidental double-quoted values, trailing commas, and stray LaTeX escapes
    text = re.sub(r"(?m)(?<![:\"])//.*$", "", text)
    text = re.sub(r':\s*""([^"\n]+)""', r': "\1"', text)
    # Auto-quote unquoted math formulas after a key (e.g. "y_expr": (w * x**2) / 24, or "y_expr": 0.5 * w * (L - x)**2)
    def _quote_unquoted_val(m):
        k = m.group(1)
        val = m.group(2).strip()
        sep = m.group(3)
        if val in ("true", "false", "null") or (val.startswith('"') and val.endswith('"')) or (val.startswith('{') or val.startswith('[')):
            return m.group(0)
        if re.match(r'^[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?$', val):
            return m.group(0)
        safe_val = val.replace('"', '\\"')
        return f'{k}: "{safe_val}"{sep}'

    text = re.sub(r'("y_expr"|"expr"|"expression"|"y"|"formula"|"s_expr"|"val")\s*:\s*([^,\n}\]]+?)(\s*[,}\]\n])', _quote_unquoted_val, text)
    # Quote any values starting with parenthesis (e.g. : (a + b) / c,)
    text = re.sub(r'(:\s*)(\([^\n,}\]]+\))(\s*[,}\]\n])', r'\1"\2"\3', text)
    # Quote bare variable identifiers used as JSON values (e.g. "x_max": reaction_time_s)
    text = re.sub(
        r'(:\s*)([A-Za-z_][A-Za-z0-9_]*)(\s*[,}\]])',
        lambda m: m.group(0) if m.group(2) in ("true", "false", "null") else f'{m.group(1)}"{m.group(2)}"{m.group(3)}',
        text,
    )
    text = re.sub(r",\s*([}\]])", r"\1", text)
    text = re.sub(r'\\(?!["\\/bfnrtu])', r"\\\\", text)
    idx = text.find("{")
    if idx == -1:
        raise ValueError("LLM response did not contain a JSON object.")
    obj, _ = json.JSONDecoder().raw_decode(text[idx:])
    if not isinstance(obj, dict):
        raise ValueError("Decoded JSON root was not a dictionary.")
    return obj


#: Universal physical constants. Explicit procedure parameters may still override them.
_UNIVERSAL_CONSTANTS: Dict[str, float] = {
    "R_gas": 8.314,            # J/(mol*K) ideal gas constant
    "g": 9.81,                 # m/s^2 standard gravity
    "k_B": 1.380649e-23,       # J/K Boltzmann constant
    "N_A": 6.02214076e23,      # 1/mol Avogadro constant
    "F_faraday": 96485.33212,  # C/mol Faraday constant
}

#: Shorthand alias -> ordered (source parameter, scale, offset) candidates.
#: Aliases are derived ONLY from real procedure parameters, never pre-seeded.
_ALIAS_SOURCES: Dict[str, Tuple[Tuple[str, float, float], ...]] = {
    # Structural / mechanical
    "L": (
        ("span_m", 1.0, 0.0), ("beam_span_m", 1.0, 0.0), ("length_m", 1.0, 0.0),
        ("beam_length_m", 1.0, 0.0), ("rod_length_m", 1.0, 0.0),
        ("span_cm", 1e-2, 0.0), ("span_mm", 1e-3, 0.0), ("length_mm", 1e-3, 0.0),
        ("span", 1.0, 0.0), ("length", 1.0, 0.0),
    ),
    "E": (
        ("elastic_modulus_Pa", 1.0, 0.0), ("youngs_modulus_Pa", 1.0, 0.0),
        ("elastic_modulus_GPa", 1e9, 0.0), ("youngs_modulus_GPa", 1e9, 0.0),
        ("elastic_modulus_MPa", 1e6, 0.0), ("youngs_modulus_MPa", 1e6, 0.0),
    ),
    "I": (
        ("moment_of_inertia_m4", 1.0, 0.0), ("second_moment_of_area_m4", 1.0, 0.0),
        ("area_moment_of_inertia_m4", 1.0, 0.0), ("moment_inertia_m4", 1.0, 0.0),
        ("moment_of_inertia_mm4", 1e-12, 0.0),
    ),
    "w": (
        ("distributed_load_kN_per_m", 1e3, 0.0), ("load_kN_per_m", 1e3, 0.0),
        ("udl_kN_per_m", 1e3, 0.0), ("distributed_load_N_per_m", 1.0, 0.0),
        ("load_N_per_m", 1.0, 0.0),
    ),
    "P": (
        ("load_N", 1.0, 0.0), ("applied_load_N", 1.0, 0.0), ("point_load_N", 1.0, 0.0),
        ("axial_load_N", 1.0, 0.0), ("force_N", 1.0, 0.0), ("load_kN", 1e3, 0.0),
    ),
    "F": (
        ("force_N", 1.0, 0.0), ("applied_load_N", 1.0, 0.0), ("load_N", 1.0, 0.0),
        ("point_load_N", 1.0, 0.0), ("thrust_N", 1.0, 0.0), ("load_kN", 1e3, 0.0),
    ),
    # Electrical / instrumentation
    "R0": (
        ("nominal_resistance_ohm", 1.0, 0.0), ("resistance_ohm", 1.0, 0.0),
        ("unstrained_resistance_ohm", 1.0, 0.0), ("gauge_resistance_ohm", 1.0, 0.0),
        ("R_nominal_ohm", 1.0, 0.0),
    ),
    "R": (
        ("nominal_resistance_ohm", 1.0, 0.0), ("resistance_ohm", 1.0, 0.0),
        ("unstrained_resistance_ohm", 1.0, 0.0),
    ),
    "GF": (("gauge_factor", 1.0, 0.0), ("gauge_factor_gf", 1.0, 0.0)),
    "V_ex": (
        ("excitation_voltage_V", 1.0, 0.0), ("bridge_voltage_V", 1.0, 0.0),
        ("supply_voltage_V", 1.0, 0.0),
    ),
    "V0": (
        ("initial_voltage_V", 1.0, 0.0), ("source_voltage_V", 1.0, 0.0),
        ("applied_voltage_V", 1.0, 0.0), ("dc_voltage_V", 1.0, 0.0),
    ),
    "C": (
        ("capacitance_F", 1.0, 0.0), ("capacitance_mF", 1e-3, 0.0),
        ("capacitance_uF", 1e-6, 0.0), ("capacitance_nF", 1e-9, 0.0),
    ),
    # Thermal / reaction kinetics
    "T": (
        ("temperature_K", 1.0, 0.0), ("temperature_C", 1.0, 273.15),
        ("temperature_celsius", 1.0, 273.15), ("temperature_Celsius", 1.0, 273.15),
    ),
    "Ea": (
        ("activation_energy_kJ", 1e3, 0.0), ("activation_energy_J", 1.0, 0.0),
        ("activation_energy_kJ_per_mol", 1e3, 0.0),
    ),
    "Ea_J": (
        ("activation_energy_kJ", 1e3, 0.0), ("activation_energy_J", 1.0, 0.0),
        ("activation_energy_kJ_per_mol", 1e3, 0.0), ("Ea", 1.0, 0.0),
    ),
    "A": (
        ("pre_exponential_factor", 1.0, 0.0), ("frequency_factor", 1.0, 0.0),
        ("arrhenius_pre_factor", 1.0, 0.0),
    ),
    "C0": (
        ("initial_concentration_M", 1.0, 0.0), ("initial_concentration_mol_per_L", 1.0, 0.0),
    ),
    # Enzyme kinetics
    "Vmax": (("max_velocity", 1.0, 0.0), ("v_max", 1.0, 0.0), ("V_max", 1.0, 0.0)),
    "V_max": (("max_velocity", 1.0, 0.0), ("v_max", 1.0, 0.0), ("Vmax", 1.0, 0.0)),
    "Km": (("michaelis_constant", 1.0, 0.0), ("michaelis_constant_M", 1.0, 0.0), ("K_m", 1.0, 0.0)),
    "K_m": (("michaelis_constant", 1.0, 0.0), ("michaelis_constant_M", 1.0, 0.0), ("Km", 1.0, 0.0)),
    "Ki": (("inhibition_constant", 1.0, 0.0), ("K_i", 1.0, 0.0)),
    "K_i": (("inhibition_constant", 1.0, 0.0), ("Ki", 1.0, 0.0)),
    "kcat": (("turnover_number", 1.0, 0.0), ("k_cat", 1.0, 0.0)),
    "k_cat": (("turnover_number", 1.0, 0.0), ("kcat", 1.0, 0.0)),
}

#: Aliases whose physical meaning changes with domain (skipped for the listed domains).
_ALIAS_DOMAIN_EXCLUDES: Dict[str, Tuple[str, ...]] = {
    # R is the gas constant in chemistry/thermodynamics but a resistance elsewhere
    "R": ("chem", "reaction", "thermodynam", "arrhenius", "enzyme", "biochem", "michaelis"),
    # I is moment of inertia only in structural/civil/mechanical; inhibitor conc in bio/chem; current in electronics
    "I": ("bio", "enzyme", "michaelis", "chem", "electr", "circuit"),
}

#: Synonym groups kept in sync once one spelling resolves (never overwrites).
_ALIAS_EQUIVALENTS: Tuple[Tuple[str, ...], ...] = (
    ("L", "length", "span"),
    ("E", "E_modulus", "youngs_modulus"),
    ("I", "I_moment"),
    ("P", "load", "force"),
    ("V_ex", "Vex"),
    ("Vmax", "V_max"),
    ("Km", "K_m"),
    ("Ki", "K_i"),
    ("kcat", "k_cat"),
    ("GF", "G_F"),
    ("R0", "R_nominal"),
    ("Ea", "Ea_J"),
)

#: Domain keyword groups -> defaults applied ONLY to names still absent after alias resolution.
_DOMAIN_DEFAULT_GROUPS: Tuple[Tuple[str, Tuple[str, ...], Dict[str, float]], ...] = (
    (
        "structural",
        ("civil_engineering", "mechanical_engineering", "structural", "civil", "mechanical", "beam", "truss"),
        {"E": 200e9, "I": 8.333e-6, "L": 3.0, "w": 5000.0, "w0": 5000.0, "P": 1000.0, "F": 1000.0},
    ),
    (
        "electrical",
        ("electronics", "electrical", "electric", "circuit", "wheatstone", "instrumentation", "sensor"),
        {"R0": 1000.0, "R": 1000.0, "V0": 5.0, "V_ex": 5.0, "C": 1e-6, "GF": 2.0, "strain": 0.001, "epsilon": 0.001},
    ),
    (
        "enzyme_kinetics",
        ("biology", "biochem", "enzyme", "michaelis", "metabolic"),
        {"Vmax": 100.0, "V_max": 100.0, "Km": 5.0, "K_m": 5.0, "Ki": 2.5, "K_i": 2.5, "kcat": 10.0},
    ),
    (
        "physics",
        ("physics", "thermodynam", "gas law", "kinetic theory"),
        {"R": 8.314},
    ),
    (
        "chemistry",
        ("chemistry", "chem", "reaction", "thermodynam", "arrhenius"),
        {"A": 1e9, "Ea": 65000.0, "Ea_J": 65000.0, "R": 8.314},
    ),
)

_NUMERIC_TEXT_RE = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$")


def _coerce_numeric(value: Any) -> Optional[float]:
    """Return a finite float for real numbers and plain numeric strings, else None."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float, np.integer, np.floating)):
        fval = float(value)
        return fval if math.isfinite(fval) else None
    if isinstance(value, str):
        text = value.strip().replace(",", "").replace("_", "")
        if _NUMERIC_TEXT_RE.match(text):
            fval = float(text)
            return fval if math.isfinite(fval) else None
    return None


def _build_seed_constants(
    parameters: dict,
    domain: str,
    trace: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Build the scientific evaluation environment with real procedure parameters taking priority.

    Resolution order (a later stage never overwrites an earlier one):
      1. Universal physical constants (R_gas, g, k_B, N_A, F_faraday).
      2. Every numeric procedure parameter, kept verbatim under its long name.
      3. Shorthand aliases derived from those parameters with unit conversion
         (e.g. span_m -> L, elastic_modulus_GPa * 1e9 -> E, load_kN * 1e3 -> P).
      4. Equivalent spellings of an already resolved alias (Vmax/V_max, Km/K_m, ...).
      5. Domain-specific defaults, applied ONLY to names that are still absent.
      6. Derived Arrhenius rate constant when A, Ea, R and T are all available.
    """
    notes: List[str] = trace if trace is not None else []
    defaulted: set = set()

    def _note(message: str) -> None:
        notes.append(message)
        logger.debug("seed: %s", message)

    env: Dict[str, Any] = dict(_UNIVERSAL_CONSTANTS)
    params = parameters if isinstance(parameters, dict) else {}
    domain_text = str(domain or "").strip().lower()

    # 2. Real procedure parameters (shorthand names supplied directly are kept as-is)
    direct_count = 0
    for key, value in params.items():
        if not isinstance(key, str) or not key.isidentifier():
            continue
        fval = _coerce_numeric(value)
        if fval is not None:
            env[key] = fval
            direct_count += 1
            continue
        if isinstance(value, list) and value:
            try:
                env[key] = np.asarray(value, dtype=float)
                direct_count += 1
            except Exception:
                logger.debug("seed: parameter '%s' is not numeric and was skipped", key)
    if direct_count:
        _note(f"{direct_count} procedure parameter value(s) used directly")

    # 3. Derive shorthand aliases from the actual parameters only (multi-pass for chains)
    for _ in range(4):
        resolved_this_pass = 0
        for alias, sources in _ALIAS_SOURCES.items():
            if alias in env:
                continue
            if any(key in domain_text for key in _ALIAS_DOMAIN_EXCLUDES.get(alias, ())):
                continue
            for source, scale, offset in sources:
                raw = _coerce_numeric(env.get(source))
                if raw is None:
                    continue
                value = raw * scale + offset
                if not math.isfinite(value):
                    continue
                env[alias] = value
                resolved_this_pass += 1
                if scale != 1.0 or offset != 0.0:
                    conversion = f"{raw:g} x {scale:g}" + (f" + {offset:g}" if offset else "")
                    _note(f"{alias} = {value:g} derived from parameter '{source}' ({conversion})")
                else:
                    _note(f"{alias} = {value:g} derived from parameter '{source}'")
                break
        if not resolved_this_pass:
            break

    # 4. Keep equivalent spellings of an already resolved alias in sync
    for group in _ALIAS_EQUIVALENTS:
        source_name = next((name for name in group if name in env), None)
        if source_name is None:
            continue
        raw = _coerce_numeric(env.get(source_name))
        if raw is None:
            continue
        for name in group:
            if name not in env:
                env[name] = raw
                _note(f"{name} = {raw:g} mirrored from equivalent name '{source_name}'")

    # 5. Domain-specific defaults for values that are still genuinely absent
    for label, keywords, defaults in _DOMAIN_DEFAULT_GROUPS:
        if not any(keyword in domain_text for keyword in keywords):
            continue
        applied = []
        for name, value in defaults.items():
            if name in env:
                continue
            env[name] = float(value)
            defaulted.add(name)
            applied.append(f"{name}={value:g}")
        if applied:
            _note(f"domain defaults for '{label}' applied (no parameter supplied): {', '.join(applied)}")

    # Strain-gauge convention: symbolic gain k mirrors a user-supplied gauge factor
    if "k" not in env and "GF" in env and "GF" not in defaulted and not any(n in env for n in ("A", "Ea")):
        gf = _coerce_numeric(env.get("GF"))
        if gf:
            env["k"] = gf
            _note(f"k = {gf:g} mirrored from gauge factor GF (strain-gauge convention)")

    # 6. Derived rate constant from the Arrhenius law once inputs are available
    if "k" not in env and all(name in env for name in ("A", "Ea", "R", "T")):
        try:
            rate = float(env["A"]) * math.exp(-float(env["Ea"]) / (float(env["R"]) * float(env["T"])))
            if math.isfinite(rate) and rate > 0:
                env["k"] = rate
                _note(f"k = {rate:.6g} derived from Arrhenius law A*exp(-Ea/(R*T))")
        except Exception:
            pass

    logger.info(
        "seed environment for domain '%s': %d direct parameter(s), %d resolution note(s)",
        domain or "general",
        direct_count,
        len(notes),
    )
    return env


def evaluate_equation_model(
    model_spec: dict,
    topic: str,
    parameters: dict,
    domain: str,
    n_points: int = 120,
    min_plots: int = 2,
) -> dict:
    """Evaluate a declarative JSON scientific equation spec into verified dense 2D plot arrays."""
    seed_trace: List[str] = []
    env = _build_seed_constants(parameters, domain, trace=seed_trace)
    raw_constants = model_spec.get("constants")
    if isinstance(raw_constants, dict):
        pending = dict(raw_constants)
        for _ in range(3):
            next_pending = {}
            for k, v in pending.items():
                if not isinstance(k, str) or not k.isidentifier():
                    continue
                try:
                    val = _safe_eval_expr(v, env)
                    if isinstance(val, (int, float, np.floating, np.integer)):
                        fval = float(val)
                        if math.isfinite(fval):
                            env[k] = fval
                except Exception:
                    next_pending[k] = v
            prev_len = len(pending)
            pending = next_pending
            if not pending or len(pending) == prev_len:
                break
        # Note: optional derived constants referencing unseeded variables are silently
        # skipped unless actually referenced inside a plot expression below.

    raw_plots = model_spec.get("plots") or model_spec.get("2D_plots") or model_spec.get("3D_plots") or []
    if not isinstance(raw_plots, list) or not raw_plots:
        raise ValueError("JSON model must provide distinct plots (target 3).")

    evaluated_plots: List[dict] = []
    plot_errors: List[str] = []
    for idx, p in enumerate(raw_plots[:4]):
        if not isinstance(p, dict):
            continue
        try:
            ptype = str(p.get("plot_type", "line")).lower()
            title = str(p.get("title") or f"{topic[:40]} — Plot {idx + 1}")
            x_label = str(p.get("x_label") or p.get("x_name") or "Independent Variable")
            y_label = str(p.get("y_label") or "Measured Response")
            series_name = str(p.get("series_name") or "Theoretical Curve")

            if ptype == "bar" and isinstance(p.get("categories"), list) and isinstance(p.get("values"), list):
                cats = [str(c) for c in p["categories"]]
                vals = [float(_safe_eval_expr(v, env)) for v in p["values"]]
                n = min(len(cats), len(vals))
                if n >= 2:
                    evaluated_plots.append({
                        "plot_type": "bar",
                        "title": title,
                        "x_label": x_label,
                        "y_label": y_label,
                        "x": cats[:n],
                        "y": vals[:n],
                        "series_name": series_name,
                        "extra_series": None,
                    })
                continue

            x_name_raw = str(p.get("x_name") or "x").strip()
            x_name = x_name_raw
            if not x_name.isidentifier():
                low_xn = (x_name_raw + " " + x_label).lower()
                if "time" in low_xn:
                    x_name = "t"
                elif "temp" in low_xn:
                    x_name = "T"
                elif "strain" in low_xn or "eps" in low_xn:
                    x_name = "strain"
                elif "activation" in low_xn:
                    x_name = "Ea"
                elif "freq" in low_xn:
                    x_name = "freq"
                elif "volt" in low_xn:
                    x_name = "V"
                else:
                    x_name = "x"
            x_min_val = p.get("x_min", 0.0)
            x_max_val = p.get("x_max", 10.0)
            x_min = float(_safe_eval_expr(x_min_val, env)) if isinstance(x_min_val, str) else float(x_min_val)
            x_max = float(_safe_eval_expr(x_max_val, env)) if isinstance(x_max_val, str) else float(x_max_val)
            if not (math.isfinite(x_min) and math.isfinite(x_max)):
                raise ValueError(f"Plot {idx + 1} has non-finite domain bounds [{x_min}, {x_max}].")
            if x_min > x_max:
                x_min, x_max = x_max, x_min
            elif x_min == x_max:
                x_max = x_min + (abs(x_min) * 0.5 or 1.0)

            x_arr = np.linspace(x_min, x_max, n_points)
            local_env = dict(env)
            local_env[x_name] = x_arr
            if x_name in ("strain", "eps", "epsilon"):
                local_env["strain"] = local_env["eps"] = local_env["epsilon"] = x_arr
            elif x_name in ("t", "time"):
                local_env["t"] = local_env["time"] = x_arr
            elif x_name in ("T", "temp", "temperature", "T_K"):
                local_env["T"] = local_env["temp"] = local_env["temperature"] = local_env["T_K"] = x_arr
            elif x_name in ("Ea", "activation_energy_kJ", "Ea_J"):
                if "kj" in (x_name_raw + " " + x_label).lower() and x_max <= 1000.0:
                    local_env["activation_energy_kJ"] = x_arr
                    local_env["Ea"] = local_env["Ea_J"] = x_arr * 1000.0
                else:
                    local_env["Ea"] = local_env["Ea_J"] = x_arr

            y_expr = p.get("y_expr")
            if not y_expr:
                raise ValueError(f"Plot {idx + 1} ('{title}') is missing 'y_expr'.")

            # Pre-resolve any undefined scientific variables in y_expr
            try:
                norm_expr = _normalize_math_expr(str(y_expr))
                parsed_tree = ast.parse(norm_expr, mode="eval")
                for node in ast.walk(parsed_tree):
                    if isinstance(node, ast.Name):
                        nm = node.id
                        if nm not in local_env and nm not in _SAFE_CALLABLES and nm not in ("np", "math", "pi", "e"):
                            low_dom = (domain or "").lower()
                            if nm in ("w", "w0"): local_env[nm] = float(env.get("w", 5000.0))
                            elif nm in ("E", "E_modulus"): local_env[nm] = float(env.get("E", 200e9))
                            elif nm in ("I", "I_moment"):
                                if any(k in low_dom for k in ("bio", "enzyme", "michaelis", "chem")):
                                    local_env[nm] = float(env.get("I", env.get("Ki", 2.5)))
                                elif any(k in low_dom for k in ("electr", "circuit")):
                                    local_env[nm] = float(env.get("I", 1.0))
                                else:
                                    local_env[nm] = float(env.get("I", 8.333e-6))
                            elif nm in ("L", "length", "span"): local_env[nm] = float(env.get("L", 3.0))
                            elif nm in ("P", "F", "load", "force"): local_env[nm] = float(env.get("P", 1000.0))
                            elif nm in ("Vmax", "V_max"): local_env[nm] = float(env.get("Vmax", 100.0))
                            elif nm in ("Km", "K_m"): local_env[nm] = float(env.get("Km", 5.0))
                            elif nm in ("Ki", "K_i"): local_env[nm] = float(env.get("Ki", 2.5))
                            elif nm in ("kcat", "k_cat"): local_env[nm] = float(env.get("kcat", 10.0))
                            elif nm == "R":
                                if any(k in low_dom for k in ("electr", "circuit", "physics")):
                                    local_env[nm] = float(env.get("R", env.get("R0", 1000.0)))
                                else:
                                    local_env[nm] = float(env.get("R_gas", 8.314))
                            elif nm in ("R0", "res"): local_env[nm] = float(env.get("R0", 1000.0))
                            elif nm in ("V", "V0", "voltage"): local_env[nm] = float(env.get("V0", 5.0))
                            elif nm in ("C", "capacitance"): local_env[nm] = float(env.get("C", 1e-6))
                            elif nm in ("g", "gravity"): local_env[nm] = 9.81
                            else: local_env[nm] = 1.0
            except Exception:
                pass

            y_raw = _safe_eval_expr(y_expr, local_env)
            if np.ndim(y_raw) == 0:
                expr_names = [
                    n.id for n in ast.walk(ast.parse(_normalize_math_expr(str(y_expr)), mode="eval"))
                    if isinstance(n, ast.Name)
                ]
                for cand in ("x", "s", "S", "strain", "epsilon", "eps", "t", "time", "temp", "temperature", "T_K", "T", "Ea", "gf", "GF", "freq", "frequency", "omega", "voltage", "V", "load", "force", "w", "I", "conc", "concentration", "sub", "substrate", "inh", "inhibitor"):
                    if cand in expr_names and cand != x_name:
                        local_env[cand] = x_arr
                        y_raw = _safe_eval_expr(y_expr, local_env)
                        if np.ndim(y_raw) > 0 and np.ptp(y_raw) > 1e-12:
                            break
                if np.ndim(y_raw) == 0:
                    for cand in expr_names:
                        if cand not in ("np", "math", "pi", "e") and cand not in _SAFE_CALLABLES:
                            old = local_env.get(cand)
                            local_env[cand] = x_arr
                            try:
                                test_raw = _safe_eval_expr(y_expr, local_env)
                                if np.ndim(test_raw) > 0 and np.ptp(test_raw) > 1e-12:
                                    y_raw = test_raw
                                    break
                            except Exception:
                                pass
                            if old is not None:
                                local_env[cand] = old
            if np.ndim(y_raw) == 0:
                raise ValueError(f"Plot {idx + 1} y_expr '{y_expr}' did not vary with '{x_name}'.")
            y_arr = np.asarray(y_raw, dtype=float)
            if y_arr.shape != x_arr.shape:
                raise ValueError(f"Plot {idx + 1} y_expr shape mismatch: {y_arr.shape} vs {x_arr.shape}")
            if not np.all(np.isfinite(y_arr)):
                finite_mask = np.isfinite(y_arr)
                if np.count_nonzero(finite_mask) >= n_points // 2:
                    y_arr = np.nan_to_num(
                        y_arr,
                        nan=float(np.nanmedian(y_arr[finite_mask])),
                        posinf=float(np.nanmax(y_arr[finite_mask])),
                        neginf=float(np.nanmin(y_arr[finite_mask])),
                    )
                else:
                    raise ValueError(f"Plot {idx + 1} y_expr '{y_expr}' produced invalid/non-finite values.")
            if np.ptp(y_arr) <= 1e-12:
                raise ValueError(f"Plot {idx + 1} y_expr '{y_expr}' is flat/constant over [{x_min}, {x_max}].")

            extra_series = []
            for s in (p.get("extra_curves") or []):
                if not isinstance(s, dict):
                    continue
                s_expr = s.get("expr") or s.get("expression") or s.get("y_expr")
                if not s_expr:
                    continue
                try:
                    sy_raw = _safe_eval_expr(s_expr, local_env)
                    if np.ndim(sy_raw) == 0:
                        sy_arr = np.full(n_points, float(sy_raw))
                    else:
                        sy_arr = np.asarray(sy_raw, dtype=float)
                    if sy_arr.shape == x_arr.shape:
                        if not np.all(np.isfinite(sy_arr)):
                            s_finite = np.isfinite(sy_arr)
                            if np.count_nonzero(s_finite) >= n_points // 2:
                                sy_arr = np.nan_to_num(
                                    sy_arr,
                                    nan=float(np.nanmedian(sy_arr[s_finite])),
                                    posinf=float(np.nanmax(sy_arr[s_finite])),
                                    neginf=float(np.nanmin(sy_arr[s_finite])),
                                )
                        if np.all(np.isfinite(sy_arr)):
                            extra_series.append({
                                "y": sy_arr.tolist(),
                                "name": str(s.get("name", "Comparison")),
                                "color": s.get("color", "#10b981"),
                            })
                except Exception:
                    continue

            evaluated_plots.append({
                "plot_type": "scatter" if ptype == "scatter" else "line",
                "title": title,
                "x_label": x_label,
                "y_label": y_label,
                "x": x_arr.tolist(),
                "y": y_arr.tolist(),
                "series_name": series_name,
                "extra_series": extra_series or None,
            })
        except Exception as plot_err:
            plot_errors.append(str(plot_err))

    if len(evaluated_plots) < min_plots:
        err_msg = "; ".join(plot_errors) if plot_errors else f"Evaluated only {len(evaluated_plots)} valid plot(s); need >= {min_plots}."
        raise ValueError(err_msg)

    # Populate clean numerical metrics from evaluated constants & primary curves
    num_res = model_spec.get("numerical_results") if isinstance(model_spec.get("numerical_results"), dict) else {}
    primary_metrics = {}
    for idx, pl in enumerate(evaluated_plots):
        ys = [float(v) for v in pl["y"]]
        primary_metrics[f"plot_{idx + 1}_min"] = round(min(ys), 6)
        primary_metrics[f"plot_{idx + 1}_max"] = round(max(ys), 6)
        primary_metrics[f"plot_{idx + 1}_span"] = round(max(ys) - min(ys), 6)
    num_res.setdefault("primary_metrics", primary_metrics)
    num_res.setdefault("operating_parameters", {k: v for k, v in env.items() if isinstance(v, float) and k not in ("pi", "e", "N_A", "k_B")})

    observations = [str(o) for o in (model_spec.get("observations") or []) if str(o).strip()]
    if not observations:
        p0 = evaluated_plots[0]
        observations = [
            f"Evaluated {len(evaluated_plots)} governing scientific 2D curves (120 points each) for '{topic}'.",
            f"Primary response '{p0['y_label']}' spans [{min(p0['y']):.4g}, {max(p0['y']):.4g}] over '{p0['x_label']}'.",
        ]

    return {
        "numerical_results": num_res,
        "plots": evaluated_plots,
        "observations": observations,
        "_plot_errors": plot_errors,
        "_seed_log": seed_trace,
    }


class LLMEquationModelSynthesizer:
    """
    Prompts LM Studio (oreal-deepseek-r1-distill-qwen-7b) for a compact declarative
    JSON specification of governing physical/chemical equations and evaluates them cleanly
    across dense 120-point NumPy vectors without Python code syntax failure risks.
    """

    def __init__(self, model: Optional[str] = None):
        cfg = get_llm_config()
        self.model = model or cfg["lmstudio_model"]

    def synthesize(
        self,
        topic: str,
        hypothesis: str,
        parameters: dict,
        domain: str,
        refinement: Optional[dict] = None,
        previous_error: Optional[str] = None,
        temperature: float = 0.05,
    ) -> dict:
        ref = refinement or {}
        equations = ref.get("equations") or []
        ind_vars = ref.get("independent_vars") or []
        dep_vars = ref.get("dependent_vars") or []
        refined_obj = ref.get("refined_objective") or hypothesis
        seed_env = _build_seed_constants(parameters, domain)
        seed_names = sorted(seed_env.keys())
        unit_notes: List[str] = []
        if "Ea" in seed_env:
            unit_notes.append("Ea and Ea_J are ALREADY in J/mol")
        r_seed = seed_env.get("R")
        if isinstance(r_seed, float) and math.isclose(r_seed, 8.314, rel_tol=1e-9):
            unit_notes.append("R = 8.314 J/(mol*K) gas constant")
        if "g" in seed_env:
            unit_notes.append("g = 9.81 m/s^2")
        constants_note = "; ".join(unit_notes) or "values come from the experiment parameters above"

        repair_note = ""
        if previous_error:
            repair_note = f"\nFIX THIS PREVIOUS MODEL ERROR:\n{previous_error[:450]}\n"

        prompt = f"""Design a mathematically accurate 2D scientific visualization model as JSON for:
Topic: {topic}
Domain: {domain}
Objective: {refined_obj}
Hypothesis: {hypothesis}
Independent Variables: {json.dumps(ind_vars)}
Dependent Variables: {json.dumps(dep_vars)}
Governing Equations: {json.dumps(equations)}
Predefined Constants Available: {json.dumps(seed_names)} (note: {constants_note})
Parameters: {json.dumps(parameters)}
{repair_note}
Return ONLY valid JSON with:
1. "constants": derived scalar constants or formulas (e.g. {{"k": "A * exp(-Ea / (R * T))"}}). Do NOT multiply activation_energy_kJ*1000 if using Ea (Ea is already J/mol).
2. "plots": EXACTLY 3 distinct 2D plots representing real governing equations:
   - Plot 1: Primary independent variable vs dependent response (include 1-2 physical comparison curves in "extra_curves").
   - Plot 2: Secondary thermodynamic, time-transient, concentration-vs-time, or frequency response.
   - Plot 3: Parametric sensitivity curve across an important physical parameter (e.g., gauge factor sweep, temperature k(T) Arrhenius sweep, stress vs strain).
3. Schema for each plot:
   {{
     "plot_type": "line",
     "title": "Descriptive Scientific Title",
     "x_name": "var_name",
     "x_label": "Variable Name (Unit)",
     "x_min": 0.0,
     "x_max": 1.0,
     "y_label": "Measured Variable (Unit)",
     "series_name": "Primary Curve Label",
     "y_expr": "mathematical formula in x_name using np/math (NO random noise)",
     "extra_curves": [{{"name": "Comparison Label", "expr": "formula in x_name", "color": "#10b981"}}]
   }}
4. "observations": 3 concise scientific observations naming physical relationships and units.
CRITICAL:
- Output STRICT valid JSON only: NEVER include // comments, trailing commas, or extra double quotes inside strings (write `"y_expr": "V_ex * (GF * strain) / 4.0"`, NOT `""...""`). Numeric bounds "x_min"/"x_max" must be plain JSON numbers like 0.0 or 120.0.
- Define only constants you actually need in plots.
- Every "y_expr" MUST strictly depend on that plot's "x_name" using ASCII names (e.g. "strain", "t", "T", "gf") and vary smoothly (no flat constants, no random noise!).
- For exothermic reactions with pre-exponential A=1e9, Ea=65000 J/mol, verify k*t spans ~0.1..5 over [x_min, x_max] so exponential curves show clear smooth decay rather than instant 0!
EXAMPLE OUTPUT (for a simple spring-mass experiment):
{{"constants":{{"k":"spring_constant","omega":"np.sqrt(k/mass)"}},"plots":[{{"plot_type":"line","title":"Spring-Mass Displacement vs Time","x_name":"t","x_label":"Time (s)","x_min":0.0,"x_max":5.0,"y_label":"Displacement (m)","series_name":"x(t)","y_expr":"amplitude * np.cos(omega * t)","extra_curves":[{{"name":"Velocity","expr":"- amplitude * omega * np.sin(omega * t)","color":"#10b981"}}]}},{{"plot_type":"line","title":"Spring Potential Energy vs Displacement","x_name":"x","x_label":"Displacement (m)","x_min":-0.5,"x_max":0.5,"y_label":"Energy (J)","series_name":"PE","y_expr":"0.5 * k * x**2","extra_curves":[{{"name":"KE at x","expr":"0.5 * k * (amplitude**2 - x**2)","color":"#f59e0b"}}]}},{{"plot_type":"line","title":"Period vs Spring Constant","x_name":"k_sweep","x_label":"Spring Constant (N/m)","x_min":1.0,"x_max":50.0,"y_label":"Period (s)","series_name":"T(k)","y_expr":"2 * np.pi / np.sqrt(k_sweep / mass)","extra_curves":[]}}],"observations":["Displacement follows simple harmonic motion x=A*cos(ωt) with ω=√(k/m)","Total mechanical energy E=½kA² is conserved; PE and KE exchange sinusoidally","Period T=2π√(m/k) decreases with increasing spring constant"]}}
"""
        prefill_json = '{\n  "constants": {'
        raw = chat_completion(
            messages=[
                {
                    "role": "system",
                    "content": "You are a senior computational physicist and chemist. Output strictly valid JSON modeling exact scientific equations without prose.",
                },
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": f"<think>\n</think>\n{prefill_json}"},
            ],
            temperature=temperature,
            max_tokens=1150,
            timeout=90,
        )
        return _extract_json_model(raw, prefix=prefill_json)


# ─── Scientific validation gate & evidence-based confidence ─────────────

#: Matches a parenthesised unit indicator, e.g. "(m)", "(s)", "(K)", "(mol/L)".
_UNIT_INDICATOR_RE = re.compile(r"\([^()]*[A-Za-z][^()]*\)")

#: Minimum plots a synthesis attempt is asked to produce (used for confidence).
_REQUESTED_PLOTS = 3

#: Minimum data points expected per validated plot.
_MIN_PLOT_POINTS = 20


def _numeric_series(values: Any) -> Optional[List[float]]:
    """Return a float list for a numeric series, or None when the series is non-numeric."""
    if not isinstance(values, (list, tuple, np.ndarray)):
        return None
    try:
        return [float(v) for v in values]
    except (TypeError, ValueError):
        return None


def _label_mentions(text: Any, needles: Tuple[str, ...]) -> bool:
    """Case-insensitive substring test against a plot label."""
    low = str(text or "").lower()
    return any(needle in low for needle in needles)


def validate_scientific_output(
    result_dict: dict,
    domain: str,
    procedure_params: Optional[dict] = None,
) -> dict:
    """
    Rule-based scientific plausibility gate for synthesized simulation output.

    Universal checks (all domains, per plot):
      - x values monotonically non-decreasing (line/scatter plots)
      - every y value finite (no NaN / inf)
      - x and y arrays of equal length
      - axis labels carry unit indicators, e.g. "Time (s)"
      - at least 20 data points per plot

    Domain checks:
      - physics / mechanical / civil / electronics: no negative mass, temperature,
        energy or resistance; Kelvin temperatures strictly positive
      - chemistry / chem: non-negative concentrations and reaction rates
      - computer / cs: complexity-style curves non-decreasing over positive x

    Never raises: problems are reported as warnings so the caller can lower the
    confidence score rather than block the pipeline.
    """
    warnings: List[str] = []
    checks_passed = 0
    checks_total = 0
    domain_text = str(domain or "").lower()
    params = procedure_params if isinstance(procedure_params, dict) else {}

    def record(ok: bool, message: str) -> None:
        nonlocal checks_passed, checks_total
        checks_total += 1
        if ok:
            checks_passed += 1
        elif message:
            warnings.append(message)

    plots = result_dict.get("plots") or result_dict.get("plot_data") or []
    if not isinstance(plots, list) or not plots:
        return {
            "valid": False,
            "warnings": ["No plot data available for scientific validation."],
            "checks_passed": 0,
            "checks_total": 1,
        }

    is_physics = any(k in domain_text for k in ("physics", "mechanical", "civil", "electronics", "electrical"))
    is_chemistry = any(k in domain_text for k in ("chemistry", "chem"))
    is_cs = any(k in domain_text for k in ("computer", "cs", "algorithm", "machine_learning", "software"))

    # Declared-parameter sanity: only quantities with hard physical bounds are checked.
    for name, value in params.items():
        fval = _coerce_numeric(value)
        if fval is None:
            continue
        key = str(name).strip().lower()
        if key.startswith("temperature") and any(unit in key for unit in ("_k", "kelvin")):
            record(fval > 0.0, f"Procedure parameter {name}={fval} is not a physically valid temperature (must exceed 0 K).")
        elif key.startswith(("mass", "resistance")) and any(unit in key for unit in ("_kg", "ohm")):
            record(fval >= 0.0, f"Procedure parameter {name}={fval} is negative (physically invalid).")

    for idx, plot in enumerate(plots):
        if not isinstance(plot, dict):
            continue
        label = f"Plot {idx + 1} ('{plot.get('title', 'untitled')}')"
        x_raw = plot.get("x") or []
        y_raw = plot.get("y") or []
        x_vals = _numeric_series(x_raw)
        y_vals = _numeric_series(y_raw)
        is_bar = str(plot.get("plot_type", "line")).lower() == "bar"

        if y_vals is None:
            record(False, f"{label}: y-axis holds non-numeric values; numerical checks skipped.")
            continue

        # 1. x/y alignment
        record(len(x_raw) == len(y_raw), f"{label}: x/y length mismatch ({len(x_raw)} vs {len(y_raw)}).")

        # 2. Finite y values
        finite_ok = all(math.isfinite(v) for v in y_vals)
        record(finite_ok, f"{label}: y-axis contains non-finite values (NaN/inf).")

        # 3. Monotonically non-decreasing x for continuous plots
        if x_vals is not None and not is_bar:
            monotonic = all(x_vals[i] <= x_vals[i + 1] for i in range(len(x_vals) - 1))
            record(monotonic, f"{label}: x-axis is not monotonically non-decreasing.")
        else:
            record(True, "")

        # 4. Unit indicators on the axis labels
        y_has_unit = bool(_UNIT_INDICATOR_RE.search(str(plot.get("y_label", ""))))
        x_has_unit = bool(_UNIT_INDICATOR_RE.search(str(plot.get("x_label", ""))))
        unit_ok = y_has_unit and (x_has_unit or is_bar)
        record(unit_ok, f"{label}: axis labels missing unit indicators (expected e.g. '(m)', '(s)', '(K)').")

        # 5. Data density
        record(len(y_vals) >= _MIN_PLOT_POINTS, f"{label}: only {len(y_vals)} data points (>= {_MIN_PLOT_POINTS} required).")

        finite_y = [v for v in y_vals if math.isfinite(v)]
        if not finite_y:
            continue
        y_label = plot.get("y_label", "")
        title = plot.get("title", "")

        # 6. Physics / engineering: positivity of intrinsically positive quantities
        if is_physics:
            if _label_mentions(y_label, ("mass", "temperature", "energy", "resistance", "ohm", "pressure")):
                record(
                    min(finite_y) >= 0.0,
                    f"{label}: negative values in positive-only quantity '{y_label}'.",
                )
            kelvin_label = _label_mentions(y_label, ("kelvin", "(k)")) or bool(
                re.search(r"(?<![a-z])k(?![a-z])", str(y_label).lower())
            )
            if kelvin_label:
                record(min(finite_y) > 0.0, f"{label}: non-positive temperature in '{y_label}' (Kelvin must exceed 0).")

        # 7. Chemistry: concentrations and rates are non-negative
        if is_chemistry:
            if _label_mentions(y_label, ("concentration", "mol", "(m)", "molar")):
                record(
                    min(finite_y) >= 0.0,
                    f"{label}: negative concentration in '{y_label}'.",
                )
            if _label_mentions(y_label, ("rate", "velocity", "flux")):
                record(min(finite_y) >= 0.0, f"{label}: negative reaction rate in '{y_label}'.")

        # 8. CS: complexity-style curves must not decrease for positive x
        if is_cs and x_vals is not None and not is_bar:
            if _label_mentions(f"{title} {y_label}", ("complexity", "operations", "runtime", "order")):
                pairs = [(x, y) for x, y in zip(x_vals, y_vals) if math.isfinite(y) and x > 0]
                if pairs:
                    non_decreasing = all(
                        pairs[i][1] <= pairs[i + 1][1] + 1e-12 for i in range(len(pairs) - 1)
                    )
                    record(non_decreasing, f"{label}: complexity curve decreases over positive x.")

    logger.info(
        "scientific validation for domain '%s': %d/%d checks passed, %d warning(s)",
        domain or "general",
        checks_passed,
        checks_total,
        len(warnings),
    )

    return {
        "valid": not warnings,
        "warnings": warnings,
        "checks_passed": checks_passed,
        "checks_total": checks_total,
    }


def compute_confidence(
    plots_requested: int,
    plots_succeeded: int,
    validation_result: Optional[dict],
    generation_method: str,
    used_fallback: bool,
) -> float:
    """
    Evidence-based confidence score in [0.1, 0.98].

    Replaces fixed per-branch constants (0.92 / 0.89 / 0.85) with a score derived
    from how much of the requested output was produced, how many independent
    scientific checks passed, and which generation method produced the numbers.
    """
    base = 0.5

    # Plot completeness: up to +0.25
    plot_ratio = plots_succeeded / max(plots_requested, 1)
    base += 0.25 * plot_ratio

    # Validation: up to +0.15
    if validation_result and validation_result.get("checks_total", 0) > 0:
        check_ratio = validation_result["checks_passed"] / validation_result["checks_total"]
        base += 0.15 * check_ratio

    # Method bonus: verified deterministic engine +0.10, LLM equation model +0.05,
    # LLM Python code backup +0.0
    method = str(generation_method or "").lower()
    if method == "deterministic_engine":
        base += 0.10
    elif method == "equation_model":
        base += 0.05

    # Degraded/fallback path penalty
    if used_fallback:
        base -= 0.15

    return round(min(max(base, 0.1), 0.98), 2)


def _validation_log_lines(validation: dict, limit: int = 6) -> List[str]:
    """Render a validation report as audit-log lines (warnings capped for readability)."""
    status = "valid" if validation.get("valid") else "review advised"
    lines = [
        "[L3_validation] Scientific checks passed "
        f"{validation.get('checks_passed', 0)}/{validation.get('checks_total', 0)} ({status})"
    ]
    for warning in (validation.get("warnings") or [])[:limit]:
        lines.append(f"[L3_validation] WARNING: {warning}")
    extra = len(validation.get("warnings") or []) - limit
    if extra > 0:
        lines.append(f"[L3_validation] ... {extra} further warning(s) suppressed")
    return lines


def run_dynamic_simulation(procedure: dict) -> dict:
    """
    Orchestrates structured equation synthesis + vectorized NumPy evaluation (primary),
    with automatic self-repair retry and sandboxed Python synthesis backup for novel experiments.
    """
    topic = procedure.get("topic") or procedure.get("hypothesis", "Custom Experiment")
    hypothesis = procedure.get("hypothesis", "")
    parameters = procedure.get("parameters", {})
    domain = procedure.get("domain", "general")
    steps = procedure.get("steps", [])
    refinement = procedure.get("refinement")

    synthesizer = LLMEquationModelSynthesizer()
    simulation_log = [f"[L3_dynamic] Synthesizing equation-driven 2D model via {synthesizer.model} for '{topic[:80]}'"]
    last_error = None
    best_partial = None

    for attempt in range(1, 3):
        try:
            model_spec = synthesizer.synthesize(
                topic=topic,
                hypothesis=hypothesis,
                parameters=parameters,
                domain=domain,
                refinement=refinement,
                previous_error=last_error,
                temperature=0.05 if attempt == 1 else 0.15,
            )
            evaluated = evaluate_equation_model(
                model_spec=model_spec,
                topic=topic,
                parameters=parameters,
                domain=domain,
                n_points=120,
                min_plots=1,
            )
            for seed_note in (evaluated.get("_seed_log") or [])[:12]:
                simulation_log.append(f"[L3_dynamic] Parameter seeding: {seed_note}")
            numerical_results, plot_data, observations = _normalize_and_validate_plots(
                evaluated,
                topic,
                min_plots=1,
                min_curve_points=20,
            )
            partial_errs = evaluated.get("_plot_errors") or []
            if len(plot_data) >= 3:
                simulation_log.append(
                    f"[L3_dynamic] Equation attempt {attempt}: evaluated {len(plot_data)} dense 2D plots (120 pts/curve)"
                )
                validation = validate_scientific_output(
                    {"plots": plot_data, "numerical_results": numerical_results},
                    domain,
                    parameters,
                )
                simulation_log.extend(_validation_log_lines(validation))
                confidence = compute_confidence(
                    plots_requested=_REQUESTED_PLOTS,
                    plots_succeeded=len(plot_data),
                    validation_result=validation,
                    generation_method="equation_model",
                    used_fallback=False,
                )
                return {
                    "status": "success",
                    "engine_used": "dynamic_llm_code",
                    "generation_method": "equation_model",
                    "domain": domain,
                    "hypothesis": hypothesis,
                    "numerical_results": numerical_results,
                    "plot_data": plot_data,
                    "observations": observations,
                    "confidence_score": confidence,
                    "validation": validation,
                    "simulation_log": simulation_log,
                    "visualization_type": "graph",
                }

            if best_partial is None or len(plot_data) > len(best_partial[1]):
                best_partial = (numerical_results, plot_data, observations)

            if attempt == 1:
                last_error = "; ".join(partial_errs) or f"Only {len(plot_data)} valid plot(s) evaluated; generate all 3 distinct varying plots."
                simulation_log.append(
                    f"[L3_dynamic] Equation attempt 1 produced {len(plot_data)} valid plot(s); retrying for 3 ({last_error[:140]})"
                )
                continue
        except Exception as e:
            last_error = str(e)
            simulation_log.append(f"[L3_dynamic] Equation attempt {attempt} failed: {last_error[:220]}")

    if best_partial is not None:
        num_res, p_data, obs = best_partial
        simulation_log.append(
            f"[L3_dynamic] Using validated equation model with {len(p_data)} dense 120-pt primary plot(s)"
        )
        validation = validate_scientific_output({"plots": p_data, "numerical_results": num_res}, domain, parameters)
        simulation_log.extend(_validation_log_lines(validation))
        confidence = compute_confidence(
            plots_requested=_REQUESTED_PLOTS,
            plots_succeeded=len(p_data),
            validation_result=validation,
            generation_method="equation_model",
            used_fallback=False if len(p_data) >= 2 else True,
        )
        return {
            "status": "success",
            "engine_used": "dynamic_llm_code",
            "generation_method": "equation_model",
            "domain": domain,
            "hypothesis": hypothesis,
            "numerical_results": num_res,
            "plot_data": p_data,
            "observations": obs,
            "confidence_score": confidence,
            "validation": validation,
            "simulation_log": simulation_log,
            "visualization_type": "graph",
        }

    # Secondary backup: full NumPy/SciPy sandboxed Python code generation
    generator = LLMSimulationGenerator()
    runner = SandboxExecutionRunner()
    try:
        code = generator.generate_code(
            topic=topic,
            hypothesis=hypothesis,
            parameters=parameters,
            domain=domain,
            refinement=refinement,
            steps=steps,
            previous_error=last_error,
            temperature=0.1,
        )
        simulation_log.append(f"[L3_dynamic] Code backup: synthesized {len(code)} chars of Python code")
        results = runner.run(code)
        numerical_results, plot_data, observations = _normalize_and_validate_plots(
            results,
            topic,
            min_plots=1,
            min_curve_points=10,
        )
        simulation_log.append(
            f"[L3_dynamic] Code backup: validated {len(plot_data)} 2D plots and {len(numerical_results)} metric groups"
        )
        validation = validate_scientific_output(
            {"plots": plot_data, "numerical_results": numerical_results},
            domain,
            parameters,
        )
        simulation_log.extend(_validation_log_lines(validation))
        confidence = compute_confidence(
            plots_requested=_REQUESTED_PLOTS,
            plots_succeeded=len(plot_data),
            validation_result=validation,
            generation_method="python_backup",
            used_fallback=True,
        )
        return {
            "status": "success",
            "engine_used": "dynamic_llm_code",
            "generation_method": "python_backup",
            "domain": domain,
            "hypothesis": hypothesis,
            "numerical_results": numerical_results,
            "plot_data": plot_data,
            "observations": observations,
            "confidence_score": confidence,
            "validation": validation,
            "simulation_log": simulation_log,
            "visualization_type": "graph",
        }
    except Exception as e:
        last_error = str(e)
        simulation_log.append(f"[L3_dynamic] Code backup failed: {last_error[:220]}")

    return {
        "status": "failed",
        "engine_used": "dynamic_llm_code",
        "generation_method": "failed",
        "domain": domain,
        "hypothesis": hypothesis,
        "numerical_results": {},
        "plot_data": [],
        "observations": [f"Dynamic simulation execution failed after retry: {last_error}"],
        "confidence_score": 0.0,
        "validation": {
            "valid": False,
            "warnings": ["Simulation failed before producing any scientific plot."],
            "checks_passed": 0,
            "checks_total": 0,
        },
        "simulation_log": simulation_log,
        "visualization_type": "graph",
    }
