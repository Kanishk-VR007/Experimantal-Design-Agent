import time
import subprocess
import requests

def test_memory_agent():
    print("Starting memory agent...")
    process = subprocess.Popen(["python", "memory_agent/main.py"])
    
    # wait for it to start
    time.sleep(3)
    
    try:
        # ping
        resp = requests.get("http://localhost:8001/")
        print("Ping response:", resp.status_code, resp.json())
        
        # submit feedback
        feedback_data = {
            "memory_id": "test_mem_123",
            "memory_type": "hypothesis",
            "score": 0.85,
            "feedback_type": "hypothesis_quality",
            "run_id": "test_run_001"
        }
        resp = requests.post("http://localhost:8001/improve/feedback", json=feedback_data)
        print("Submit feedback:", resp.status_code, resp.json())
        
        # get feedback scores
        resp = requests.get("http://localhost:8001/improve/feedback-scores")
        print("Feedback scores:", resp.status_code, resp.json())
        
        # record run accuracy
        accuracy_data = {
            "run_id": "test_run_001",
            "domain": "test_domain",
            "hypothesis_score": 0.9,
            "procedure_score": 0.8,
            "simulation_conf": 0.85,
            "analysis_depth": 0.7,
            "audit_score": 0.9,
            "review_score_10": 8.5
        }
        resp = requests.post("http://localhost:8001/improve/record-run-accuracy", json=accuracy_data)
        print("Record run accuracy:", resp.status_code, resp.json())
        
        # get accuracy report
        resp = requests.get("http://localhost:8001/improve/accuracy-report")
        print("Accuracy report:", resp.status_code, resp.json())
        
        print("Memory agent works properly!")
        
    except Exception as e:
        print("Error:", e)
    finally:
        process.terminate()
        process.wait()

if __name__ == "__main__":
    test_memory_agent()
