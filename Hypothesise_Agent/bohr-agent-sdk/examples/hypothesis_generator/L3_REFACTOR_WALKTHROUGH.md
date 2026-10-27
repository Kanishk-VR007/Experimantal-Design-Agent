# Walkthrough: Dynamic LLM Simulation Refactor

I have successfully refactored the L3 Simulation Agent to use dynamic LLM code generation and a sandboxed execution runner!

## 1. Updated Dependencies
- Added `ollama>=0.1.7` to `backend/requirements.txt` and installed it in your local environment.

## 2. Dynamic Simulation Engine (`dynamic_sim.py`)
- Created `LLMSimulationGenerator` which prompts `llama3.2` to write a self-contained Python script to simulate the experiment based on the generated hypothesis and experimental parameters. It strictly avoids Markdown block formatting and visualization libraries (e.g., matplotlib).
- Built `SandboxExecutionRunner` that receives the generated script and executes it in a single `scope` dictionary using `exec()`.
- Whitelisted modules (`numpy`, `scipy`, `math`) are made available in the execution scope.
- Automatically handles serialization: Any `numpy` arrays, floats, or integers output by the script are safely converted to built-in Python types so they can be JSON-serialized and sent to the frontend.
- Added heuristics to automatically transform array outputs into `plot_data` and scalar values into `numerical_results` for the frontend.

## 3. Integration with L3 Pipeline (`agent.py`)
- Refactored `run_simulation` in `simulation_agent/agent.py` to bypass the old keyword-routing map (`router.route()`).
- The pipeline now natively invokes `run_dynamic_simulation`.
- Robust error handling: if the LLM's code fails to execute, a structured payload is returned with `confidence_score: 0.0` and the traceback is logged in the `simulation_log`.

## Verification
- Verified by running `test_dynamic_sim.py` in the background. The LLM successfully generated an Arrhenius equation chemistry simulation using `scipy.integrate.odeint`, executed it, and produced the expected `plot_data` and `numerical_results` payload.

> [!TIP]
> You can now test this directly from the React UI! Run your project (e.g., `python launch.py`) and enter a completely custom experiment scenario; `llama3.2` will write and execute the simulation code on the fly.
