#!/usr/bin/env python3
"""
Experimental Design Agent
=========================
An intelligent agent that designs complete scientific experiments by:
  1. Fetching relevant research papers from Bohrium Science Navigator
  2. Analyzing existing methodologies and gaps
  3. Generating structured experimental designs using Ollama LLM
  4. Providing testable hypotheses with clear variables and procedures

This agent acts as a scientific advisor that helps researchers:
- Identify research gaps based on existing literature
- Design rigorous experiments with proper controls
- Define independent/dependent variables clearly
- Outline step-by-step experimental procedures
- Predict expected outcomes and potential limitations

Usage:
    python experimental_design_agent.py
    
    Or import as module:
    from experimental_design_agent import ExperimentalDesignAgent
    agent = ExperimentalDesignAgent()
    design = agent.design_experiment("Your research topic")

Requirements:
    pip install requests python-dotenv
    
    Ollama must be running locally:
    ollama serve
    ollama pull llama3

Environment Setup:
    Create a .env file with any custom configurations (optional)
    
Author: Hypothesis Agent Team
Date: February 2026
"""

import os
import json
import sys
import time
import requests
from datetime import datetime
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Configuration
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.3"))
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)


class ExperimentalDesignAgent:
    """
    An AI agent that designs scientific experiments by combining
    literature review from Bohrium and experimental design via Ollama.
    """
    
    def __init__(self, ollama_url: str = OLLAMA_URL, model: str = OLLAMA_MODEL):
        self.ollama_url = ollama_url
        self.model = model
        self.papers_cache = []
        
    # ═══════════════════════════════════════════════════════════════════════
    # 1️⃣ LITERATURE REVIEW: Fetch papers from Bohrium Science Navigator
    # ═══════════════════════════════════════════════════════════════════════
    
    def fetch_research_papers(self, query: str, max_results: int = 3) -> List[Dict]:
        """
        Fetch relevant research papers from Bohrium Science Navigator.
        
        This is a public API - no authentication required.
        Returns papers with title, abstract, authors, citations, etc.
        
        Args:
            query: Research topic or keywords
            max_results: Maximum number of papers to retrieve (default: 3)
            
        Returns:
            List of paper dictionaries with metadata
        """
        papers = []
        
        print(f"🔍 Searching Bohrium for: '{query}'...")
        
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (compatible; ExperimentalDesignAgent/1.0)",
                "Accept": "application/json, text/plain, */*",
                "Referer": "https://bohrium.com/",
            }
            
            # Bohrium public paper search API
            api_url = "https://bohrium.com/api/v1/paper/search"
            params = {
                "keyword": query,
                "page": 1,
                "page_size": max_results,
                "sort": "relevance",
            }
            
            response = requests.get(api_url, params=params, headers=headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                # Handle different response structures from Bohrium API
                items = (
                    data.get("data", {}).get("list", [])
                    or data.get("data", [])
                    or data.get("results", [])
                    or []
                )
                
                for item in items[:max_results]:
                    paper = {
                        "title": item.get("title_en") or item.get("title", ""),
                        "abstract": item.get("abstract_en") or item.get("abstract", ""),
                        "authors": [
                            a.get("name", str(a)) if isinstance(a, dict) else str(a)
                            for a in item.get("authors", [])
                        ],
                        "method": item.get("method") or item.get("methodology", ""),
                        "limitations": item.get("limitations", ""),
                        "url": item.get("url", ""),
                        "doi": item.get("doi", ""),
                        "citations": item.get("citation_count", 0),
                        "impact_factor": item.get("impact_factor", ""),
                        "published": item.get("publish_date", ""),
                    }
                    papers.append(paper)
                    
                print(f"✅ Found {len(papers)} papers from Bohrium")
                
            elif response.status_code == 404:
                print("⚠️  Bohrium API endpoint not found - may have changed")
            else:
                print(f"⚠️  Bohrium API returned status {response.status_code}")
                
        except requests.exceptions.Timeout:
            print("⚠️  Request timed out - Bohrium may be slow")
        except requests.exceptions.ConnectionError:
            print("⚠️  Cannot connect to Bohrium - check internet connection")
        except Exception as e:
            print(f"⚠️  Bohrium search error: {e}")
        
        self.papers_cache = papers
        return papers
    
    # ═══════════════════════════════════════════════════════════════════════
    # 2️⃣ EXPERIMENTAL DESIGN: Generate via Ollama LLM
    # ═══════════════════════════════════════════════════════════════════════
    
    def generate_experimental_design(self, experiment_data: List[Dict]) -> str:
        """
        Generate a complete experimental design using Ollama LLM.
        
        Takes research paper data and creates a structured experimental design
        including hypothesis, methodology, variables, and expected outcomes.
        
        Args:
            experiment_data: List of paper dictionaries from Bohrium
            
        Returns:
            Formatted experimental design as string
        """
        
        if not experiment_data:
            return "❌ No experiment data available. Cannot generate design."
        
        # Build comprehensive prompt for experimental design
        prompt = f"""You are an expert Experimental Design Agent and scientific advisor.

Your role is to analyze existing research and design NEW experiments that advance the field.

Based on the following research papers:

{json.dumps(experiment_data, indent=2)}

Generate a COMPLETE experimental design that includes ALL of the following sections:

## 1. RESEARCH GAP ANALYSIS
- What gaps exist in current research?
- What questions remain unanswered?
- Why is a new experiment needed?

## 2. RESEARCH HYPOTHESIS
- State a clear, testable hypothesis
- Explain the rationale based on existing literature
- Define expected relationships between variables

## 3. EXPERIMENTAL VARIABLES
- Independent Variable(s): What will be manipulated?
- Dependent Variable(s): What will be measured?
- Control Variables: What must remain constant?
- Confounding Variables: What might interfere?

## 4. EXPERIMENTAL DESIGN
- Design Type: (e.g., randomized controlled trial, factorial design, etc.)
- Sample Size: Recommended number of subjects/samples
- Control Group: Description of control conditions
- Experimental Group(s): Description of treatment conditions

## 5. METHODOLOGY & PROCEDURES
- Step-by-step experimental procedure
- Equipment and materials needed
- Data collection methods
- Timeline for the experiment

## 6. DATA ANALYSIS PLAN
- Statistical tests to be used
- Metrics and measurements
- How to interpret results

## 7. EXPECTED OUTCOMES
- Predicted results if hypothesis is correct
- Alternative results if hypothesis is wrong
- Practical implications of findings

## 8. LIMITATIONS & RISKS
- Potential experimental limitations
- Sources of error or bias
- Risk mitigation strategies

## 9. ETHICAL CONSIDERATIONS
- Any ethical concerns
- Required approvals or protocols

Be specific, rigorous, and scientific. Use technical terminology appropriately.
Format with clear markdown headings and bullet points.
"""

        print(f"\n🧠 Generating experimental design using {self.model}...")
        print("⏳ This may take 30-60 seconds...\n")
        
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "temperature": OLLAMA_TEMPERATURE,
                "top_p": 0.9,
                "num_predict": 4096,
                "repeat_penalty": 1.1,
                "stream": False
            }
            
            response = requests.post(
                self.ollama_url, 
                json=payload, 
                timeout=180  # 3 minute timeout for complex generation
            )
            
            response.raise_for_status()
            result = response.json()
            
            design_output = result.get("response", "")
            
            if design_output:
                print("✅ Experimental design generated successfully!\n")
                return design_output
            else:
                return "❌ Ollama returned empty response"
                
        except requests.exceptions.ConnectionError:
            error_msg = """
❌ Cannot connect to Ollama.

Please ensure Ollama is running:
  1. Open a terminal
  2. Run: ollama serve
  3. In another terminal: ollama pull llama3
  4. Try this script again

Visit: https://ollama.ai for installation instructions
"""
            return error_msg
            
        except requests.exceptions.Timeout:
            return "❌ Ollama request timed out - try a smaller model or increase timeout"
            
        except requests.exceptions.HTTPError as e:
            return f"❌ Ollama HTTP error: {e}"
            
        except Exception as e:
            return f"❌ Experimental design generation failed: {e}"
    
    # ═══════════════════════════════════════════════════════════════════════
    # 3️⃣ FULL PIPELINE: Complete experimental design workflow
    # ═══════════════════════════════════════════════════════════════════════
    
    def design_experiment(self, topic: str, max_papers: int = 3, save_output: bool = True) -> Dict:
        """
        Complete experimental design pipeline.
        
        Args:
            topic: Research topic or question
            max_papers: Number of papers to retrieve (default: 3)
            save_output: Whether to save results to file (default: True)
            
        Returns:
            Dictionary with papers, design, and metadata
        """
        
        print("=" * 70)
        print("🔬 EXPERIMENTAL DESIGN AGENT")
        print("=" * 70)
        print(f"📋 Topic: {topic}")
        print(f"📚 Papers to fetch: {max_papers}")
        print(f"🤖 LLM Model: {self.model}")
        print("=" * 70)
        print()
        
        # Step 1: Fetch research papers
        start_time = time.time()
        papers = self.fetch_research_papers(topic, max_papers)
        
        if not papers:
            print("\n⚠️  No papers found. Generating design without literature review...")
            papers = [{
                "title": f"Research on {topic}",
                "abstract": f"Exploring {topic} and its applications.",
                "authors": [],
                "method": "",
                "limitations": "Limited prior research available"
            }]
        
        # Step 2: Generate experimental design
        design = self.generate_experimental_design(papers)
        
        elapsed_time = time.time() - start_time
        
        # Step 3: Compile results
        results = {
            "topic": topic,
            "timestamp": datetime.now().isoformat(),
            "papers_found": len(papers),
            "papers": papers,
            "experimental_design": design,
            "processing_time_seconds": round(elapsed_time, 2),
            "model_used": self.model
        }
        
        # Step 4: Save to file if requested
        if save_output:
            self._save_results(topic, results, design)
        
        return results
    
    def _save_results(self, topic: str, results: Dict, design: str):
        """Save experimental design to JSON and readable text files"""
        
        # Create safe filename
        safe_topic = "".join(c if c.isalnum() else "_" for c in topic)[:50]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save JSON
        json_file = os.path.join(OUTPUT_DIR, f"experiment_design_{safe_topic}_{timestamp}.json")
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        # Save readable report
        txt_file = os.path.join(OUTPUT_DIR, f"experiment_design_{safe_topic}_{timestamp}.txt")
        with open(txt_file, "w", encoding="utf-8") as f:
            f.write("=" * 70 + "\n")
            f.write("EXPERIMENTAL DESIGN REPORT\n")
            f.write("=" * 70 + "\n\n")
            f.write(f"Topic: {topic}\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Papers Analyzed: {len(results['papers'])}\n")
            f.write(f"Model: {results['model_used']}\n")
            f.write("\n" + "=" * 70 + "\n\n")
            
            f.write("LITERATURE SOURCES:\n")
            f.write("-" * 70 + "\n")
            for i, paper in enumerate(results['papers'], 1):
                f.write(f"\n{i}. {paper['title']}\n")
                if paper.get('authors'):
                    f.write(f"   Authors: {', '.join(paper['authors'][:3])}\n")
                if paper.get('citations'):
                    f.write(f"   Citations: {paper['citations']}\n")
                if paper.get('url'):
                    f.write(f"   URL: {paper['url']}\n")
            
            f.write("\n" + "=" * 70 + "\n\n")
            f.write("EXPERIMENTAL DESIGN:\n")
            f.write("-" * 70 + "\n\n")
            f.write(design)
        
        print(f"\n💾 Results saved:")
        print(f"   📄 {json_file}")
        print(f"   📄 {txt_file}")


# ═══════════════════════════════════════════════════════════════════════════
# MAIN: Interactive mode
# ═══════════════════════════════════════════════════════════════════════════

def main():
    """Main function for standalone execution"""
    
    print("\n" + "=" * 70)
    print("🔬 EXPERIMENTAL DESIGN AGENT")
    print("=" * 70)
    print("\nThis agent will:")
    print("  1️⃣  Search Bohrium Science Navigator for relevant papers")
    print("  2️⃣  Analyze existing research and identify gaps")
    print("  3️⃣  Generate a complete experimental design with Ollama")
    print("  4️⃣  Save structured output to JSON and readable report")
    print("=" * 70 + "\n")
    
    # Get user input
    if len(sys.argv) > 1:
        topic = " ".join(sys.argv[1:])
    else:
        topic = input("🔍 Enter your research topic: ").strip()
    
    if not topic:
        print("❌ No topic provided. Exiting.")
        return
    
    # Initialize agent
    agent = ExperimentalDesignAgent()
    
    # Design experiment
    results = agent.design_experiment(topic, max_papers=3, save_output=True)
    
    # Display results
    print("\n" + "=" * 70)
    print("📊 EXPERIMENTAL DESIGN OUTPUT")
    print("=" * 70 + "\n")
    print(results["experimental_design"])
    print("\n" + "=" * 70)
    print(f"⏱️  Total processing time: {results['processing_time_seconds']} seconds")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
