"""
Token Filtering, Stop-Word Removal & Ollama Qwen Prompt Refiner
===============================================================
Two-stage pre-processing pipeline before sending context to LM Studio's
`oreal-deepseek-r1-distill-qwen-7b`:
  1. Deterministic NLP token filtering & scientific stop-word removal
     (strips filler/boilerplate/citations while preserving units, formulas,
     chemical formulas, numbers, and scientific causal operators).
  2. Prompt & variable refinement via local Ollama `qwen3:4b-thinking`
     producing clean, structured scientific specifications and context.
"""

import os
import re
import json
import math
import logging
from collections import Counter
from typing import Dict, Any, List, Tuple, Optional, Literal
import requests
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(BASE_DIR, ".env"))

logger = logging.getLogger(__name__)

# Refinement parse-path logging must be visible even when the host process
# (script, pytest, uvicorn) never configures the logging module.
logger.setLevel(logging.INFO)
if not logging.getLogger().handlers and not logger.handlers:
    _console = logging.StreamHandler()
    _console.setFormatter(logging.Formatter("%(levelname)s [prompt_refiner] %(message)s"))
    logger.addHandler(_console)
    logger.propagate = False

# Canonical experiment domains understood by the downstream routing & simulation engines.
VALID_DOMAINS: Tuple[str, ...] = (
    "physics",
    "chemistry",
    "biology",
    "civil_engineering",
    "mechanical_engineering",
    "electronics",
    "computer_science",
    "general",
)

DomainLiteral = Literal[
    "physics",
    "chemistry",
    "biology",
    "civil_engineering",
    "mechanical_engineering",
    "electronics",
    "computer_science",
    "general",
]

# Free-form labels small local models emit -> canonical domain keys.
DOMAIN_ALIASES: Dict[str, str] = {
    "physical": "physics",
    "phys": "physics",
    "physic": "physics",
    "chem": "chemistry",
    "chemical": "chemistry",
    "chemestry": "chemistry",
    "bio": "biology",
    "biological": "biology",
    "life_science": "biology",
    "civil": "civil_engineering",
    "structural_engineering": "civil_engineering",
    "mechanical": "mechanical_engineering",
    "mechanics": "mechanical_engineering",
    "mech_engineering": "mechanical_engineering",
    "electronic": "electronics",
    "electrical": "electronics",
    "electrical_engineering": "electronics",
    "electronic_engineering": "electronics",
    "ee": "electronics",
    "cs": "computer_science",
    "comp_sci": "computer_science",
    "computerscience": "computer_science",
    "computer_sciences": "computer_science",
    "ml": "computer_science",
    "machine_learning": "computer_science",
    "data_science": "computer_science",
    "general_science": "general",
    "other": "general",
    "unknown": "general",
    "none": "general",
    "n/a": "general",
}

# Standard high-frequency English stop words minus scientific operators
# (we intentionally KEEP: if, then, when, while, not, no, nor, above, below,
#  under, over, between, against, more, less, increase, decrease, same, per, vs).
STOP_WORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "of",
    "with", "by", "from", "as", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "shall", "should", "may", "might", "must", "can", "could", "this", "that",
    "these", "those", "it", "its", "they", "them", "their", "we", "our", "us",
    "you", "your", "i", "me", "my", "he", "she", "him", "her", "his", "who",
    "whom", "which", "what", "whose", "where", "why", "how", "all", "any",
    "both", "each", "few", "many", "most", "other", "some", "such", "only",
    "own", "so", "than", "too", "very", "just", "also", "even", "here", "there",
    "about", "into", "through", "during", "before", "after", "up", "down",
    "out", "off", "again", "further", "once", "such", "etc", "via", "using",
    "based", "shown", "show", "shows", "present", "presents", "study", "studies",
    "paper", "propose", "proposes", "proposed", "approach", "method", "methods",
    "results", "result", "recent", "novel", "comprehensive", "survey", "overview",
    "however", "moreover", "therefore", "furthermore", "respectively", "significantly",
    "experiment", "experiments", "experimental", "investigate", "demonstrate",
})

# Boilerplate fragments common in paper abstracts
NOISE_PATTERNS = [
    r"https?://\S+",
    r"<[^>]+>",
    r"\[\s*\d+(?:\s*,\s*\d+)*\s*\]",
    r"\b(?:et\s+al\.?|fig\.?|eq\.?|copyright|arxiv)\b",
    r"©\s*\d{4}",
]


def clean_raw_text(text: str) -> str:
    """Remove URLs, HTML tags, citation brackets, and excessive whitespace."""
    if not text:
        return ""
    cleaned = text
    for pat in NOISE_PATTERNS:
        cleaned = re.sub(pat, " ", cleaned, flags=re.IGNORECASE)
    # Normalize unicode dashes / spaces while preserving scientific symbols & math
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def tokenize_scientific(text: str) -> List[str]:
    """
    Tokenize text while keeping numbers+units (1.5m, 9.81, 15kN/m, O(n^2), H2O) intact.
    """
    cleaned = clean_raw_text(text)
    if not cleaned:
        return []
    # Match formulas, chemical tokens, numeric+unit spans, or words
    pattern = r"[A-Za-z0-9]+(?:[._/\-\+\^][A-Za-z0-9]+)*|[=<>±×÷√πθαωμΩ°%]+"
    return re.findall(pattern, cleaned)


def filter_tokens(text: str) -> Dict[str, Any]:
    """
    Perform token filtering & stop-word removal on a scientific text string.
    Returns filtered tokens alongside transparent token-count audit statistics.
    """
    raw_tokens = tokenize_scientific(text)
    filtered: List[str] = []
    removed_stopwords = 0
    removed_noise = 0
    seen_lower = set()

    for tok in raw_tokens:
        low = tok.lower()
        # Drop pure single-char noise unless it is a valid variable/unit/operator
        if len(tok) == 1 and not (tok.isdigit() or tok in set("LmgtVTIRFpqxyn=+<>%°")):
            removed_noise += 1
            continue
        if low in STOP_WORDS:
            removed_stopwords += 1
            continue
        # Light redundancy trim on repeated non-numeric filler while keeping measurements
        is_numeric = any(ch.isdigit() for ch in tok)
        if not is_numeric and low in seen_lower and len(filtered) > 12:
            removed_noise += 1
            continue
        seen_lower.add(low)
        filtered.append(tok)

    raw_n = len(raw_tokens)
    filt_n = len(filtered)
    reduction_pct = round(((raw_n - filt_n) / raw_n) * 100.0, 1) if raw_n > 0 else 0.0

    return {
        "raw_token_count": raw_n,
        "filtered_token_count": filt_n,
        "removed_stopwords_count": removed_stopwords,
        "removed_noise_count": removed_noise,
        "reduction_pct": reduction_pct,
        "filtered_tokens": filtered,
        "filtered_text": " ".join(filtered),
    }


def filter_and_compress_context(topic: str, papers: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Filter tokens and remove stop words across user topic and retrieved literature.
    Scores and extracts high-signal sentences & scientific terms for downstream LLMs.
    """
    topic_stats = filter_tokens(topic)
    query_terms = {t.lower() for t in topic_stats["filtered_tokens"]}

    paper_raw_tokens = 0
    paper_filt_tokens = 0
    paper_stopwords = 0
    compressed_papers: List[str] = []
    keyword_counter: Counter = Counter()

    for tok in topic_stats["filtered_tokens"]:
        keyword_counter[tok] += 3  # Boost user topic terms

    for idx, p in enumerate(papers[:4], 1):
        title = str(p.get("title", "") or "")
        abstract = str(p.get("abstract") or p.get("summary") or "")
        combined_paper = f"{title}. {abstract}"
        p_stats = filter_tokens(combined_paper)

        paper_raw_tokens += p_stats["raw_token_count"]
        paper_filt_tokens += p_stats["filtered_token_count"]
        paper_stopwords += p_stats["removed_stopwords_count"]

        for tok in p_stats["filtered_tokens"]:
            if len(tok) > 2:
                keyword_counter[tok] += 1

        # Score sentences in abstract by relevance to topic + quantitative density
        sentences = re.split(r"(?<=[.!?])\s+", clean_raw_text(abstract))
        scored_sents: List[Tuple[float, str]] = []
        for s in sentences:
            if not s.strip():
                continue
            s_toks = {t.lower() for t in tokenize_scientific(s)}
            overlap = len(query_terms & s_toks)
            has_num = 1.5 if re.search(r"\d+(?:\.\d+)?", s) else 0.0
            scored_sents.append((overlap * 2.0 + has_num + min(len(s) / 200.0, 1.0), s))
        scored_sents.sort(key=lambda x: x[0], reverse=True)
        best_sent = " ".join(s for _, s in scored_sents[:2])

        t_clean = clean_raw_text(title)[:110]
        compressed_papers.append(
            f"[P{idx}] {t_clean} | Key tokens: {' '.join(p_stats['filtered_tokens'][:18])}"
            + (f" | Core finding: {best_sent[:220]}" if best_sent else "")
        )

    total_raw = topic_stats["raw_token_count"] + paper_raw_tokens
    total_filt = topic_stats["filtered_token_count"] + paper_filt_tokens
    total_stop = topic_stats["removed_stopwords_count"] + paper_stopwords
    overall_reduction = round(((total_raw - total_filt) / total_raw) * 100.0, 1) if total_raw > 0 else 0.0

    top_keywords = [k for k, _ in keyword_counter.most_common(18)]

    return {
        "topic_filtered": topic_stats["filtered_text"],
        "topic_tokens": topic_stats["filtered_tokens"],
        "compressed_papers": compressed_papers,
        "top_keywords": top_keywords,
        "stats": {
            "raw_token_count": total_raw,
            "filtered_token_count": total_filt,
            "removed_stopwords_count": total_stop,
            "reduction_pct": overall_reduction,
        },
    }


def _heuristic_refinement(topic: str, filtered_ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic scientific fallback if Ollama refinement server is unavailable."""
    low = topic.lower()
    domain = "general"
    exp_type = "general_experiment"
    equations: List[str] = []
    params: Dict[str, Any] = {}

    if any(w in low for w in ["strain gauge", "wheatstone", "load cell"]):
        domain = "mechanical_engineering"
        exp_type = "dynamic_custom"
        equations = ["delta_R = R0 * GF * strain", "V_out = V_ex * (GF * strain) / (4 + 2 * GF * strain)"]
        params = {"gauge_factor": 2.1, "nominal_resistance_ohm": 120.0, "excitation_voltage_V": 5.0}
    elif any(w in low for w in ["pendulum", "oscillat", "harmonic"]):
        domain = "physics"
        exp_type = "pendulum"
        equations = ["T = 2*pi*sqrt(L/g)", "d^2(theta)/dt^2 + (b/m)*d(theta)/dt + (g/L)*sin(theta) = 0"]
        m_len = re.search(r"(\d+(?:\.\d+)?)\s*(?:-|\s)?(?:m|meter|meters)\b", low)
        params = {"length_m": float(m_len.group(1)) if m_len else 1.5, "gravity": 9.81, "damping": 0.1, "angle_rad": 0.5}
    elif any(w in low for w in ["projectile", "trajectory", "ballistic", "launch"]):
        domain = "physics"
        exp_type = "projectile"
        equations = ["R = (v0^2 * sin(2*theta)) / g", "y(t) = v0*sin(theta)*t - 0.5*g*t^2"]
        params = {"initial_velocity_ms": 20.0, "launch_angle_deg": 45.0, "gravity": 9.81}
    elif any(w in low for w in ["nickel", "chlorine", "chlorium", "molecule", "h2o", "water", "ch4", "co2", "benzene", "bond", "chemistry", "titration", "reaction"]):
        domain = "chemistry"
        exp_type = "titration" if "titration" in low else ("dynamic_custom" if any(k in low for k in ["nickel", "chlorine", "chlorium", "reaction"]) else "molecular_geometry")
        equations = ["k = A * exp(-Ea / (R*T))", "C(t) = C0 * exp(-k * t)"]
        params = {"temperature_K": 323.15, "initial_concentration_M": 1.0, "activation_energy_kJ": 65.0, "pre_exponential_factor": 1e9}
    elif any(w in low for w in ["beam", "deflect", "span", "truss", "civil", "structural"]):
        domain = "civil_engineering"
        exp_type = "beam_analysis"
        equations = ["delta_max = 5*w*L^4 / (384*E*I)", "sigma_max = M_max * (h/2) / I"]
        params = {"span_m": 6.0, "load_kN_per_m": 15.0, "elastic_modulus_GPa": 200.0}
    elif any(w in low for w in ["gear", "spur", "pinion", "shaft", "torque", "thermo", "otto", "carnot"]):
        domain = "mechanical_engineering"
        exp_type = "gear_train"
        equations = ["omega_2 = -omega_1 * (N1 / N2)", "T_out = T_in * (N2 / N1) * eta"]
        params = {"teeth_driver": 20, "teeth_driven": 40, "rpm_input": 1500}
    elif any(w in low for w in ["arduino", "blink", "voltage divider", "rlc"]) or re.search(r"\bled\b", low):
        domain = "electronics"
        exp_type = "arduino_led"
        equations = ["V = I * R", "I_LED = (V_cc - V_f) / R"]
        params = {"supply_voltage_V": 5.0, "led_forward_voltage_V": 2.0, "led_current_mA": 20}
    elif any(w in low for w in ["cnn", "transformer", "lstm", "dropout", "neural", "classification", "cifar"]):
        domain = "computer_science"
        exp_type = "model_comparison"
        equations = ["L_CE = -sum(y_i * log(p_i))", "Accuracy = (TP + TN) / N"]
        params = {"epochs": 50, "learning_rate": 0.001}
    elif any(w in low for w in ["cell", "bacteria", "growth", "gene", "protein", "biology"]):
        domain = "biology"
        exp_type = "growth_curve"
        equations = ["dN/dt = r * N * (1 - N/K)"]
        params = {"growth_rate": 0.5, "carrying_capacity": 1e6}

    return {
        "domain": domain,
        "experiment_type": exp_type,
        "refined_objective": f"Quantitatively evaluate {topic} using controlled variables and statistical validation.",
        "parameters": params,
        "independent_vars": filtered_ctx["topic_tokens"][:3],
        "dependent_vars": ["primary measured response", "error residual"],
        "control_vars": ["ambient temperature", "measurement calibration", "trial replication count"],
        "equations": equations,
        "refined_prompt": (
            f"Design a rigorous scientific experiment investigating {filtered_ctx['topic_filtered']}. "
            f"Verify theoretical predictions with explicit parameter values, control groups, and 95% confidence statistical tests."
        ),
        "refiner_source": "deterministic_fallback",
    }


# ---------------------------------------------------------------------------
# Structured refinement contract: Qwen JSON -> Pydantic schema validation
# ---------------------------------------------------------------------------

_NUMERIC_PREFIX_RE = re.compile(r"^[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?")
_KEY_VALUE_RE = re.compile(r"([^,;:\n]+?)\s*[:=]\s*([^,;\n]+)")
_REFINEMENT_SIGNAL_KEYS = (
    "domain",
    "experiment_type",
    "refined_prompt",
    "refined_objective",
    "parameters",
    "equations",
    "independent_vars",
    "dependent_vars",
    "control_vars",
)


def _normalize_domain(value: Any) -> str:
    """Map any model-emitted domain label onto the canonical domain literal set."""
    text = str(value or "").strip().lower()
    text = re.sub(r"[\s\-/+&]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    if text in VALID_DOMAINS:
        return text
    if text in DOMAIN_ALIASES:
        return DOMAIN_ALIASES[text]
    # Loosen things like "applied physics" / "computational_chemistry".
    for canonical in VALID_DOMAINS:
        if canonical == "general":
            continue
        head = canonical.split("_")[0]
        if canonical in text or (len(head) >= 5 and head in text):
            return canonical
    return "general"


def _coerce_numeric(value: Any) -> Any:
    """Best-effort numeric coercion: '1.5 m' -> 1.5, '1e9' -> 1e9, 'TBD' -> 'TBD'."""
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, (list, tuple)):
        return [_coerce_numeric(item) for item in value]
    if isinstance(value, dict):
        return {str(k): _coerce_numeric(v) for k, v in value.items()}
    if not isinstance(value, str):
        return value

    text = re.sub(r"(?<=\d),(?=\d{3}(?:\D|$))", "", value.strip())
    if not text:
        return value
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        pass

    match = _NUMERIC_PREFIX_RE.match(text)
    if not match:
        return value
    try:
        number = float(match.group(0))
    except ValueError:
        return value
    if re.fullmatch(r"[-+]?\d+", match.group(0)):
        return int(number)
    return number


def _as_text(value: Any) -> str:
    """Flatten scalars/containers into a single trimmed string field."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (list, tuple)):
        return "; ".join(part for part in (_as_text(item) for item in value) if part)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    return str(value).strip()


def _as_list_item(value: Any) -> str:
    """Reduce a variable/equation list element (str or {'name': ...}) to a string."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip().strip('"\'')
    if isinstance(value, dict):
        for key in ("name", "variable", "symbol", "equation", "value", "description"):
            if value.get(key) not in (None, ""):
                return _as_text(value[key])
        return _as_text(value)
    return _as_text(value).strip('"\'')


def _split_str_list(text: str, split_commas: bool = True) -> List[str]:
    """Split one string on semicolons / newlines / bullets (optionally commas too)."""
    text = _as_text(text).strip().strip("[]")
    if not text:
        return []
    items: List[str] = []
    for chunk in re.split(r"[;\n]+", text):
        chunk = re.sub(r"^\s*(?:[-*\u2022]|\d+[.)])\s+", "", chunk).strip()
        if not chunk:
            continue
        if split_commas:
            items.extend(part.strip() for part in re.split(r",", chunk) if part.strip())
        else:
            items.append(chunk)
    return [item.strip().strip('"\'') for item in items if item.strip()]


def _as_str_list(value: Any, split_commas: bool = True) -> List[str]:
    """Coerce comma/semicolon/newline/bullet separated strings and lists into List[str]."""
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        items: List[str] = []
        for entry in value:
            if isinstance(entry, str):
                items.extend(_split_str_list(entry, split_commas))
            else:
                text = _as_list_item(entry)
                if text:
                    items.append(text)
        return items
    if isinstance(value, dict):
        return [item for item in (_as_list_item(entry) for entry in value.values()) if item]
    return _split_str_list(value, split_commas)


def _parse_key_value_pairs(text: str) -> Dict[str, Any]:
    """Parse 'k: v, k2 = v2' style parameter dumps into a mapping."""
    pairs: Dict[str, Any] = {}
    for raw_key, raw_value in _KEY_VALUE_RE.findall(text or ""):
        key = raw_key.strip().strip('"\'')
        if key:
            pairs[key] = raw_value.strip()
    return pairs


def _as_parameters(value: Any) -> Dict[str, Any]:
    """Coerce model parameter payloads into Dict[str, Any] with numeric values where possible."""
    if value is None:
        return {}
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return {}
        try:
            value = json.loads(_strip_model_artifacts(text))
        except (json.JSONDecodeError, ValueError):
            value = _parse_key_value_pairs(text)
    if isinstance(value, (list, tuple)):
        flattened: Dict[str, Any] = {}
        for entry in value:
            if isinstance(entry, dict):
                name = entry.get("name") or entry.get("parameter") or entry.get("key") or entry.get("symbol")
                raw_value = entry.get("value", entry.get("baseline", entry.get("default")))
                if _as_text(name) and raw_value is not None:
                    flattened[_as_text(name)] = raw_value
            elif isinstance(entry, str):
                flattened.update(_parse_key_value_pairs(entry))
        value = flattened
    if not isinstance(value, dict):
        return {}

    cleaned: Dict[str, Any] = {}
    for raw_key, raw_value in value.items():
        name = _as_text(raw_key).strip('"\'')
        if not name or raw_value is None:
            continue
        # Collapse single-item containers: {"length_m": [1.5]} -> {"length_m": 1.5}
        if isinstance(raw_value, (list, tuple)) and len(raw_value) == 1:
            raw_value = raw_value[0]
        cleaned[name] = _coerce_numeric(raw_value)
    return cleaned


class RefinementSchema(BaseModel):
    """
    Validated shape of the Qwen prompt-refinement payload.

    Every field carries a safe default (and lenient pre-validators) so partial
    model responses still validate instead of rejecting the whole refinement.
    """

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    domain: DomainLiteral = "general"
    experiment_type: str = "general_experiment"
    refined_objective: str = ""
    parameters: Dict[str, Any] = Field(default_factory=dict)
    independent_vars: List[str] = Field(default_factory=list)
    dependent_vars: List[str] = Field(default_factory=list)
    control_vars: List[str] = Field(default_factory=list)
    equations: List[str] = Field(default_factory=list)
    refined_prompt: str = ""

    @field_validator("domain", mode="before")
    @classmethod
    def _validate_domain(cls, value: Any) -> str:
        return _normalize_domain(value)

    @field_validator("experiment_type", "refined_objective", "refined_prompt", mode="before")
    @classmethod
    def _validate_text(cls, value: Any) -> str:
        return _as_text(value)

    @field_validator("parameters", mode="before")
    @classmethod
    def _validate_parameters(cls, value: Any) -> Dict[str, Any]:
        return _as_parameters(value)

    @field_validator("independent_vars", "dependent_vars", "control_vars", mode="before")
    @classmethod
    def _validate_var_lists(cls, value: Any) -> List[str]:
        return _as_str_list(value, split_commas=True)

    @field_validator("equations", mode="before")
    @classmethod
    def _validate_equations(cls, value: Any) -> List[str]:
        return _as_str_list(value, split_commas=False)


def _validate_refinement_payload(
    payload: Dict[str, Any],
    base: Dict[str, Any],
) -> Tuple[Dict[str, Any], List[str]]:
    """
    Run a parsed refinement dict through RefinementSchema.

    Missing/empty fields are back-filled from the deterministic baseline, and any
    field that still fails validation falls back to its schema default so a
    single malformed value never discards an otherwise usable refinement.
    """
    candidate: Dict[str, Any] = dict(base or {})
    for key, value in (payload or {}).items():
        if value is None:
            continue
        if isinstance(value, (str, list, dict, tuple, set)) and len(value) == 0:
            continue
        candidate[key] = value

    defaulted: List[str] = []
    try:
        validated = RefinementSchema.model_validate(candidate).model_dump()
    except ValidationError as exc:
        logger.warning(
            "Refinement schema validation failed (%s issue(s)); retrying field-by-field",
            exc.error_count(),
        )
        validated = {}
        for name, field_info in RefinementSchema.model_fields.items():
            try:
                single = RefinementSchema.model_validate({name: candidate.get(name)})
                validated[name] = getattr(single, name)
            except ValidationError:
                defaulted.append(name)
                if name in (base or {}):
                    validated[name] = base[name]
                else:
                    validated[name] = field_info.get_default(call_default_factory=True)

    merged = dict(candidate)
    merged.update(validated)
    # Downstream simulation engines require a numeric dict of baseline parameters.
    if not isinstance(merged.get("parameters"), dict):
        merged["parameters"] = dict((base or {}).get("parameters") or {})
    return merged, defaulted


def _strip_model_artifacts(text: str) -> str:
    """Drop Qwen thinking blocks and Markdown code fences from a model response."""
    if not text:
        return ""
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"</?think>", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"```[a-zA-Z0-9_+-]*", "", cleaned)
    return cleaned.strip()


def _try_decode_json(text: str) -> Optional[Dict[str, Any]]:
    """Decode a dict from text that starts with (or is) a JSON object."""
    candidate = (text or "").strip()
    if not candidate:
        return None
    try:
        parsed = json.loads(candidate)
        if isinstance(parsed, dict):
            return parsed
    except (json.JSONDecodeError, ValueError):
        pass
    try:
        parsed, _ = json.JSONDecoder().raw_decode(candidate)
        if isinstance(parsed, dict):
            return parsed
    except (json.JSONDecodeError, ValueError):
        pass
    return None


def _iter_embedded_json_objects(text: str) -> List[str]:
    """Yield balanced {...} spans found anywhere in free text (string-aware scan)."""
    spans: List[str] = []
    depth = 0
    start = -1
    in_string = False
    escaped = False
    for index, char in enumerate(text or ""):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            if depth == 0:
                start = index
            depth += 1
        elif char == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and start >= 0:
                    spans.append(text[start:index + 1])
                    start = -1
    return spans


def _looks_like_refinement(payload: Optional[Dict[str, Any]]) -> bool:
    """True when a decoded dict actually carries refinement content (not a stray fragment)."""
    if not isinstance(payload, dict) or not payload:
        return False
    return any(payload.get(key) for key in _REFINEMENT_SIGNAL_KEYS)


def _parse_refinement_json(raw_text: str) -> Tuple[Optional[Dict[str, Any]], str]:
    """
    Multi-path parser for Qwen refinement output.

    Path order (first success wins):
      1. ``direct_json``            - the response is already a complete JSON object.
      2. ``prefill_reconstruction`` - the response is only the tail after the
         assistant prefill ``{"domain": "`` and must be re-assembled.
      3. ``embedded_json_extraction`` - a complete object hides inside prose/code fences.
    """
    raw = (raw_text or "").strip()
    if not raw:
        return None, "empty_response"

    cleaned = _strip_model_artifacts(raw)
    if not cleaned:
        return None, "empty_response"

    # 1. Complete JSON object already present in the response.
    direct = _try_decode_json(cleaned)
    if _looks_like_refinement(direct):
        return direct, "direct_json"

    # 2. Assistant-prefill tail reconstruction (the historical behaviour).
    for variant in ('{"domain": "' + cleaned, '{"domain": ' + cleaned):
        reconstructed = _strip_model_artifacts(variant)
        parsed = _try_decode_json(reconstructed)
        if _looks_like_refinement(parsed):
            return parsed, "prefill_reconstruction"

    # 3. A complete object embedded in surrounding text / code fences.
    best: Optional[Dict[str, Any]] = None
    for span in _iter_embedded_json_objects(cleaned):
        parsed = _try_decode_json(span)
        if not _looks_like_refinement(parsed):
            continue
        if best is None or len(parsed) > len(best):
            best = parsed
    if best is not None:
        return best, "embedded_json_extraction"

    logger.info("Refinement JSON parse failed on all paths (response head: %r)", cleaned[:120])
    return None, "unparsed"


def _attach_filtering_context(
    payload: Dict[str, Any],
    filtered_ctx: Dict[str, Any],
    parse_path: str,
) -> Dict[str, Any]:
    """Attach token-filtering audit stats and provenance to a refinement payload."""
    payload["token_filtering"] = filtered_ctx["stats"]
    payload["compressed_papers"] = filtered_ctx["compressed_papers"]
    payload["top_keywords"] = filtered_ctx["top_keywords"]
    payload["refiner_parse_path"] = parse_path
    return payload


def refine_prompt_with_ollama_qwen(
    topic: str,
    papers: List[Dict[str, Any]],
    timeout: int = 25,
) -> Dict[str, Any]:
    """
    Stage 1 + Stage 2 Pipeline:
      1. Token filtering & stop-word removal across topic + literature.
      2. Prompt refinement using Ollama `qwen3:4b-thinking` (assistant JSON prefill + `think: False`).
    Returns the refined structured context dict along with token compression stats.
    """
    filtered_ctx = filter_and_compress_context(topic, papers)
    ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
    qwen_model = os.getenv("OLLAMA_REFINER_MODEL") or os.getenv("OLLAMA_MODEL", "qwen3:4b-thinking")

    # Select an available Qwen model if configured tag is missing
    try:
        tags_resp = requests.get(f"{ollama_url}/api/tags", timeout=3)
        if tags_resp.status_code == 200:
            avail = [m.get("name", "") for m in tags_resp.json().get("models", []) if m.get("name")]
            if qwen_model not in avail:
                qwen_candidates = [m for m in avail if "qwen" in m.lower()]
                if qwen_candidates:
                    qwen_model = qwen_candidates[0]
                elif avail:
                    qwen_model = avail[0]
    except Exception:
        fallback = _heuristic_refinement(topic, filtered_ctx)
        logger.warning("Ollama runtime unreachable at %s; using deterministic refinement", ollama_url)
        return _attach_filtering_context(fallback, filtered_ctx, "ollama_unavailable")

    system_msg = (
        "You are a Scientific Prompt Refinement Agent. Given stop-word-filtered scientific tokens "
        "and compressed paper signals, output strictly ONE valid JSON object with keys: "
        '"domain" (one of physics, chemistry, biology, civil_engineering, mechanical_engineering, electronics, computer_science, general), '
        '"experiment_type" (concise snake_case), '
        '"refined_objective" (1 precise testable scientific sentence), '
        '"parameters" (JSON object of explicit numeric parameter_name: value pairs with unit suffix), '
        '"independent_vars" (array of strings), '
        '"dependent_vars" (array of strings), '
        '"control_vars" (array of strings), '
        '"equations" (array of key governing formula strings), '
        '"refined_prompt" (concise dense instruction for DeepSeek-R1 to design the experiment). '
        "\nExamples of correct output:\n\n"
        'Physics example input: "pendulum oscillation period vs length"\n'
        '{"domain":"physics","experiment_type":"simple_pendulum","refined_objective":"Measure oscillation period T as a function of pendulum length L to verify T=2π√(L/g)","parameters":{"length_m":1.0,"gravity_m_s2":9.81,"mass_kg":0.5},"independent_vars":["length_m"],"dependent_vars":["period_s"],"control_vars":["mass_kg","air_resistance"],"equations":["T = 2*pi*sqrt(L/g)"],"refined_prompt":"Design a pendulum experiment varying length 0.2-2.0m, measuring period with photogate, 10 trials per length, compute g from T²∝L regression."}\n\n'
        'Chemistry example input: "rate of reaction between acid and carbonate"\n'
        '{"domain":"chemistry","experiment_type":"reaction_kinetics","refined_objective":"Determine reaction rate k for HCl + CaCO3 → CaCl2 + H2O + CO2 by measuring CO2 volume over time","parameters":{"concentration_M":1.0,"temperature_K":298,"mass_ite_g":5.0},"independent_vars":["concentration_M"],"dependent_vars":["reaction_rate_mol_per_s"],"control_vars":["temperature_K","particle_size"],"equations":["rate = k[HCl]^n","k = A*exp(-Ea/(R*T))"],"refined_prompt":"Design kinetics experiment: vary HCl concentration 0.5-2.0M, measure CO2 volume via gas syringe at 30s intervals, fit to rate law, determine order n and rate constant k."}\n\n'
        'CS example input: "binary search vs linear search performance"\n'
        '{"domain":"computer_science","experiment_type":"algorithm_complexity","refined_objective":"Compare time complexity of binary search O(log n) vs linear search O(n) across input sizes","parameters":{"min_array_size":100,"max_array_size":100000,"num_trials":50},"independent_vars":["array_size"],"dependent_vars":["search_time_ms"],"control_vars":["hardware","data_distribution"],"equations":["T_linear = O(n)","T_binary = O(log n)"],"refined_prompt":"Benchmark binary vs linear search: sorted arrays from 100 to 100000 elements, 50 random-target trials per size, measure wall-clock time, plot scaling curves, verify asymptotic complexity ratios."}\n'
        "\nEmit ONLY the single JSON object for the actual input below; never restate these examples."
    )

    lit_block = "\n".join(filtered_ctx["compressed_papers"][:3]) or "No external papers."
    user_msg = (
        f"Filtered Topic Tokens: {filtered_ctx['topic_filtered']}\n"
        f"Original Topic: {topic}\n"
        f"High-Signal Keywords: {', '.join(filtered_ctx['top_keywords'][:12])}\n"
        f"Filtered Literature:\n{lit_block}\n"
        "Output compact refinement JSON now."
    )

    parse_path = "not_attempted"
    try:
        resp = requests.post(
            f"{ollama_url}/api/chat",
            json={
                "model": qwen_model,
                "messages": [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg},
                    {"role": "assistant", "content": '{"domain": "'},
                ],
                "think": False,
                "stream": False,
                "options": {
                    "num_predict": 480,
                    "temperature": 0.1,
                    "stop": ["\n\n"],
                },
            },
            timeout=timeout,
        )
        if resp.status_code == 200:
            message = resp.json().get("message") or {}
            raw_tail = message.get("content") or message.get("thinking") or ""

            parsed, parse_path = _parse_refinement_json(raw_tail)
            if parsed:
                # Pydantic validation keeps partial/hallucinated responses usable:
                # invalid domains map to "general", bad fields fall back to the
                # deterministic baseline, and numeric parameters stay numeric.
                base = _heuristic_refinement(topic, filtered_ctx)
                refinement, defaulted_fields = _validate_refinement_payload(parsed, base)
                refinement["refiner_source"] = f"ollama:{qwen_model}"
                logger.info(
                    "Qwen refinement accepted via parse path '%s' (model=%s, domain=%s, defaulted_fields=%s)",
                    parse_path,
                    qwen_model,
                    refinement.get("domain"),
                    ", ".join(defaulted_fields) or "none",
                )
                return _attach_filtering_context(refinement, filtered_ctx, parse_path)

            logger.warning(
                "Qwen refinement JSON unusable (path=%s, head=%r); using deterministic refinement",
                parse_path,
                (raw_tail or "")[:120],
            )
        else:
            parse_path = f"http_{resp.status_code}"
            logger.warning("Ollama refinement returned HTTP %s; using deterministic refinement", resp.status_code)
    except Exception as e:
        parse_path = "ollama_error"
        logger.warning("Ollama Qwen prompt refinement failed (%s); using deterministic refinement", e)

    fallback = _heuristic_refinement(topic, filtered_ctx)
    return _attach_filtering_context(fallback, filtered_ctx, parse_path)


def build_deepseek_messages(topic: str, refinement: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Construct clean, high-precision system & user messages for LM Studio's
    `oreal-deepseek-r1-distill-qwen-7b` using the Qwen-refined prompt and
    stop-word-filtered context.
    """
    domain = refinement.get("domain", "general")
    exp_type = refinement.get("experiment_type", "experiment")
    params = refinement.get("parameters", {})
    equations = refinement.get("equations", [])
    ind_vars = refinement.get("independent_vars", [])
    dep_vars = refinement.get("dependent_vars", [])
    ctrl_vars = refinement.get("control_vars", [])
    lit_lines = "\n".join(refinement.get("compressed_papers", [])[:3]) or "None provided."
    keywords = ", ".join(refinement.get("top_keywords", [])[:12])

    # Domain-conditional scientific rigor requirements injected into the DeepSeek brief.
    domain_constraints = {
        "physics": "DOMAIN REQUIREMENTS: Include conservation laws (energy, momentum), dimensional analysis with SI units, governing differential equations, and error propagation formulas.",
        "chemistry": "DOMAIN REQUIREMENTS: Include balanced reaction equations, stoichiometric calculations, Arrhenius parameters where applicable, molar concentrations with units, and thermodynamic constraints (enthalpy, entropy, Gibbs free energy).",
        "computer_science": "DOMAIN REQUIREMENTS: Include computational complexity analysis (Big-O), algorithmic correctness conditions, specific dataset size/type specifications, convergence criteria for iterative methods, and reproducibility parameters (random seeds, hardware specs).",
        "biology": "DOMAIN REQUIREMENTS: Include sample size calculations (statistical power), biological controls (positive/negative), measurement precision for biological assays, and ethical considerations for living organisms.",
        "electronics": "DOMAIN REQUIREMENTS: Include circuit equations (Kirchhoff's laws, Ohm's law), component tolerances, frequency response analysis where applicable, and signal-to-noise ratio considerations.",
        "civil_engineering": "DOMAIN REQUIREMENTS: Include structural load calculations, safety factors, material property specifications (yield strength, elastic modulus), and relevant building code references.",
        "mechanical_engineering": "DOMAIN REQUIREMENTS: Include force/stress/strain analysis, material fatigue considerations, thermodynamic efficiency calculations, and tolerance specifications.",
    }
    domain_requirements = domain_constraints.get(domain, "")
    domain_block = f"{domain_requirements}\n\n" if domain_requirements else ""

    system_prompt = (
        "You are an expert Scientific Experimental Design Architect. "
        "Keep internal reasoning brief and focused. Output clean, publication-grade raw Markdown directly "
        "(do NOT wrap the output in ```markdown code fences). "
        "Your response MUST contain ALL 7 exact Markdown headings so downstream automated audit & simulation parsers extract every variable and statistical metric:\n"
        "## 1. HYPOTHESIS\n"
        "(Write a clear, quantitative 'If ... then ...' testable hypothesis stating expected values/formulas.)\n"
        "## 2. VARIABLES\n"
        "(List Independent Variable(s), Dependent Variable(s), Control Variable(s), and Confounding Variable(s) with exact numeric baselines and SI units.)\n"
        "## 3. EXPERIMENTAL DESIGN\n"
        "(Specify Design Type, Sample/Trial Size, Control Group, and Experimental Group conditions.)\n"
        "## 4. METHODOLOGY & PROCEDURES\n"
        "(List Apparatus/Materials and a numbered 5-step reproducible procedure with exact measurements.)\n"
        "## 5. DATA ANALYSIS PLAN\n"
        "(Specify quantitative metrics, statistical significance tests e.g. 95% confidence interval / regression / t-test, and error propagation checks.)\n"
        "## 6. EXPECTED OUTCOMES\n"
        "(State quantitative predicted results, validation thresholds, and alternative outcomes.)\n"
        "## 7. LIMITATIONS & BIAS CONTROLS\n"
        "(Detail key limitations, measurement uncertainties, and concrete risk mitigation controls.)"
    )

    user_prompt = (
        f"### REFINED EXPERIMENT BRIEF\n"
        f"- **Topic**: {topic}\n"
        f"- **Canonical Domain**: {domain} (`{exp_type}`)\n"
        f"- **Refined Objective**: {refinement.get('refined_objective', topic)}\n"
        f"- **Filtered High-Signal Keywords**: {keywords}\n"
        f"- **Governing Equations**: {'; '.join(str(e) for e in equations) if equations else 'Domain-standard conservation/kinetic laws'}\n"
        f"- **Structured Baseline Parameters**: {json.dumps(params)}\n"
        f"- **Independent Variables**: {', '.join(str(x) for x in ind_vars) if ind_vars else 'Manipulated input parameter'}\n"
        f"- **Dependent Variables**: {', '.join(str(x) for x in dep_vars) if dep_vars else 'Measured primary outcome'}\n"
        f"- **Control Variables**: {', '.join(str(x) for x in ctrl_vars) if ctrl_vars else 'Environmental & calibration constants'}\n\n"
        f"### STOP-WORD-FILTERED LITERATURE CONTEXT\n"
        f"{lit_lines}\n\n"
        f"### REFINED INSTRUCTION FROM QWEN PRE-PROCESSOR\n"
        f"{refinement.get('refined_prompt', topic)}\n\n"
        f"{domain_block}"
        "Generate the complete, scientifically rigorous experimental design (400-550 words) across all 7 headings now."
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
