"""Project-local configuration. Remote planning, synthesis and translation are opt-in."""
from __future__ import annotations
import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Load a .env if python-dotenv is available (optional dependency).
try:  # pragma: no cover - convenience only
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except Exception:
    pass

def _b(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _f(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _i(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


@dataclass
class Settings:
    # ---- paths ----
    corpus_path: Path = ROOT / "corpus" / "corpus.jsonl"
    classifier_rules_path: Path = ROOT / "config" / "classifier_rules.yaml"
    registry_path: Path = ROOT / "config" / "registry_router.yaml"
    consent_log_path: Path = field(default_factory=lambda: Path(os.getenv("IP_SAKTI_LOG_DIR", str(ROOT / "logs"))) / "consent_log.jsonl")
    audit_log_path: Path = field(default_factory=lambda: Path(os.getenv("IP_SAKTI_LOG_DIR", str(ROOT / "logs"))) / "audit_log.jsonl")

    # Models plan and synthesize source-cited conditional guidance and translate.
    # They do not establish the product's legal category or verify its facts.
    # provider: "anthropic" | "openai" | "none"
    llm_provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "none").strip().lower())
    llm_base_url: str = field(default_factory=lambda: os.getenv("LLM_BASE_URL", "").strip())
    llm_api_key: str = field(default_factory=lambda: os.getenv("LLM_API_KEY", "").strip())
    llm_model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "").strip())
    llm_max_tokens: int = field(default_factory=lambda: _i("LLM_MAX_TOKENS", 900))
    llm_timeout: float = field(default_factory=lambda: _f("LLM_TIMEOUT", 30.0))
    # Some third-party gateways sit behind Cloudflare and 403 non-browser User-Agents.
    llm_user_agent: str = field(default_factory=lambda: os.getenv(
        "LLM_USER_AGENT",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"))

    # ---- retrieval ----
    # retriever: "bm25" (always works, default) | "hybrid" (adds dense embeddings)
    retriever: str = field(default_factory=lambda: os.getenv("RETRIEVER", "bm25").strip().lower())
    dense_model: str = field(default_factory=lambda: os.getenv("DENSE_MODEL", "intfloat/multilingual-e5-small").strip())
    top_k: int = field(default_factory=lambda: _i("TOP_K", 6))
    rerank_top_n: int = field(default_factory=lambda: _i("RERANK_TOP_N", 4))

    # ---- abstention gate ----
    # If the blended confidence is below this, the assistant abstains + escalates.
    abstain_threshold: float = field(default_factory=lambda: _f("ABSTAIN_THRESHOLD", 0.22))
    # If query/corpus lexical overlap (coverage) is below this, force abstain (out-of-scope).
    coverage_floor: float = field(default_factory=lambda: _f("COVERAGE_FLOOR", 0.15))
    min_citations: int = field(default_factory=lambda: _i("MIN_CITATIONS", 1))

    # ---- translation layer ----
    # "llm" (use the configured multilingual LLM), "none" (English only). Production: indictrans2 / bhashini.
    translate_provider: str = field(default_factory=lambda: os.getenv("TRANSLATE_PROVIDER", "none").strip().lower())

    @property
    def llm_enabled(self) -> bool:
        return (self.llm_provider in {"anthropic", "openai"}
                and bool(self.llm_api_key) and bool(self.llm_model))


def _load_provider_file(s: Settings) -> None:
    """Opt-in compatibility for a local provider.txt containing a key and URL.

    Explicit environment values win. The caller must choose a provider and model;
    adjacent credentials never activate a model on their own.
    """
    # Credential discovery requires opt-in. Explicit offline mode always wins.
    if (not _b("ALLOW_PROVIDER_FILE", False)
            or s.llm_provider not in {"anthropic", "openai"} or s.llm_enabled):
        return
    import json
    for cand in (ROOT / "provider.txt", ROOT.parent / "provider.txt"):
        try:
            cfg = json.loads(cand.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(cfg, dict):
            continue
        url, key = cfg.get("url", ""), cfg.get("key", "")
        if not isinstance(url, str) or not isinstance(key, str):
            continue
        url, key = url.strip(), key.strip()
        if url and key:
            if not s.llm_base_url:
                s.llm_base_url = url
            if not s.llm_api_key:
                s.llm_api_key = key
            return


settings = Settings()
_load_provider_file(settings)
DISCLAIMER = (
    "IP-SAKTI Sahayak provides information, not legal advice. Verify every citation "
    "against the primary source and consult a qualified IP/regulatory professional "
    "before acting."
)
