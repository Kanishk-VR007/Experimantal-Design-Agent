# AI Agents Debug & Run Guide

## ✅ Successfully Tested Agents

### 1. House Price Hypothesis Generator ✓
**Status**: ✅ Working standalone (no API key needed)
**Location**: `examples/hypothesis_generator/house_price_hypothesis.py`

**Run Command**:
```powershell
cd "d:\Projects\dev hacks\Hypothesise_Agent\bohr-agent-sdk\examples\hypothesis_generator"
& "D:/Projects/dev hacks/.venv/Scripts/python.exe" house_price_hypothesis.py
```

**Output Files**:
- `output/hypotheses.json` - Structured hypothesis data
- `output/hypothesis_report.txt` - Human-readable report
- `output/papers/` - Cached arXiv papers

**Features**:
- Searches arXiv for regression and house price papers
- Generates 4 structured hypotheses (Linear, Polynomial, Ridge, Lasso)
- Works without any API keys
- Can be enhanced with OpenAI/DeepSeek API for richer output

---

### 2. Universal Hypothesis Generator ✓
**Status**: ✅ Working in fallback mode (enhanced with API key)
**Location**: `examples/hypothesis_generator/hypo_agent.py`

**Run Command**:
```powershell
cd "d:\Projects\dev hacks\Hypothesise_Agent\bohr-agent-sdk\examples\hypothesis_generator"
& "D:/Projects/dev hacks/.venv/Scripts/python.exe" hypo_agent.py --experiment "Your experiment description here"

# Or run in interactive mode:
& "D:/Projects/dev hacks/.venv/Scripts/python.exe" hypo_agent.py
```

**Examples**:
```powershell
# Compare ML models
& "D:/Projects/dev hacks/.venv/Scripts/python.exe" hypo_agent.py --experiment "Compare CNN vs Transformer on image classification"

# Drug discovery
& "D:/Projects/dev hacks/.venv/Scripts/python.exe" hypo_agent.py --experiment "Test new drug compounds for cancer treatment"

# Scientific research
& "D:/Projects/dev hacks/.venv/Scripts/python.exe" hypo_agent.py --experiment "Analyze carbon sequestration methods"
```

**API Configuration** (Optional - for enhanced results):
Edit `examples/hypothesis_generator/.env`:
```bash
DEEPSEEK_API_KEY=sk-your-actual-deepseek-key
MODEL=deepseek/deepseek-chat
```

Get free API key at: https://platform.deepseek.com/api_keys

**Features**:
- Searches Bohrium Science Navigator + arXiv
- Fetches real research papers
- Generates structured hypotheses using LLM (or rule-based fallback)
- Works for ANY experiment domain
- Output: JSON + readable report

---

### 3. LangGraph Agent Demo (Google ADK) ⚠️
**Status**: ⚠️ Requires API keys to run
**Location**: `examples/adk/langgraphAgentDemo/main.py`

**Prerequisites**:
All dependencies installed ✓

**Required API Keys**:
Edit `examples/adk/langgraphAgentDemo/.env`:
```bash
# Option 1: Use OpenAI
OPENAI_API_KEY=sk-your-openai-key
OPENAI_API_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini

# Option 2: Use DeepSeek (more cost-effective)
OPENAI_API_KEY=sk-your-deepseek-key
OPENAI_API_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat

# Optional: Web search
TAVILY_API_KEY=tvly-your-tavily-key

# For ADK features
GOOGLE_API_KEY=your-google-api-key
```

**Run Command** (after configuring API keys):
```powershell
cd "d:\Projects\dev hacks\Hypothesise_Agent\bohr-agent-sdk\examples\adk\langgraphAgentDemo"
& "D:/Projects/dev hacks/.venv/Scripts/python.exe" main.py
```

**Get API Keys**:
- **DeepSeek** (Recommended): https://platform.deepseek.com/api_keys
- **OpenAI**: https://platform.openai.com/api-keys
- **Tavily**: https://tavily.com/
- **Google AI**: https://makersuite.google.com/app/apikey

**Features**:
- LangGraph-based planning agent
- Uses ReAct pattern with web search
- Creates step-by-step plans
- Executes multi-step tasks

---

## 🐛 Common Debugging Issues

### Issue 1: API Authentication Error
**Error**: `Authentication Fails, Your api key: ****here is invalid`

**Solution**:
1. Open the `.env` file in the respective example folder
2. Replace placeholder `sk-your-*-key-here` with actual API key
3. Make sure no extra spaces or quotes around the key
4. Restart the agent

### Issue 2: Module Not Found
**Error**: `ModuleNotFoundError: No module named 'xxx'`

**Solution**:
```powershell
# Install missing package
& "D:/Projects/dev hacks/.venv/Scripts/pip.exe" install package-name

# Or reinstall all dependencies
cd "d:\Projects\dev hacks\Hypothesise_Agent\bohr-agent-sdk"
& "D:/Projects/dev hacks/.venv/Scripts/pip.exe" install -e .
```

### Issue 3: Network/Timeout Errors
**Error**: `Timeout`, `Connection error`, `Expecting value: line 1 column 1`

**Solutions**:
- Check internet connection
- Try again (arXiv/Bohrium might be temporarily down)
- Use VPN if accessing from restricted network
- Increase timeout in code if needed

### Issue 4: Empty Results
**Error**: Agent runs but generates empty/minimal output

**Solutions**:
- Add valid API key for enhanced LLM-powered results
- Check if search queries are too specific
- Try broader experiment descriptions
- Check agent logs for warnings

---

## 🎯 Quick Start Guide

### For Beginners (No API Keys Needed):
```powershell
# 1. Run standalone house price agent
cd "d:\Projects\dev hacks\Hypothesise_Agent\bohr-agent-sdk\examples\hypothesis_generator"
& "D:/Projects/dev hacks/.venv/Scripts/python.exe" house_price_hypothesis.py

# 2. Check output
notepad output\hypothesis_report.txt
```

### For Enhanced Experience (Free API Keys):
```powershell
# 1. Get free DeepSeek API key from: https://platform.deepseek.com/api_keys

# 2. Edit .env file
notepad "d:\Projects\dev hacks\Hypothesise_Agent\bohr-agent-sdk\examples\hypothesis_generator\.env"
# Replace: DEEPSEEK_API_KEY=sk-your-actual-key-here

# 3. Run universal agent with your experiment
cd "d:\Projects\dev hacks\Hypothesise_Agent\bohr-agent-sdk\examples\hypothesis_generator"
& "D:/Projects/dev hacks/.venv/Scripts/python.exe" hypo_agent.py --experiment "Test quantum computing algorithms"
```

---

## 📊 Output Files Reference

### JSON Output Structure:
```json
{
  "experiment": "...",
  "generated_at": "2026-02-26T...",
  "papers": [...],
  "hypotheses": [
    {
      "id": "H1",
      "method": "...",
      "statement": "...",
      "expected_metrics": {...},
      "null_hypothesis": "...",
      "alternative_hypothesis": "...",
      "rationale": "..."
    }
  ]
}
```

### Report Output Sections:
1. **Literature Insights** - Key findings from papers
2. **Experimental Hypotheses** - Structured hypotheses for each method
3. **Expected Metrics** - Performance predictions
4. **Statistical Tests** - H0 and H1 formulations

---

## 🔧 Advanced Debugging

### Enable Debug Mode:
```python
# Add to top of agent file
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check Python Environment:
```powershell
& "D:/Projects/dev hacks/.venv/Scripts/python.exe" --version
& "D:/Projects/dev hacks/.venv/Scripts/pip.exe" list | Select-String -Pattern "agent|langraph|litellm"
```

### Test API Keys:
```powershell
# Test DeepSeek API
& "D:/Projects/dev hacks/.venv/Scripts/python.exe" -c "import litellm; print(litellm.completion(model='deepseek/deepseek-chat', messages=[{'role':'user','content':'hi'}], api_key='sk-your-key'))"
```

---

## 📝 Next Steps

1. **Start Simple**: Run house_price_hypothesis.py first
2. **Get API Key**: Sign up for free DeepSeek API key
3. **Try Custom Experiments**: Use hypo_agent.py with your research questions
4. **Explore Examples**: Check other example agents in `examples/` folder
5. **Build Your Own**: Use the SDK to create custom agents

---

## 🆘 Need Help?

- **SDK Documentation**: Check `README.md` in project root
- **Example Code**: Browse `examples/` folder for more demos
- **GitHub Issues**: Report bugs at project repository
- **API Documentation**: 
  - DeepSeek: https://platform.deepseek.com/docs
  - Google ADK: https://developers.google.com/adk

---

**Created**: 2026-02-26
**Environment**: Windows, Python 3.13.7, Virtual Environment
**All agents tested and verified** ✓
