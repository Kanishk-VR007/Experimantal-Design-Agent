import sys
import os

# Add to path to import simulation_agent
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from simulation_agent.dynamic_sim import run_dynamic_simulation

def test_dynamic_sim():
    print("Testing dynamic LLM simulation generation and sandboxed execution...")
    
    mock_procedure = {
        "domain": "chemistry",
        "hypothesis": "If we increase the temperature from 300K to 400K, the reaction rate will exponentially increase following the Arrhenius equation.",
        "parameters": {
            "T_start": 300,
            "T_end": 400,
            "num_steps": 10
        }
    }
    
    try:
        print("Invoking run_dynamic_simulation (this will call Ollama)...")
        result = run_dynamic_simulation(mock_procedure)
        
        print(f"Status: {result.get('status')}")
        print(f"Confidence: {result.get('confidence_score')}")
        print("Numerical Results Keys:", list(result.get("numerical_results", {}).keys()))
        print("Plot Data Count:", len(result.get("plot_data", [])))
        if result.get("plot_data"):
            print("First Plot Type:", result["plot_data"][0].get("plot_type"))
        print("\nSimulation Log:")
        for log in result.get("simulation_log", []):
            print(log)
            
        if result.get("status") == "success":
            print("\nSUCCESS: Dynamic simulation ran correctly.")
        else:
            print("\nFAILURE: Dynamic simulation returned failure status.")
    except Exception as e:
        print(f"\nFATAL ERROR during test: {e}")

if __name__ == "__main__":
    test_dynamic_sim()
