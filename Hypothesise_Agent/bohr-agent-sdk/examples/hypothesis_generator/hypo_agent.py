#!/usr/bin/env python3
"""
Universal Hypothesis Generation Agent
======================================
Uses the Bohrium Science Agent SDK to:
  1. Accept ANY experiment description as input
  2. Fetch real research papers from Bohrium AI Science Navigator + arXiv
  3. Use DeepSeek LLM to generate structured hypotheses (in English)
  4. Save JSON + readable report to output/

Usage:
    python hypo_agent.py --experiment "Compare CNN, RNN, Transformer on CIFAR-10"
    python hypo_agent.py --experiment "Effect of learning rate on model convergence" --max-papers 10
    python hypo_agent.py --dry-run --experiment "Transformer vs LSTM for time series"
    python hypo_agent.py          # interactive mode (prompts for input)

Dry Run Mode:
    Use --dry-run flag to simulate the workflow without making API calls.
    Shows generated queries, expected workflow, and output structure.

Requirements (install if missing):
    pip install litellm arxiv python-dotenv requests beautifulsoup4

API Key setup (create a .env file here or set env vars):
    DEEPSEEK_API_KEY=sk-...
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import os
import re
import json
import time
import textwrap
import argparse
import requests
from datetime import datetime
from typing import List, Dict, Optional

import arxiv
from dotenv import load_dotenv

# ─── Load Environment ────────────────────────────────────────────────────────────
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
if not DEEPSEEK_API_KEY:
    raise ValueError("Missing DEEPSEEK_API_KEY in .env file.")
MODEL = os.getenv("MODEL", "deepseek/deepseek-chat")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
PAPER_DIR  = os.path.join(OUTPUT_DIR, "papers")
os.makedirs(PAPER_DIR, exist_ok=True)

# ─── LLM Client (via litellm -> DeepSeek) ───────────────────────────────────────

def call_llm(system_prompt: str, user_prompt: str, expect_json: bool = False) -> str:
    """
    Calls DeepSeek via litellm. Forces English-only responses.
    Falls back gracefully if no API key is set.
    """
    if not DEEPSEEK_API_KEY:
        print("[WARN] No DEEPSEEK_API_KEY found — using rule-based fallback mode.")
        return ""

    try:
        import litellm
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ]
        response = litellm.completion(
            model=MODEL,
            messages=messages,
            api_key=DEEPSEEK_API_KEY,
            temperature=0.4,
            max_tokens=4096,
            top_p=0.9,
            frequency_penalty=0.1,
        )
        return response.choices[0].message.content.strip()
    except ImportError:
        print("[WARN] litellm not installed. Run: pip install litellm")
        return ""
    except Exception as e:
        print(f"[WARN] LLM call failed: {e}")
        return ""


# ─── Paper Source 1: Bohrium Science Navigator (web search) ─────────────────────

def search_bohrium(query: str, max_results: int = 5) -> List[Dict]:
    """
    Searches Bohrium's Science Navigator for academic papers.
    Uses the public search endpoint — returns title, abstract, authors, DOI, citations.
    """
    papers = []
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; BohriumHypoAgent/1.0)",
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://bohrium.com/",
        }
        # Bohrium public paper search API (Science Navigator)
        api_url = "https://bohrium.com/api/v1/paper/search"
        params  = {
            "keyword": query,
            "page": 1,
            "page_size": max_results,
            "sort": "relevance",
        }
        resp = requests.get(api_url, params=params, headers=headers, timeout=10)

        if resp.status_code == 200:
            data = resp.json()
            items = (
                data.get("data", {}).get("list", [])
                or data.get("data", [])
                or data.get("results", [])
                or data.get("items", [])
            )
            for item in items[:max_results]:
                papers.append({
                    "source": "Bohrium",
                    "id":      item.get("doi", item.get("id", "unknown")),
                    "title":   item.get("title_en") or item.get("title", ""),
                    "authors": [a.get("name", a) if isinstance(a, dict) else str(a)
                                for a in item.get("authors", [])],
                    "summary": item.get("abstract_en") or item.get("abstract", ""),
                    "url":     item.get("url", ""),
                    "citations": item.get("citation_count", 0),
                    "impact_factor": item.get("impact_factor", ""),
                    "published": item.get("publish_date", ""),
                })
        else:
            print(f"   [Bohrium] HTTP {resp.status_code} for query: '{query}'")
    except requests.exceptions.Timeout:
        print(f"   [Bohrium] Request timed out for query: '{query}'")
    except Exception as e:
        print(f"   [Bohrium] Search error: {e}")

    return papers


# ─── Paper Source 2: arXiv ───────────────────────────────────────────────────────

def search_arxiv(query: str, max_results: int = 4) -> List[Dict]:
    """
    Searches arXiv as the secondary/fallback source.
    No API key required.
    """
    papers = []
    try:
        client = arxiv.Client()
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance,
        )
        for paper in client.results(search):
            papers.append({
                "source":  "arXiv",
                "id":       paper.get_short_id(),
                "title":    paper.title,
                "authors":  [a.name for a in paper.authors],
                "summary":  paper.summary.replace("\n", " "),
                "url":      paper.pdf_url,
                "citations": None,
                "impact_factor": None,
                "published": str(paper.published.date()),
            })
    except Exception as e:
        print(f"   [arXiv] Search error: {e}")
    return papers


# ─── Query Generation via LLM ────────────────────────────────────────────────────

SYSTEM_QUERY_GEN = """You are a research assistant. 
IMPORTANT: You MUST respond ONLY in English. Do NOT use Chinese or any other language.
Your task is to generate search queries for academic paper databases."""

def generate_search_queries(experiment: str) -> List[str]:
    """
    Uses DeepSeek to generate 3 targeted search queries for the experiment.
    Falls back to simple keyword extraction if no API key.
    """
    prompt = f"""Given the following scientific experiment description, generate exactly 3 
concise and specific academic search queries to find relevant research papers.

Experiment: {experiment}

Return ONLY a JSON array of 3 strings. Example format:
["query one", "query two", "query three"]

Rules:
- Each query should target a different aspect of the experiment
- Use technical/academic terminology
- Keep queries under 10 words each
- Output ONLY the JSON array, nothing else"""

    result = call_llm(SYSTEM_QUERY_GEN, prompt, expect_json=True)
    if result:
        try:
            # Extract JSON array from response
            match = re.search(r'\[.*?\]', result, re.DOTALL)
            if match:
                queries = json.loads(match.group())
                if isinstance(queries, list) and len(queries) >= 1:
                    return [str(q) for q in queries[:3]]
        except Exception:
            pass

    # Fallback: extract key terms from experiment description
    print("   [>] Using keyword extraction for search queries (no LLM)")
    words = re.findall(r'\b[A-Za-z][A-Za-z0-9]{3,}\b', experiment)
    stopwords = {'with', 'from', 'that', 'this', 'have', 'will', 'using', 'compare',
                 'comparing', 'analysis', 'analyze', 'implement', 'based', 'dataset'}
    keywords = [w for w in words if w.lower() not in stopwords][:6]
    return [
        " ".join(keywords[:4]) + " machine learning",
        " ".join(keywords[:3]) + " deep learning survey",
        " ".join(keywords[1:5]) + " performance comparison",
    ]


# ─── Hypothesis Generation via LLM ──────────────────────────────────────────────

SYSTEM_HYPO_GEN = """You are a senior scientific researcher writing an experiment report.
CRITICAL: You MUST respond ONLY in English. Do NOT use Chinese, Japanese, or any other language.
All output must be in English regardless of input language.
Your task is to generate well-structured scientific hypotheses."""

def generate_hypotheses_llm(experiment: str, papers: List[Dict]) -> Optional[str]:
    """
    Uses DeepSeek to generate structured hypotheses from experiment + paper abstracts.
    Returns JSON string or None if LLM unavailable.
    """
    # Build abstract summaries (cap text to avoid token overflow)
    paper_summaries = []
    for i, p in enumerate(papers[:10], 1):
        abstract = p["summary"][:400] if p["summary"] else "No abstract available."
        paper_summaries.append(
            f"[Paper {i}] ({p['source']}) {p['title']}\n"
            f"  Authors: {', '.join(p['authors'][:3])}\n"
            f"  Abstract: {abstract}"
        )
    papers_block = "\n\n".join(paper_summaries) if paper_summaries else \
                   "No papers found. Use general scientific knowledge."

    prompt = f"""You are generating scientific hypotheses for this experiment:

EXPERIMENT: {experiment}

RELEVANT RESEARCH PAPERS:
{papers_block}

Generate 4-5 structured scientific hypotheses for this experiment.
IMPORTANT: Write everything in ENGLISH ONLY.

Return a valid JSON object in this EXACT format:
{{
  "hypotheses": [
    {{
      "id": "H1",
      "aspect": "short label for what this hypothesis tests",
      "hypothesis": "detailed statement of the hypothesis (2-4 sentences)",
      "null_hypothesis": "H0: formal null hypothesis statement",
      "alternate_hypothesis": "H1: formal alternate hypothesis statement",
      "expected_metrics": {{
        "metric_name": "expected value or direction"
      }},
      "rationale": "brief evidence-based rationale from literature (1-2 sentences)"
    }}
  ]
}}

Rules:
- All text MUST be in English
- Make hypotheses specific and testable
- Base rationale on the provided papers where possible
- Include quantitative expected outcomes where applicable
- Output ONLY the JSON object, no extra text"""

    return call_llm(SYSTEM_HYPO_GEN, prompt, expect_json=True)


# ─── Fallback: Rule-based Hypothesis from Abstracts ─────────────────────────────

def generate_hypotheses_fallback(experiment: str, papers: List[Dict]) -> List[Dict]:
    """
    Rule-based hypothesis generation when no LLM is available.
    Extracts key sentences and builds generic H0/H1 pairs.
    """
    performance_keywords = ["outperform", "better", "higher", "lower", "accuracy",
                             "RMSE", "R2", "precision", "recall", "F1", "error",
                             "superior", "improved", "significant", "baseline"]
    insights = []
    for p in papers:
        for sent in p["summary"].split(". "):
            if any(kw.lower() in sent.lower() for kw in performance_keywords):
                if len(sent.strip()) > 40:
                    insights.append(sent.strip()[:200])
        if len(insights) >= 8:
            break

    # Extract method names from experiment description
    methods = re.findall(r'(?:Linear|Polynomial|Ridge|Lasso|CNN|RNN|LSTM|Transformer|'
                         r'SVM|KNN|Random Forest|XGBoost|Logistic|Naive Bayes|'
                         r'Decision Tree|Neural Network)\s*(?:Regression|Classification)?',
                         experiment, re.IGNORECASE)
    methods = list(dict.fromkeys([m.strip() for m in methods])) or ["Method A", "Method B"]

    hypotheses = []
    for i, method in enumerate(methods[:4], 1):
        hypotheses.append({
            "id": f"H{i}",
            "aspect": method,
            "hypothesis": (
                f"{method} will demonstrate measurable performance characteristics on the given dataset. "
                f"Based on theoretical properties of {method}, specific trade-offs between model "
                f"complexity, training efficiency, and generalization are expected."
            ),
            "null_hypothesis": f"H0: {method} achieves no statistically significant predictive performance.",
            "alternate_hypothesis": f"H1: {method} achieves statistically significant predictive performance above baseline.",
            "expected_metrics": {"Performance": "TBD after experiment", "Compared to baseline": "Expected improvement"},
            "rationale": insights[i-1] if i-1 < len(insights) else "Based on general ML literature."
        })

    if len(methods) >= 2:
        hypotheses.append({
            "id": f"H{len(hypotheses)+1}",
            "aspect": "Comparative Analysis",
            "hypothesis": (
                f"Among all methods tested ({', '.join(methods[:4])}), there will be statistically "
                f"significant differences in generalization performance on the test set. "
                f"Regularized or more complex models will generalize better than linear baselines."
            ),
            "null_hypothesis": "H0: No statistically significant difference exists in generalization across all methods tested.",
            "alternate_hypothesis": "H1: At least one method significantly outperforms others on the test evaluation metric.",
            "expected_metrics": {"Best generalization": "Most complex/regularized model", "Worst overfitting": "Unrestricted polynomial/deep model"},
            "rationale": insights[0] if insights else "Based on bias-variance tradeoff theory."
        })

    return hypotheses


# ─── Report Saving ───────────────────────────────────────────────────────────────

def save_outputs(experiment: str, papers: List[Dict], hypotheses: List[Dict]):
    """Saves JSON data and a human-readable text report."""
    slug = re.sub(r'[^\w]', '_', experiment[:40]).strip('_').lower()
    timestamp = datetime.now().isoformat()

    result = {
        "experiment": experiment,
        "generated_at": timestamp,
        "agent": "Bohrium Universal Hypothesis Generator",
        "paper_sources": ["Bohrium Science Navigator", "arXiv"],
        "papers_fetched": len(papers),
        "papers": [{"source": p["source"], "id": p["id"], "title": p["title"],
                    "published": p.get("published", ""), "url": p.get("url", "")}
                   for p in papers],
        "hypotheses": hypotheses,
    }

    json_path = os.path.join(OUTPUT_DIR, f"hypotheses_{slug}.json")
    txt_path  = os.path.join(OUTPUT_DIR, f"report_{slug}.txt")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    # Build text report
    lines = ["=" * 72,
             "  BOHRIUM HYPOTHESIS GENERATION REPORT",
             f"  Experiment: {experiment}",
             f"  Generated : {timestamp}",
             "=" * 72]

    lines += ["\nPAPERS FETCHED", "-" * 72]
    for p in papers[:12]:
        lines.append(f"  [{p['source']}] {p['title'][:65]}")
        if p.get("published"):
            lines.append(f"    Published: {p['published']}")

    lines += ["\n\nHYPOTHESES", "=" * 72]
    for h in hypotheses:
        lines.append(f"\n[{h['id']}] {h.get('aspect', h['id'])}")
        lines.append("-" * 60)
        lines.append("\nStatement:")
        lines.append(textwrap.fill(h["hypothesis"], 70, initial_indent="  ", subsequent_indent="  "))
        lines.append("\nExpected Metrics:")
        for k, v in h.get("expected_metrics", {}).items():
            lines.append(f"  - {k}: {v}")
        lines.append(f"\n  H0: {h.get('null_hypothesis', 'N/A')}")
        lines.append(f"  H1: {h.get('alternate_hypothesis', 'N/A')}")
        if h.get("rationale"):
            lines.append("\nRationale:")
            lines.append(textwrap.fill(h["rationale"], 70, initial_indent="  ", subsequent_indent="  "))

    lines += ["\n" + "=" * 72, "END OF REPORT", "=" * 72]
    report = "\n".join(lines)

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(report)

    return json_path, txt_path, report


# ─── Dry Run Mode ────────────────────────────────────────────────────────────────

def perform_dry_run(experiment: str, max_papers: int = 5):
    """
    Simulates the hypothesis generation workflow without making actual API calls.
    Shows what queries would be generated, what steps would be executed, and 
    what output files would be created.
    """
    print("\n" + "=" * 72)
    print("  DRY RUN MODE - No API calls will be made")
    print("=" * 72)
    
    print(f"\n[*] Experiment: {experiment}")
    print(f"[*] Max Papers per Query: {max_papers}")
    
    has_llm = bool(DEEPSEEK_API_KEY)
    print(f"[*] LLM Available: {'Yes (' + MODEL + ')' if has_llm else 'No (will use rule-based fallback)'}")
    print(f"[*] Sources: Bohrium Science Navigator + arXiv")
    
    # Step 1: Show query generation
    print("\n" + "=" * 72)
    print("[STEP 1/4] SEARCH QUERY GENERATION")
    print("=" * 72)
    
    # Generate queries using keyword extraction (no LLM call in dry run)
    words = re.findall(r'\b[A-Za-z][A-Za-z0-9]{3,}\b', experiment)
    stopwords = {'with', 'from', 'that', 'this', 'have', 'will', 'using', 'compare',
                 'comparing', 'analysis', 'analyze', 'implement', 'based', 'dataset'}
    keywords = [w for w in words if w.lower() not in stopwords][:6]
    
    queries = [
        " ".join(keywords[:4]) + " machine learning",
        " ".join(keywords[:3]) + " deep learning survey",
        " ".join(keywords[1:5]) + " performance comparison",
    ]
    
    print("\nGenerated queries (keyword-based simulation):")
    for i, q in enumerate(queries, 1):
        print(f"  Q{i}: {q}")
    
    if has_llm:
        print("\n  Note: In actual run, queries would be refined using LLM")
    
    # Step 2: Show paper fetching simulation
    print("\n" + "=" * 72)
    print("[STEP 2/4] PAPER FETCHING SIMULATION")
    print("=" * 72)
    
    total_papers = 0
    for i, query in enumerate(queries, 1):
        print(f"\n  Query {i}: '{query}'")
        print(f"    [Bohrium] Would fetch up to {max_papers} papers")
        print(f"    [arXiv]   Would fetch up to {max_papers} papers")
        # Estimate 3-4 papers per query on average
        estimated = min(max_papers * 2, 8)
        total_papers += estimated
        print(f"    Estimated: ~{estimated} unique papers from this query")
    
    print(f"\n  Total estimated unique papers: ~{total_papers}")
    
    # Step 3: Show hypothesis generation
    print("\n" + "=" * 72)
    print("[STEP 3/4] HYPOTHESIS GENERATION")
    print("=" * 72)
    
    if has_llm:
        print("\n  Method: LLM-based (DeepSeek)")
        print("  Process:")
        print("    1. Send experiment description + paper abstracts to LLM")
        print("    2. LLM analyzes research findings and generates structured hypotheses")
        print("    3. Expected: 4-5 hypotheses with detailed metrics and rationale")
    else:
        print("\n  Method: Rule-based fallback")
        print("  Process:")
        print("    1. Extract key insights from paper abstracts")
        print("    2. Generate hypotheses using templates")
        print("    3. Expected: 3-4 hypotheses based on common experimental aspects")
    
    print("\n  Each hypothesis will include:")
    print("    - ID and aspect (e.g., 'H1', 'Model Performance')")
    print("    - Hypothesis statement")
    print("    - Expected metrics (e.g., accuracy, F1-score)")
    print("    - Null hypothesis (H0)")
    print("    - Alternate hypothesis (H1)")
    print("    - Rationale based on literature")
    
    # Step 4: Show output files
    print("\n" + "=" * 72)
    print("[STEP 4/4] OUTPUT FILES")
    print("=" * 72)
    
    slug = re.sub(r'[^\w]', '_', experiment[:40]).strip('_').lower()
    
    json_path = os.path.join(OUTPUT_DIR, f"hypotheses_{slug}.json")
    txt_path = os.path.join(OUTPUT_DIR, f"report_{slug}.txt")
    paper_cache = os.path.join(PAPER_DIR, f"{slug}_papers.json")
    
    print("\n  Files that would be created:")
    print(f"\n  1. JSON Data:")
    print(f"     {json_path}")
    print("     Contains structured hypotheses + paper metadata")
    
    print(f"\n  2. Text Report:")
    print(f"     {txt_path}")
    print("     Human-readable report with all hypotheses and references")
    
    print(f"\n  3. Paper Cache:")
    print(f"     {paper_cache}")
    print("     Raw paper data from Bohrium + arXiv")
    
    # Show sample output structure
    print("\n" + "=" * 72)
    print("SAMPLE OUTPUT STRUCTURE")
    print("=" * 72)
    
    sample_hypothesis = {
        "id": "H1",
        "aspect": "Model Performance",
        "hypothesis": f"In the {experiment}, the primary model will achieve significantly better performance compared to baseline approaches.",
        "expected_metrics": {
            "accuracy": "> 85%",
            "training_time": "< 10 hours",
            "inference_latency": "< 100ms"
        },
        "null_hypothesis": "There is no significant difference between models.",
        "alternate_hypothesis": "The proposed approach shows statistically significant improvement (p < 0.05).",
        "rationale": "Based on recent literature findings from similar experiments, this approach is expected to leverage architectural advantages."
    }
    
    print("\nExample Hypothesis JSON:")
    print(json.dumps(sample_hypothesis, indent=2))
    
    print("\n" + "=" * 72)
    print("DRY RUN COMPLETE")
    print("=" * 72)
    print("\nTo execute the actual run, remove the --dry-run flag:")
    print(f'  python hypo_agent.py --experiment "{experiment}"')
    print("\n")


# ─── Main Pipeline ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Bohrium Universal Hypothesis Generator Agent"
    )
    parser.add_argument(
        "--experiment", "-e",
        type=str,
        default=None,
        help='Experiment description, e.g. "Compare CNN and RNN on CIFAR-10"'
    )
    parser.add_argument(
        "--max-papers", "-n",
        type=int,
        default=5,
        help="Max papers to fetch per query (default: 5)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without making API calls (shows what would happen)"
    )
    args = parser.parse_args()

    print("\n[*] Bohrium Universal Hypothesis Generation Agent")
    print("=" * 60)

    # ── Get experiment description ──
    experiment = args.experiment
    if not experiment:
        print("\nEnter your experiment description below.")
        print("Example: 'Compare CNN, RNN and Transformer for sentiment analysis'")
        experiment = input("[?] Experiment: ").strip()
    if not experiment:
        print("[ERROR] No experiment provided. Exiting.")
        sys.exit(1)

    # ── Handle dry run mode ──
    if args.dry_run:
        perform_dry_run(experiment, args.max_papers)
        return

    print(f"\n[*] Experiment: {experiment}")
    has_llm = bool(DEEPSEEK_API_KEY)
    print(f"[*] LLM Mode : {'DeepSeek (' + MODEL + ')' if has_llm else 'Rule-based fallback (no API key)'}")
    print(f"[*] Sources  : Bohrium Science Navigator + arXiv")

    # ── Step 1: Generate search queries ──
    print("\n[1/4] Generating search queries...")
    queries = generate_search_queries(experiment)
    for i, q in enumerate(queries, 1):
        print(f"  Q{i}: {q}")

    # ── Step 2: Fetch papers from both sources ──
    print(f"\n[2/4] Fetching papers...")
    all_papers = []
    seen_ids = set()

    for query in queries:
        print(f"\n  [Bohrium] '{query}'")
        bohrium_papers = search_bohrium(query, max_results=args.max_papers)
        print(f"    -> {len(bohrium_papers)} paper(s) found")

        print(f"  [arXiv  ] '{query}'")
        arxiv_papers = search_arxiv(query, max_results=args.max_papers)
        print(f"    -> {len(arxiv_papers)} paper(s) found")

        for p in bohrium_papers + arxiv_papers:
            pid = p["id"]
            if pid not in seen_ids:
                seen_ids.add(pid)
                all_papers.append(p)

    print(f"\n  [+] Total unique papers: {len(all_papers)}")

    # Save raw papers cache
    slug = re.sub(r'[^\w]', '_', experiment[:40]).strip('_').lower()
    cache_path = os.path.join(PAPER_DIR, f"{slug}_papers.json")
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(all_papers, f, indent=2, ensure_ascii=False)

    # ── Step 3: Generate hypotheses ──
    print("\n[3/4] Generating hypotheses...")
    hypotheses = []

    if has_llm:
        print("  [>] Calling DeepSeek LLM...")
        llm_response = generate_hypotheses_llm(experiment, all_papers)
        if llm_response:
            try:
                match = re.search(r'\{.*\}', llm_response, re.DOTALL)
                if match:
                    parsed = json.loads(match.group())
                    hypotheses = parsed.get("hypotheses", [])
                    print(f"  [OK] LLM generated {len(hypotheses)} hypotheses")
            except Exception as e:
                print(f"  [WARN] Failed to parse LLM JSON: {e}")
                print("  [>] Falling back to rule-based generation...")

    if not hypotheses:
        hypotheses = generate_hypotheses_fallback(experiment, all_papers)
        print(f"  [OK] Rule-based generated {len(hypotheses)} hypotheses")

    # ── Step 4: Save and display ──
    print("\n[4/4] Saving outputs...")
    json_path, txt_path, report = save_outputs(experiment, all_papers, hypotheses)
    print(f"  JSON   : {json_path}")
    print(f"  Report : {txt_path}")
    print(f"  Papers : {cache_path}")

    print("\n" + "=" * 72)
    print(report)


if __name__ == "__main__":
    main()
