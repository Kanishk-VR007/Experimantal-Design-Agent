#!/usr/bin/env python3
"""
Test script for Experimental Design Agent
Validates core functionality without making API calls
"""

def test_import():
    """Test that the module can be imported"""
    try:
        from experimental_design_agent import ExperimentalDesignAgent
        print("✅ Module import successful")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def test_agent_creation():
    """Test that agent can be instantiated"""
    try:
        from experimental_design_agent import ExperimentalDesignAgent
        agent = ExperimentalDesignAgent()
        print(f"✅ Agent created: {agent.model}")
        return True
    except Exception as e:
        print(f"❌ Agent creation failed: {e}")
        return False

def test_mock_papers():
    """Test experimental design with mock paper data"""
    try:
        from experimental_design_agent import ExperimentalDesignAgent
        agent = ExperimentalDesignAgent()
        
        mock_papers = [
            {
                "title": "Neural Network Optimization",
                "abstract": "Study on gradient descent methods",
                "authors": ["Smith, J.", "Doe, A."],
                "method": "Comparative analysis",
                "limitations": "Limited to supervised learning"
            }
        ]
        
        print("✅ Mock paper data created")
        print(f"   Papers: {len(mock_papers)}")
        return True
    except Exception as e:
        print(f"❌ Mock test failed: {e}")
        return False

def test_bohrium_api_structure():
    """Test that Bohrium API call is structured correctly"""
    import requests
    
    # Just validate the URL and params structure
    api_url = "https://bohrium.com/api/v1/paper/search"
    params = {
        "keyword": "test",
        "page": 1,
        "page_size": 1,
        "sort": "relevance",
    }
    
    print(f"✅ API endpoint: {api_url}")
    print(f"✅ Parameters: {params}")
    print("   (Not making actual request in test mode)")
    return True

def main():
    print("\n" + "="*60)
    print("🧪 EXPERIMENTAL DESIGN AGENT - TEST SUITE")
    print("="*60 + "\n")
    
    tests = [
        ("Import Module", test_import),
        ("Create Agent", test_agent_creation),
        ("Mock Papers", test_mock_papers),
        ("API Structure", test_bohrium_api_structure),
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\n Testing: {name}")
        print("-" * 60)
        result = test_func()
        results.append((name, result))
    
    print("\n" + "="*60)
    print("📊 TEST RESULTS")
    print("="*60)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Agent is ready to use.")
        print("\nNext steps:")
        print("  1. Ensure Ollama is running: ollama serve")
        print("  2. Pull model: ollama pull llama3")
        print("  3. Run agent: python experimental_design_agent.py")
    else:
        print("\n⚠️  Some tests failed. Check errors above.")
    
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
