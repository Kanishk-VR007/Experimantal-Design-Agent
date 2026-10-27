# Hypothesise Agent: System Blueprint & AI Architecture

This document provides a comprehensive blueprint of the **Hypothesise Agent**, detailing its multi-layer architecture, self-learning capabilities, AI models used, and external API integrations.

---

## 1. System Overview & Name of the AI

- **Name of the AI System:** Hypothesise Agent
- **Core Purpose:** An AI-powered scientific research and experimentation platform. It automates hypothesis generation, literature review, experimental design, and runs domain-specific mathematical simulations.

---

## 2. Complete Layer Blueprint & Models Used

The system is structured into a 7-layer architecture. No traditional neural network weight "fine-tuning" (like LoRA) is performed. Instead, each layer is optimized through **prompt engineering**, **strict temperature controls**, and **dynamic memory retrieval weighting**.

| Layer | Component Name | Technology / Model Used | Fine-tuning / Optimization Strategy |
| :--- | :--- | :--- | :--- |
| **L1** | **Hypothesis Agent** | **DeepSeek** (`deepseek-chat`) via LiteLLM | Optimized with `temperature=0.4` and `frequency_penalty=0.1`. Extracts structured hypotheses from plain text and papers. |
| **L2** | **Experimental Design Agent** | **Ollama** (`llama3.2` / `llama3` locally) | Optimized with `temperature=0.3`, `repeat_penalty=1.1`, and a 180s timeout to enforce rigorous scientific protocol generation without hallucinations. |
| **L3** | **Simulation Agent** | **NumPy/SciPy** (Deterministic math) + **Claude / Ollama** | Uses deterministic engines (Chem, Bio, Physics, etc.) by default. Falls back to **Claude** (`claude-sonnet-4-20250514`) or **Ollama** for general domains. |
| **L4** | **Backend API** | **FastAPI** & **Uvicorn** | Orchestrates Server-Sent Events (SSE) to stream Ollama tokens to the UI in real-time. |
| **L5** | **Frontend UI** | **React 18**, **Vite**, **Plotly.js** | Renders real-time markdown streams and dynamic mathematical charts (scatter, bar, line). |
| **L6** | **Memory Agent** | **Claude** (`claude-sonnet-4-20250514`) via **LangChain** | Uses Claude at `temperature=0` to analyze pipeline metrics and generate deterministic improvement plans. |
| **L7** | **Vector Store** | **ChromaDB** (Local) / **Pinecone** (Cloud) | Stores feedback-weighted embeddings (chat history, experiment results, hypothesis procedures). |

---

## 3. LangChain Integration & Working Mechanism

### What type of LangChain is used?
The project utilizes **LangChain Anthropic** (`langchain_anthropic.ChatAnthropic`), specifically interfacing with the Anthropic Claude API.

### How it works:
LangChain is primarily used in the **L6 Memory Agent** (`improvement_engine.py`) to give the AI self-reflection and auto-correction capabilities. 
1. **Data Aggregation:** The system aggregates metrics (e.g., hypothesis scores, procedure accuracy, simulation confidence) from a local SQLite database (`memory_feedback.db`).
2. **Context Building:** It constructs a massive prompt containing pipeline accuracy trends, the weakest layer identifier, retrieval weights, and historical memory feedback scores.
3. **LangChain Invocation:** It invokes `ChatAnthropic(model="claude-sonnet-4-20250514")` to parse these complex analytics.
4. **Structured Output:** Claude outputs a strict JSON plan detailing exactly what actions to take (e.g., *prompt_improvement*, *retrieval_tuning*, *data_augmentation*) to fix underperforming layers.

*(Note: If LangChain or the Anthropic API is unavailable, the system has a graceful fallback to a hardcoded rule-based improvement engine.)*

---

## 4. Self-Learning Capability

The Hypothesise Agent is a **self-improving system** that learns from past experiments without requiring traditional model re-training. This is achieved through the **Memory Agent (L6)**:

1. **Feedback Loop:** Every time an experiment is designed and simulated, confidence scores and user feedback are recorded in SQLite.
2. **Dynamic Retrieval Reweighting (EMA):**
   The agent calculates an Exponential Moving Average for retrieval weights. 
   *Formula:* `new_weight = 0.6 * old_weight + 0.4 * (0.2 + avg_score * 1.8)`
   - *Result:* High-scoring "good" memories are surfaced more frequently in future experiments, while poor approaches are suppressed.
3. **Memory Pruning:** The system actively scans the vector database (ChromaDB) and permanently deletes (prunes) memory items whose average feedback score drops below a configured threshold (`0.25`).
4. **Continuous Improvement Plans:** The LangChain engine analyzes which layer (e.g., L2 Experimental Design) is failing the most and outputs automated plans to adjust system prompts and weights.

---

## 5. External APIs Used

The system heavily leverages external APIs to prevent hallucinations and ground the AI in actual scientific data:

1. **Bohrium Science Navigator API:** Used to retrieve highly accurate, domain-specific scientific literature and research papers.
2. **arXiv API:** Fetches open-access research papers (mostly Physics, CS, and Math) by querying the arXiv Atom XML endpoints.
3. **Semantic Scholar API:** Acts as a robust fallback to fetch paper metadata, abstracts, and citation counts for general research topics.
4. **DeepSeek API:** Powers the L1 Hypothesis generation phase.
5. **Anthropic API (Claude):** Powers the self-reflection LangChain engine and serves as the highest-tier fallback for complex mathematical simulations.
6. **Ollama API (Local HTTP):** While local, the backend interfaces with the Ollama REST API (`/api/generate` and `/api/tags`) to stream local LLM inferences.
