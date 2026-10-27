#!/usr/bin/env python3
"""
Ollama Integration Test & Dry Run
==================================
Tests Ollama connectivity and runs a complete dry run of the experimental design agent.

This script will:
1. Check if Ollama is running
2. Verify model availability (llama3)
3. Test basic API call to Ollama
4. Run a complete experiment design workflow
5. Show verbose output of all API interactions

Usage:
    python test_ollama_integration.py
"""

import os
import sys
import json
import time
import requests
from datetime import datetime
from typing import Dict, Optional
from dotenv import load_dotenv

load_dotenv()

# Configuration
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "output", "ollama_test_results.json")


def print_section(title: str):
    """Print a formatted section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def check_ollama_running() -> bool:
    """Check if Ollama server is running"""
    print("🔍 Checking Ollama server status...")
    
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        if response.status_code == 200:
            print("✅ Ollama server is running!")
            
            data = response.json()
            models = data.get("models", [])
            
            if models:
                print(f"\n📦 Available models ({len(models)}):")
                for model in models:
                    print(f"   • {model.get('name', 'unknown')}")
            else:
                print("\n⚠️  No models installed. Run: ollama pull llama3")
            
            return True
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to Ollama server")
        print("\n💡 To fix this:")
        print("   1. Install Ollama from: https://ollama.ai")
        print("   2. Open a terminal and run: ollama serve")
        print("   3. Pull model: ollama pull llama3")
        return False
        
    except Exception as e:
        print(f"❌ Error checking Ollama: {e}")
        return False


def test_ollama_generation() -> Optional[Dict]:
    """Test a simple text generation request to Ollama"""
    print("🧪 Testing Ollama text generation API...")
    
    test_prompt = "Respond with exactly: 'Test successful'"
    
    try:
        print(f"\n📤 Sending request to: {OLLAMA_URL}/api/generate")
        print(f"   Model: {OLLAMA_MODEL}")
        print(f"   Prompt: '{test_prompt}'")
        
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": test_prompt,
            "temperature": 0.1,
            "stream": False
        }
        
        start_time = time.time()
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json=payload,
            timeout=30
        )
        elapsed = time.time() - start_time
        
        print(f"\n📥 Response received in {elapsed:.2f} seconds")
        print(f"   Status code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            generated_text = result.get("response", "")
            
            print(f"   Generated text: '{generated_text[:100]}...'")
            print("✅ Ollama API call successful!")
            
            return {
                "success": True,
                "model": OLLAMA_MODEL,
                "response": generated_text,
                "elapsed_time": elapsed,
                "timestamp": datetime.now().isoformat()
            }
        else:
            print(f"❌ API call failed with status {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out (30s)")
        print("   The model might be loading or the server is overloaded")
        return None
        
    except requests.exceptions.ConnectionError:
        print("❌ Connection error - Ollama server not responding")
        return None
        
    except Exception as e:
        print(f"❌ Error during generation: {e}")
        return None


def test_experimental_design_workflow() -> bool:
    """Test the complete experimental design workflow"""
    print("🔬 Testing complete experimental design workflow...")
    
    # Mock research papers for testing
    mock_papers = [
        {
            "title": "Deep Learning for Image Classification: A Survey",
            "abstract": "This paper surveys recent advances in deep learning for image classification, "
                       "comparing CNNs, Transformers, and hybrid architectures. Results show transformers "
                       "achieve 95% accuracy on ImageNet while CNNs reach 92%.",
            "authors": ["Smith, J.", "Doe, A.", "Johnson, B."],
            "source": "Bohrium",
            "citations": 342
        },
        {
            "title": "Transformer Architecture Optimization for Computer Vision",
            "abstract": "We propose an optimized transformer architecture for vision tasks. "
                       "Our approach reduces computational cost by 40% while maintaining accuracy. "
                       "Experiments on CIFAR-10 and ImageNet show promising results.",
            "authors": ["Lee, K.", "Wang, L."],
            "source": "arXiv",
            "citations": 127
        },
        {
            "title": "Convolutional Neural Networks: Recent Improvements",
            "abstract": "Recent improvements in CNN architectures including residual connections, "
                       "attention mechanisms, and efficient convolutions. We achieve state-of-the-art "
                       "on multiple benchmarks with reduced parameters.",
            "authors": ["Chen, Y.", "Zhang, H.", "Liu, M."],
            "source": "Bohrium",
            "citations": 256
        }
    ]
    
    print(f"\n📚 Using {len(mock_papers)} mock research papers")
    for i, paper in enumerate(mock_papers, 1):
        print(f"   {i}. {paper['title'][:60]}...")
    
    # Create prompt for experimental design
    prompt = f"""You are an expert Experimental Design Agent.

Based on these research papers:
{json.dumps(mock_papers, indent=2)}

Generate a concise experimental design (200-300 words) that includes:
1. Research gap identified
2. Clear hypothesis
3. Experimental variables (independent, dependent, control)
4. Brief methodology
5. Expected outcomes

Be specific and scientific. Focus on designing a NEW experiment."""
    
    print("\n📤 Generating experimental design with Ollama...")
    print(f"   Model: {OLLAMA_MODEL}")
    print(f"   Prompt length: {len(prompt)} characters")
    
    try:
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "temperature": 0.3,
            "stream": False
        }
        
        start_time = time.time()
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json=payload,
            timeout=120  # 2 minutes for longer generation
        )
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            design = result.get("response", "")
            
            print(f"\n✅ Design generated in {elapsed:.2f} seconds")
            print(f"   Generated length: {len(design)} characters")
            print("\n" + "─" * 70)
            print("📋 GENERATED EXPERIMENTAL DESIGN:")
            print("─" * 70)
            print(design)
            print("─" * 70)
            
            # Save results
            os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "timestamp": datetime.now().isoformat(),
                    "model": OLLAMA_MODEL,
                    "papers": mock_papers,
                    "design": design,
                    "generation_time": elapsed
                }, f, indent=2, ensure_ascii=False)
            
            print(f"\n💾 Results saved to: {OUTPUT_FILE}")
            return True
            
        else:
            print(f"❌ Generation failed with status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Workflow test failed: {e}")
        return False


def main():
    print("\n" + "=" * 70)
    print("  OLLAMA INTEGRATION TEST & DRY RUN")
    print("=" * 70)
    
    # Test 1: Check if Ollama is running
    print_section("1️⃣  OLLAMA SERVER STATUS")
    ollama_running = check_ollama_running()
    
    if not ollama_running:
        print("\n🚫 Cannot proceed - Ollama server is not running")
        print("\nPlease start Ollama and try again.")
        return 1
    
    # Test 2: Test basic API call
    print_section("2️⃣  BASIC API TEST")
    test_result = test_ollama_generation()
    
    if not test_result:
        print("\n⚠️  Basic API test failed")
        print("   The server is running but not responding to generate requests")
        return 1
    
    # Test 3: Complete workflow
    print_section("3️⃣  COMPLETE WORKFLOW TEST")
    workflow_success = test_experimental_design_workflow()
    
    # Summary
    print_section("📊 TEST SUMMARY")
    print("✅ Ollama server: RUNNING")
    print(f"✅ Model: {OLLAMA_MODEL}")
    print(f"✅ Basic generation: {'SUCCESS' if test_result else 'FAILED'}")
    print(f"✅ Workflow test: {'SUCCESS' if workflow_success else 'FAILED'}")
    
    if test_result and workflow_success:
        print("\n🎉 All tests passed! Ollama is working correctly.")
        print("\nYou can now run the experimental design agent:")
        print("   python experimental_design_agent.py")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please check the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
