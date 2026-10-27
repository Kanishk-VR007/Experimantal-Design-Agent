"""
LLM Fallback Engine
General/multi-domain fallback using Claude API or Ollama
Handles cases where deterministic engines don't apply
"""

import json
import re
import os
import requests
from dotenv import load_dotenv

load_dotenv()


def run_with_claude(procedure: dict, error_context: str = "") -> dict:
    """Fallback using Claude API (requires ANTHROPIC_API_KEY)"""
    try:
        import anthropic
        client = anthropic.Anthropic()
        
        SYSTEM = """You are a scientific simulation engine embedded in a research AI pipeline.
Given an experimental procedure as JSON, simulate it scientifically and return ONLY a
valid JSON object — no markdown, no preamble — with this exact structure:
{
  "numerical_results": { ... },
  "plot_data": [
    {
      "plot_type": "line",
      "title": "...",
      "x_label": "...",
      "y_label": "...",
      "x": [...],
      "y": [...],
      "series_name": "..."
    }
  ],
  "observations": ["...", "..."],
  "confidence_score": 0.0_to_1.0,
  "simulation_log": ["step 1...", "step 2..."]
}
Ensure the output represents a valid static 2D simulation. Generate realistic, scientifically plausible values. x and y arrays must be 1D arrays with 50-200 points. No 3D data or animations."""

        note = f"\nNote: Primary engine failed: {error_context}" if error_context else ""
        prompt = f"Simulate this experiment:{note}\n\n{json.dumps(procedure, indent=2)}"

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            temperature=0.3,
            top_p=0.9,
            system=SYSTEM,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = response.content[0].text
        clean = re.sub(r"```json|```", "", raw).strip()
        return json.loads(clean)
    except Exception as e:
        print(f"⚠️  Claude API fallback failed: {e}")
        return run_with_ollama(procedure, error_context)


def run_with_ollama(procedure: dict, error_context: str = "") -> dict:
    """Fallback using local Ollama instance"""
    try:
        OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
        OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
        
        prompt = f"""You are a scientific simulation engine. Generate a simulation for this experiment.

Experiment Procedure:
{json.dumps(procedure, indent=2)}

Return ONLY valid JSON (no markdown) with this structure:
{{
  "numerical_results": {{}},
  "plot_data": [
    {{
      "plot_type": "line",
      "title": "Simulation Result",
      "x_label": "X Axis",
      "y_label": "Y Axis",
      "x": [0, 1, 2, 3, 4, 5],
      "y": [0, 1.5, 2.3, 3.1, 3.5, 4.0],
      "series_name": "Data"
    }}
  ],
  "observations": ["observation 1", "observation 2"],
  "confidence_score": 0.7,
  "simulation_log": ["step 1", "step 2"]
}}

Ensure the output represents a valid static 2D simulation. Generate realistic scientific data with 50-200 data points in 1D arrays for x and y. Do not include any 3D properties or animated data."""

        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "temperature": 0.3,
                "top_p": 0.9,
                "num_predict": 4096,
                "stream": False
            },
            timeout=180
        )
        
        if response.status_code == 200:
            data = response.json()
            raw_text = data.get("response", "")
            
            # Clean markdown
            clean = re.sub(r"```json|```", "", raw_text).strip()
            
            # Try to parse JSON
            try:
                return json.loads(clean)
            except json.JSONDecodeError:
                # Extract JSON from mixed content
                json_match = re.search(r'\{.*\}', clean, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group(0))
        
        raise Exception(f"Ollama returned status {response.status_code}")
        
    except Exception as e:
        print(f"⚠️  Ollama fallback failed: {e}")
        return get_minimal_fallback(procedure)


def get_minimal_fallback(procedure: dict) -> dict:
    """Minimal hardcoded fallback when all LLMs fail"""
    import numpy as np
    
    x = np.linspace(0, 10, 100).tolist()
    y = (np.sin(x) + np.random.normal(0, 0.1, 100)).tolist()
    
    return {
        "numerical_results": {
            "status": "fallback_used",
            "mean_value": np.mean(y),
            "std_dev": np.std(y),
        },
        "plot_data": [{
            "plot_type": "line",
            "title": f"Simulation: {procedure.get('hypothesis', 'Unknown')}",
            "x_label": "Time/Trial",
            "y_label": "Measured Value",
            "x": x,
            "y": y,
            "series_name": "Data Series"
        }],
        "observations": [
            "Fallback simulation used due to engine unavailability",
            f"Generated synthetic data for domain: {procedure.get('domain', 'general')}"
        ],
        "confidence_score": 0.5,
        "simulation_log": ["[fallback] Minimal simulation generated"]
    }


def run(procedure: dict, error_context: str = "") -> dict:
    """
    Main entry point for LLM fallback.
    Tries Claude → Ollama → Minimal fallback
    """
    # Try Claude first if API key available
    if os.getenv("ANTHROPIC_API_KEY"):
        try:
            return run_with_claude(procedure, error_context)
        except:
            pass
    
    # Try Ollama
    try:
        return run_with_ollama(procedure, error_context)
    except:
        pass
    
    # Last resort
    return get_minimal_fallback(procedure)
