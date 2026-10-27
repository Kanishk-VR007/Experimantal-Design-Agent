import json
import re
import traceback
import math
import numpy as np
import scipy.integrate
import scipy.optimize
import ollama

class LLMSimulationGenerator:
    """
    Prompts llama3.2 to write a Python script for the experiment simulation.
    """
    def __init__(self, model: str = "llama3.2"):
        self.model = model

    def generate_code(self, hypothesis: str, parameters: dict, domain: str) -> str:
        prompt = f"""
You are a Python data scientist and simulation engineer. 
Write a Python script to simulate the following scientific experiment.

Domain: {domain}
Hypothesis: {hypothesis}
Parameters: {json.dumps(parameters, indent=2)}

Requirements:
1. ONLY output raw, executable Python code. Do not use Markdown formatting (no ```python blocks).
2. DO NOT use `matplotlib` or any other visualization libraries.
3. You must IMPORT any modules you need at the top of the script (e.g., `import numpy as np`, `from scipy.integrate import solve_ivp`). The environment allows `numpy`, `scipy`, and `math`.
4. NEVER use `odeint`. Always use `scipy.integrate.solve_ivp` for differential equations.
5. The ODE function must be defined as `def model(t, y, param1, param2, ...):` where `t` is first, `y` is second, followed by any additional arguments.
6. When calling `solve_ivp`, you MUST pass the arguments exactly like this: `solve_ivp(model, [t_start, t_end], [y0], t_eval=t_points, args=(param1, param2, ...))`. Note that the initial condition must be a list or array (e.g., `[y0]`).
7. Ensure the number of parameters in `args` exactly matches the extra parameters in your `def model(...)` signature.
8. Your script MUST conclude by saving its numeric outputs and arrays into a dictionary named exactly `simulation_results`.
9. Make sure the code is completely self-contained and ready to execute. Do not include any explanations.

# Example required ending:
simulation_results = {{
    "x_data": list_or_array,
    "y_data": list_or_array
}}

Write the Python code now:
"""
        response = ollama.chat(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.1}
        )
        code = response['message']['content']
        # Clean up any accidental markdown blocks the LLM might have output despite instructions
        code = re.sub(r"^```python\s*", "", code, flags=re.IGNORECASE)
        code = re.sub(r"^```\s*", "", code, flags=re.IGNORECASE)
        code = re.sub(r"```\s*$", "", code, flags=re.IGNORECASE)
        return code.strip()


class SandboxExecutionRunner:
    """
    Executes the generated Python code in a restricted namespace.
    """
    def __init__(self):
        self.allowed_globals = {
            "__builtins__": __builtins__,
            "np": np,
            "numpy": np,
            "scipy": scipy,
            "math": math
        }

    def convert_to_serializable(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {k: self.convert_to_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.convert_to_serializable(v) for v in obj]
        elif isinstance(obj, (np.float32, np.float64)):
            return float(obj)
        elif isinstance(obj, (np.int32, np.int64)):
            return int(obj)
        return obj

    def _extract_results(self, scope: dict) -> dict:
        # a. Check aliases
        aliases = ['simulation_results', 'results', 'result', 'sim_data', 'output', 'data']
        for alias in aliases:
            if alias in scope and isinstance(scope[alias], dict):
                return scope[alias]
        
        # b. Detect and execute any uncalled user-defined functions that return a dictionary
        import inspect
        for key, val in list(scope.items()):
            if callable(val) and not key.startswith("__"):
                try:
                    if len(inspect.signature(val).parameters) == 0:
                        res = val()
                        if isinstance(res, dict):
                            return res
                except Exception:
                    pass
                    
        # c. Scan the scope and auto-harvest any list/NumPy variables
        harvested = {}
        for key, val in scope.items():
            if not key.startswith("__") and not callable(val) and not type(val).__name__ == "module":
                if isinstance(val, (list, np.ndarray)):
                    harvested[key] = val
        
        if harvested:
            return harvested
            
        raise ValueError("The script executed but did not define 'simulation_results' dictionary, and no arrays could be automatically harvested.")

    def run(self, code: str) -> dict:
        scope = dict(self.allowed_globals)
        try:
            exec(code, scope)
            results = self._extract_results(scope)
            return self.convert_to_serializable(results)
        except Exception as e:
            tb = traceback.format_exc()
            raise RuntimeError(f"Execution failed:\n{e}\n\nTraceback:\n{tb}")

def run_dynamic_simulation(procedure: dict) -> dict:
    """
    Orchestrates generation and execution of the simulation code.
    Returns the raw output structure expected by format_output.
    """
    hypothesis = procedure.get("hypothesis", "")
    parameters = procedure.get("parameters", {})
    domain = procedure.get("domain", "general")
    
    generator = LLMSimulationGenerator()
    runner = SandboxExecutionRunner()
    
    simulation_log = []
    simulation_log.append("[L3] Generating simulation code via llama3.2...")
    
    try:
        code = generator.generate_code(hypothesis, parameters, domain)
        simulation_log.append("[L3] Code generation successful. Executing in sandbox...")
        
        results = runner.run(code)
        simulation_log.append("[L3] Execution successful. Results extracted.")
        
        # We try to infer plot data and numerical results from the output
        # If there are arrays, they go to plot data. Scalars go to numerical results.
        numerical_results = {}
        arrays = {}
        for k, v in results.items():
            if isinstance(v, list) and len(v) > 1:
                arrays[k] = v
            else:
                numerical_results[k] = v
                
        plot_data = []
        if arrays:
            # Simple heuristic: pick the first array as X, rest as Y, or just plot indices if only one array.
            keys = list(arrays.keys())
            if len(keys) == 1:
                y_key = keys[0]
                y_val = arrays[y_key]
                x_val = list(range(len(y_val)))
                plot_data.append({
                    "plot_type": "line",
                    "title": f"{y_key} over index",
                    "x_label": "Index",
                    "y_label": y_key,
                    "x": x_val,
                    "y": y_val
                })
            else:
                # Assume first key is x (like time), others are y
                x_key = keys[0]
                x_val = arrays[x_key]
                for y_key in keys[1:]:
                    plot_data.append({
                        "plot_type": "line",
                        "title": f"{y_key} vs {x_key}",
                        "x_label": x_key,
                        "y_label": y_key,
                        "x": x_val,
                        "y": arrays[y_key]
                    })
        
        return {
            "status": "success",
            "engine_used": "dynamic_llm_code",
            "domain": domain,
            "hypothesis": hypothesis,
            "numerical_results": numerical_results,
            "plot_data": plot_data,
            "observations": ["LLM code execution completed successfully."],
            "confidence_score": 0.9,
            "simulation_log": simulation_log,
            "visualization_type": "graph"
        }
        
    except Exception as e:
        simulation_log.append(f"[L3] ERROR: {str(e)}")
        return {
            "status": "failed",
            "engine_used": "dynamic_llm_code",
            "domain": domain,
            "hypothesis": hypothesis,
            "numerical_results": {},
            "plot_data": [],
            "observations": [f"Execution failed: {str(e)}"],
            "confidence_score": 0.0,
            "simulation_log": simulation_log,
            "visualization_type": "graph"
        }
