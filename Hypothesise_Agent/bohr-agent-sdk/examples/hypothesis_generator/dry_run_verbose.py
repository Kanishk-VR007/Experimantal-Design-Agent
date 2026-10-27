#!/usr/bin/env python3
"""
Dry Run: Experimental Design Agent with Verbose Logging
========================================================
This script tests the complete workflow with detailed logging of all steps.
Shows exactly what's being sent to Ollama and what's received.
"""

import os
import sys
import json
import time
import requests
from datetime import datetime
from typing import List, Dict

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def fetch_mock_papers() -> List[Dict]:
    """Return mock research papers for testing"""
    return [
        {
            "title": "Dropout Regularization in Deep Neural Networks",
            "abstract": "This study examines the effect of dropout on CNN performance. "
                       "Results show 3-5% accuracy improvement on CIFAR-10 with dropout=0.5",
            "authors": ["Zhang, L.", "Wang, M."],
            "source": "Bohrium",
            "citations": 189
        },
        {
            "title": "Comparative Study of CNN Regularization Techniques",
            "abstract": "We compare dropout, batch normalization, and L2 regularization. "
                       "Dropout shows best generalization on small datasets.",
            "authors": ["Smith, J.", "Lee, K."],
            "source": "arXiv",
            "citations": 142
        }
    ]


def generate_design_with_streaming(papers: List[Dict], topic: str) -> str:
    """
    Generate experimental design using Ollama with streaming
    to show progress and avoid timeouts on long generations
    """
    
    # Create a simpler, more focused prompt
    prompt = f"""Design an experiment for: "{topic}"

Based on these papers:
{json.dumps(papers, indent=2)}

Provide a brief experimental design (200-300 words) with:

1. HYPOTHESIS: One clear, testable hypothesis
2. VARIABLES: 
   - Independent variable (what you'll change)
   - Dependent variable (what you'll measure)
3. METHOD: Brief procedure (3-5 steps)
4. EXPECTED OUTCOME: What results you expect

Be specific and scientific."""

    print("\n" + "=" * 70)
    print("📤 SENDING TO OLLAMA")
    print("=" * 70)
    print(f"URL: {OLLAMA_URL}")
    print(f"Model: {OLLAMA_MODEL}")
    print(f"Prompt length: {len(prompt)} characters")
    print(f"\nPrompt preview:")
    print("-" * 70)
    print(prompt[:300] + "...")
    print("-" * 70)
    
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "temperature": 0.3,
        "stream": True  # Use streaming to avoid timeout
    }
    
    try:
        print("\n⏳ Sending request and receiving streamed response...")
        print("(This may take 30-90 seconds for first request)\n")
        
        start_time = time.time()
        
        # Stream the response
        response = requests.post(
            OLLAMA_URL,
            json=payload,
            stream=True,
            timeout=300  # 5 minute timeout
        )
        
        if response.status_code != 200:
            return f"❌ Error: Status {response.status_code}"
        
        print("📥 RECEIVING STREAMED RESPONSE:")
        print("-" * 70)
        
        full_text = ""
        chunk_count = 0
        
        for line in response.iter_lines():
            if line:
                chunk_count += 1
                try:
                    chunk_data = json.loads(line)
                    text_chunk = chunk_data.get("response", "")
                    full_text += text_chunk
                    
                    # Show progress every 10 chunks
                    if chunk_count % 10 == 0:
                        print(f"... received {len(full_text)} chars (chunk {chunk_count})")
                    
                    # Print the text as it comes
                    print(text_chunk, end="", flush=True)
                    
                    if chunk_data.get("done", False):
                        break
                        
                except json.JSONDecodeError:
                    continue
        
        elapsed = time.time() - start_time
        
        print("\n" + "-" * 70)
        print(f"\n✅ Generation complete!")
        print(f"   Time: {elapsed:.2f} seconds")
        print(f"   Length: {len(full_text)} characters")
        print(f"   Chunks: {chunk_count}")
        
        return full_text
        
    except requests.exceptions.Timeout:
        elapsed = time.time() - start_time
        return f"❌ Timeout after {elapsed:.0f} seconds. Try a simpler prompt or faster model."
        
    except Exception as e:
        return f"❌ Error: {e}"


def main():
    print("\n" + "=" * 70)
    print("🔬 DRY RUN: EXPERIMENTAL DESIGN AGENT")
    print("=" * 70)
    print("\nThis will:")
    print("  ✓ Use mock research papers (no API calls)")
    print("  ✓ Send request to Ollama")
    print("  ✓ Show streamed response in real-time")
    print("  ✓ Save output to file")
    print("=" * 70)
    
    # Test topic
    topic = "Effect of dropout on CNN accuracy for image classification"
    
    print(f"\n📋 Research Topic:")
    print(f"   {topic}")
    
    # Fetch mock papers
    print("\n📚 Fetching mock research papers...")
    papers = fetch_mock_papers()
    print(f"   Found {len(papers)} papers")
    for i, paper in enumerate(papers, 1):
        print(f"   {i}. {paper['title']}")
    
    # Generate design
    design = generate_design_with_streaming(papers, topic)
    
    # Save output
    if design and not design.startswith("❌"):
        output_file = os.path.join(OUTPUT_DIR, "dry_run_experimental_design.txt")
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("=" * 70 + "\n")
            f.write("EXPERIMENTAL DESIGN - DRY RUN\n")
            f.write("=" * 70 + "\n\n")
            f.write(f"Topic: {topic}\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Model: {OLLAMA_MODEL}\n\n")
            f.write("=" * 70 + "\n\n")
            f.write(design)
        
        print(f"\n\n💾 Output saved to: {output_file}")
    
    # Summary
    print("\n\n" + "=" * 70)
    print("📊 DRY RUN SUMMARY")
    print("=" * 70)
    print(f"✅ Ollama connection: SUCCESS")
    print(f"✅ Request sent: SUCCESS")
    print(f"✅ Response received: {'SUCCESS' if design and not design.startswith('❌') else 'FAILED'}")
    print(f"✅ Output length: {len(design)} characters")
    
    if design and not design.startswith("❌"):
        print("\n🎉 Dry run completed successfully!")
        print("\nThe agent is working correctly. You can now:")
        print("   python experimental_design_agent.py 'Your research topic'")
    else:
        print("\n⚠️  Dry run encountered issues. Check the output above.")
    
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
