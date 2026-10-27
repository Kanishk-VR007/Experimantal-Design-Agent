# Dry Run Feature Guide

## Overview

The dry run feature allows you to simulate the hypothesis generation workflow **without making any actual API calls**. This is useful for:

- Understanding what the system will do before running it
- Testing different experiment titles quickly
- Validating your experiment description
- Preview expected outputs and file structures
- Save API costs during testing

## Usage

### Basic Dry Run

```bash
python hypo_agent.py --dry-run --experiment "Your experiment title here"
```

### Examples

```bash
# Example 1: Image classification
python hypo_agent.py --dry-run --experiment "Compare CNN vs Transformer on CIFAR-10"

# Example 2: NLP task
python hypo_agent.py --dry-run --experiment "BERT vs GPT for text summarization"

# Example 3: Time series
python hypo_agent.py --dry-run --experiment "LSTM vs GRU for stock price prediction"

# Example 4: With max papers specified
python hypo_agent.py --dry-run --experiment "Compare optimizers" --max-papers 10
```

### Interactive Demo

Use the provided demo script to try multiple examples:

```bash
python dry_run_demo.py
```

Or with a custom experiment:

```bash
python dry_run_demo.py --custom "Your experiment title"
```

## What Does Dry Run Show?

The dry run mode displays:

### 1. **Configuration Info**
   - Experiment title
   - Max papers per query
   - Whether LLM is available (checks for API key)
   - Data sources (Bohrium + arXiv)

### 2. **Search Query Generation** (Step 1/4)
   - Shows 3 generated search queries
   - Uses keyword extraction (no LLM call)
   - Indicates if LLM would refine these in actual run

### 3. **Paper Fetching Simulation** (Step 2/4)
   - Shows what would be queried
   - Estimates number of papers per source
   - Estimates total unique papers

### 4. **Hypothesis Generation** (Step 3/4)
   - Shows the method (LLM-based or rule-based)
   - Explains the process
   - Lists what each hypothesis includes

### 5. **Output Files** (Step 4/4)
   - Shows file paths that would be created:
     - JSON data file (hypotheses + metadata)
     - Text report (human-readable)
     - Paper cache (raw paper data)

### 6. **Sample Output Structure**
   - Displays an example hypothesis in JSON format
   - Shows all fields: id, hypothesis, metrics, H0, H1, rationale

## Actual Run vs Dry Run

| Feature | Dry Run | Actual Run |
|---------|---------|------------|
| API Calls | ❌ None | ✅ Yes |
| Paper Fetching | ❌ Simulated | ✅ Real data |
| LLM Queries | ❌ None | ✅ If API key set |
| Output Files | ❌ Not created | ✅ Created |
| Execution Time | ~1 second | ~30-60 seconds |
| API Costs | 💰 Free | 💰 Tokens used |

## Switching to Actual Run

After reviewing the dry run output, execute the actual run by removing the `--dry-run` flag:

```bash
# Dry run
python hypo_agent.py --dry-run --experiment "Compare CNNs"

# Actual run
python hypo_agent.py --experiment "Compare CNNs"
```

## Exit Codes

- `0` - Successful dry run
- `1` - No experiment provided or error

## Tips

1. **Always dry run first** - See what queries will be generated
2. **Check API key status** - Dry run shows if LLM is available
3. **Refine experiment titles** - Test different phrasings
4. **Estimate costs** - See how many papers would be fetched
5. **Validate structure** - Ensure output meets your needs

## Notes

- Dry run uses keyword extraction for queries (faster, no API needed)
- Actual run uses LLM for better query generation (if API key is set)
- Paper estimates are approximate (actual count may vary)
- No files are created during dry run
- Safe to run unlimited times without costs

## See Also

- [hypo_agent.py](hypo_agent.py) - Main hypothesis generator
- [dry_run_demo.py](dry_run_demo.py) - Interactive demo script
- [README.md](../../README.md) - Full project documentation
