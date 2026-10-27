#!/usr/bin/env python3
"""
Quick Ollama Response Test
===========================
Verifies that Ollama receives requests and sends responses properly.
Shows detailed request/response flow.
"""

import requests
import json
import time

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3"

def test_simple_response():
    """Test a simple question to verify request/response flow"""
    
    prompt = "What is 2 + 2? Respond with just the number."
    
    print("=" * 70)
    print("  SIMPLE OLLAMA REQUEST/RESPONSE TEST")
    print("=" * 70)
    
    print(f"\n📤 SENDING REQUEST:")
    print(f"   URL: {OLLAMA_URL}")
    print(f"   Model: {MODEL}")
    print(f"   Prompt: '{prompt}'")
    
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "temperature": 0.1,
        "stream": False
    }
    
    print(f"\n📦 Request payload:")
    print(json.dumps(payload, indent=2))
    
    try:
        print(f"\n⏳ Waiting for response...")
        start = time.time()
        
        response = requests.post(OLLAMA_URL, json=payload, timeout=30)
        elapsed = time.time() - start
        
        print(f"\n📥 RESPONSE RECEIVED in {elapsed:.2f}s")
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            print(f"\n📋 Full response JSON:")
            print(json.dumps(result, indent=2))
            
            generated = result.get("response", "")
            print(f"\n✅ Generated text: '{generated}'")
            print(f"   Length: {len(generated)} characters")
            
            # Check other fields
            print(f"\n📊 Additional info:")
            print(f"   Model: {result.get('model', 'N/A')}")
            print(f"   Done: {result.get('done', 'N/A')}")
            print(f"   Total duration: {result.get('total_duration', 'N/A')}")
            
            print("\n🎉 SUCCESS - Ollama is receiving requests and sending responses!")
            return True
        else:
            print(f"❌ Error: Status {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return False


def test_experimental_design_simple():
    """Test a simple experimental design request"""
    
    prompt = """Design a simple experiment to test:
"Does adding dropout improve CNN accuracy on image classification?"

Respond with:
1. Hypothesis (1 sentence)
2. Variables (2-3 sentences)
3. Method (2-3 sentences)

Keep it under 100 words."""
    
    print("\n\n" + "=" * 70)
    print("  EXPERIMENTAL DESIGN REQUEST TEST")
    print("=" * 70)
    
    print(f"\n📤 Sending experimental design request...")
    print(f"   Prompt length: {len(prompt)} chars")
    
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "temperature": 0.3,
        "stream": False
    }
    
    try:
        print(f"⏳ Generating (may take 10-30 seconds)...")
        start = time.time()
        
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        elapsed = time.time() - start
        
        print(f"\n📥 Response received in {elapsed:.2f}s")
        
        if response.status_code == 200:
            result = response.json()
            design = result.get("response", "")
            
            print(f"\n✅ Generated experimental design:")
            print("─" * 70)
            print(design)
            print("─" * 70)
            
            print(f"\n📊 Stats:")
            print(f"   Generated: {len(design)} characters")
            print(f"   Time: {elapsed:.2f} seconds")
            
            print("\n🎉 SUCCESS - Ollama can handle experimental design requests!")
            return True
        else:
            print(f"❌ Error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return False


if __name__ == "__main__":
    print("\n" + "🧪 Testing Ollama Request/Response Flow\n")
    
    # Test 1: Simple
    test1 = test_simple_response()
    
    # Test 2: Experimental design
    test2 = test_experimental_design_simple()
    
    # Summary
    print("\n\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    print(f"Simple test: {'✅ PASS' if test1 else '❌ FAIL'}")
    print(f"Design test: {'✅ PASS' if test2 else '❌ FAIL'}")
    
    if test1 and test2:
        print("\n🎉 All tests passed! Ollama is working correctly.")
        print("\nReady to run full experimental design agent!")
    else:
        print("\n⚠️  Some tests failed.")
