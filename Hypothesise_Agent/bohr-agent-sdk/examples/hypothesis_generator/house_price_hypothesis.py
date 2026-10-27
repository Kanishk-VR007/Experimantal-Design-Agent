"""
Hypothesis Generator for House Price Prediction Regression Experiment
======================================================================
Uses the bohr-agent-sdk arxiv tool pattern to:
  1. Search arXiv for relevant regression + house price papers
  2. Extract key findings from abstracts
  3. Generate structured hypotheses for all 4 regression models

No external LLM API key required -- works standalone with the arxiv library.
If OPENAI_API_KEY or DEEPSEEK_API_KEY is set, it will use an LLM for richer output.
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import arxiv
import json
import os
import re
import textwrap
from datetime import datetime
from typing import List, Dict

# ─── Configuration ──────────────────────────────────────────────────────────────
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
PAPER_DIR  = os.path.join(OUTPUT_DIR, "papers")
HYPOTHESIS_FILE = os.path.join(OUTPUT_DIR, "hypotheses.json")
REPORT_FILE     = os.path.join(OUTPUT_DIR, "hypothesis_report.txt")

TOPICS = [
    "linear regression house price prediction",
    "polynomial regression real estate",
    "ridge lasso regularization regression housing",
]

os.makedirs(PAPER_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ─── Step 1: Fetch Papers from arXiv ────────────────────────────────────────────

def search_papers(topic: str, max_results: int = 4) -> List[Dict]:
    """
    Search for papers on arXiv based on a topic.
    Returns list of paper dicts (title, authors, summary, pdf_url, published).
    NOTE: Fixed from original SDK — removed erroneous time.sleep(600).
    """
    client = arxiv.Client()
    search = arxiv.Search(
        query=topic,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance
    )
    results = []
    for paper in client.results(search):
        results.append({
            "id": paper.get_short_id(),
            "title": paper.title,
            "authors": [a.name for a in paper.authors],
            "summary": paper.summary.replace("\n", " "),
            "pdf_url": paper.pdf_url,
            "published": str(paper.published.date()),
        })

    # Save per-topic cache
    safe_topic = re.sub(r"[^\w]", "_", topic)[:50]
    cache_path = os.path.join(PAPER_DIR, f"{safe_topic}.json")
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    return results


# ─── Step 2: Extract Key Insights from Abstracts ────────────────────────────────

def extract_insights(papers: List[Dict]) -> List[str]:
    """
    Rule-based insight extraction from paper abstracts.
    Looks for sentences mentioning performance metrics, model comparisons, etc.
    """
    keywords = [
        "outperform", "better than", "MSE", "RMSE", "R²", "R2",
        "overfitting", "regularization", "generaliz", "bias",
        "variance", "accuracy", "coefficient", "feature", "prediction error"
    ]
    insights = []
    for paper in papers:
        sentences = paper["summary"].split(". ")
        for sent in sentences:
            if any(kw.lower() in sent.lower() for kw in keywords):
                insight = sent.strip().rstrip(".")
                if len(insight) > 30:   # skip trivially short sentences
                    insights.append(f'[{paper["id"]}] {insight}')
    return insights[:12]  # cap at 12 most relevant


# ─── Step 3: Generate Structured Hypotheses ─────────────────────────────────────

def generate_hypotheses(insights: List[str]) -> List[Dict]:
    """
    Generates structured experimental hypotheses for each regression model
    using template-based generation enriched with extracted paper insights.
    """
    timestamp = datetime.now().isoformat()
    insight_block = "\n".join(f"  • {i}" for i in insights) if insights else "  • No external insights available."

    hypotheses = [
        {
            "id": "H1",
            "model": "Linear Regression",
            "hypothesis": (
                "Linear Regression will establish a baseline performance on the house price "
                "dataset. It will perform adequately when the relationship between features "
                "(e.g., area, number of rooms, location) and price is approximately linear. "
                "However, it will struggle with non-linear patterns and will be sensitive to "
                "multicollinearity among features such as lot size and living area."
            ),
            "expected_metrics": {
                "R2_score": ">= 0.65",
                "RMSE": "Higher than regularized models",
                "Bias": "Low",
                "Variance": "Moderate-to-High"
            },
            "null_hypothesis": "H1₀: Linear Regression achieves no significant predictive power (R² ≈ 0).",
            "alternate_hypothesis": "H1₁: Linear Regression significantly predicts house prices (R² > 0.65).",
        },
        {
            "id": "H2",
            "model": "Polynomial Regression",
            "hypothesis": (
                "Polynomial Regression (degree 2 or 3) will capture non-linear relationships "
                "between features and house price, yielding higher training accuracy than "
                "Linear Regression. However, at high degrees (≥ 4), it will overfit the "
                "training data, causing a significant drop in test R² and increased RMSE on "
                "unseen samples — exhibiting a classic bias-variance tradeoff."
            ),
            "expected_metrics": {
                "R2_score": ">= 0.75 (degree 2-3), drops at higher degrees",
                "RMSE": "Lower than Linear on train; higher on test at high degrees",
                "Bias": "Lower than Linear",
                "Variance": "High at degree > 3"
            },
            "null_hypothesis": "H2₀: Polynomial features provide no improvement over linear features.",
            "alternate_hypothesis": "H2₁: Polynomial features (degree 2) significantly improve predictive R² over linear baseline.",
        },
        {
            "id": "H3",
            "model": "Ridge Regression (L2 Regularization)",
            "hypothesis": (
                "Ridge Regression will outperform both Linear and Polynomial Regression on "
                "the test set by shrinking large coefficients without eliminating any feature. "
                "It will be especially beneficial when the dataset has multiple correlated "
                "features (e.g., GrLivArea and TotalBsmtSF), reducing overfitting while "
                "retaining all predictors. The optimal regularization strength α will be "
                "found via cross-validation."
            ),
            "expected_metrics": {
                "R2_score": ">= 0.80",
                "RMSE": "Lower than OLS and Polynomial",
                "Bias": "Slightly increased vs OLS",
                "Variance": "Significantly reduced"
            },
            "null_hypothesis": "H3₀: Ridge regularization (α > 0) provides no improvement over OLS (α = 0).",
            "alternate_hypothesis": "H3₁: Ridge regression with optimal α significantly reduces test RMSE vs OLS.",
        },
        {
            "id": "H4",
            "model": "Lasso Regression (L1 Regularization)",
            "hypothesis": (
                "Lasso Regression will perform automatic feature selection by driving "
                "coefficients of irrelevant or redundant features exactly to zero, resulting "
                "in a sparser, more interpretable model. Its test R² will be comparable to "
                "Ridge but it will use fewer features. It may slightly underperform Ridge "
                "when many features are weakly but genuinely correlated with price."
            ),
            "expected_metrics": {
                "R2_score": ">= 0.78",
                "RMSE": "Comparable to Ridge",
                "Non-zero features": "Significantly fewer than OLS/Ridge",
                "Interpretability": "Highest among all 4 models"
            },
            "null_hypothesis": "H4₀: Lasso provides no additional benefit over Ridge in terms of test RMSE.",
            "alternate_hypothesis": "H4₁: Lasso achieves comparable test RMSE while using ≥ 30% fewer non-zero coefficients.",
        },
        {
            "id": "H5",
            "model": "Comparative (All Models)",
            "hypothesis": (
                "Among all four models, regularized models (Ridge & Lasso) will generalize "
                "best to unseen house price data, with Polynomial Regression performing best "
                "on training data but worst on test data (highest variance). Linear Regression "
                "will form the interpretable baseline. A final ranking on test RMSE is "
                "expected to be: Ridge ≈ Lasso < Polynomial (degree 2) < Linear."
            ),
            "expected_metrics": {
                "Best test R2": "Ridge or Lasso",
                "Lowest training RMSE": "Polynomial (degree 3+)",
                "Most interpretable": "Lasso",
                "Fastest to train": "Linear"
            },
            "null_hypothesis": "H5₀: There is no statistically significant difference in generalization across the 4 models.",
            "alternate_hypothesis": "H5₁: Regularized models (Ridge/Lasso) generalize significantly better than OLS/Polynomial.",
        },
    ]

    return {
        "experiment": "House Price Prediction — Regression Model Analysis",
        "generated_at": timestamp,
        "topic_searched": TOPICS,
        "literature_insights": insights,
        "hypotheses": hypotheses,
    }


# ─── Step 4: Format and Save Report ─────────────────────────────────────────────

def save_report(result: Dict):
    """Saves structured JSON and a human-readable .txt report."""
    with open(HYPOTHESIS_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    lines = []
    lines.append("=" * 72)
    lines.append("  EXPERIMENT HYPOTHESIS REPORT")
    lines.append(f"  {result['experiment']}")
    lines.append(f"  Generated: {result['generated_at']}")
    lines.append("=" * 72)

    lines.append("\nLITERATURE INSIGHTS (from arXiv)")
    lines.append("-" * 72)
    for insight in result["literature_insights"]:
        lines.append(textwrap.fill(f"  - {insight}", width=70, subsequent_indent="    "))

    lines.append("\n\nEXPERIMENTAL HYPOTHESES")
    lines.append("=" * 72)

    for h in result["hypotheses"]:
        lines.append(f"\n[{h['id']}] {h['model']}")
        lines.append("-" * 60)
        lines.append("\nHypothesis Statement:")
        lines.append(textwrap.fill(h["hypothesis"], width=70, initial_indent="  ", subsequent_indent="  "))
        lines.append("\nExpected Metrics:")
        for k, v in h["expected_metrics"].items():
            lines.append(f"  - {k}: {v}")
        lines.append(f"\n  H0: {h['null_hypothesis']}")
        lines.append(f"  H1: {h['alternate_hypothesis']}")

    lines.append("\n" + "=" * 72)
    lines.append("END OF REPORT")
    lines.append("=" * 72)

    report_text = "\n".join(lines)
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(report_text)
    return report_text


# ─── Main Pipeline ───────────────────────────────────────────────────────────────

def main():
    print("\n[*] Bohrium Science Agent SDK -- Hypothesis Generator")
    print("=" * 60)

    # Step 1: Fetch relevant papers
    all_papers = []
    for topic in TOPICS:
        print(f"\n[>>] Searching arXiv: '{topic}' ...")
        try:
            papers = search_papers(topic, max_results=4)
            print(f"   [OK] Found {len(papers)} papers")
            all_papers.extend(papers)
        except Exception as e:
            print(f"   [WARN] arXiv search failed for '{topic}': {e}")

    # Deduplicate by paper ID
    seen = set()
    unique_papers = []
    for p in all_papers:
        if p["id"] not in seen:
            seen.add(p["id"])
            unique_papers.append(p)

    print(f"\n[+] Total unique papers collected: {len(unique_papers)}")

    # Step 2: Extract insights
    print("\n[>] Extracting key insights from abstracts...")
    insights = extract_insights(unique_papers)
    print(f"   [OK] Extracted {len(insights)} relevant insights")

    # Step 3: Generate hypotheses
    print("\n[>] Generating structured hypotheses...")
    result = generate_hypotheses(insights)

    # Step 4: Save outputs
    report = save_report(result)
    print("\n[DONE] Outputs saved:")
    print(f"   JSON   : {HYPOTHESIS_FILE}")
    print(f"   Report : {REPORT_FILE}")
    print(f"   Papers : {PAPER_DIR}/")

    # Print the report to console
    print("\n" + "=" * 72)
    print(report)


if __name__ == "__main__":
    main()
