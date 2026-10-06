"""
Cradilot runtime configuration — one place, entirely environment-driven.

Nothing about who is selling, which engine answers, or which product list is quoted
is hardcoded in the codebase. Fork the repo, set these variables, and the same engine
becomes your company's tool with your own price list.

Keys are read from the environment only. They are never written to disk by this
application, never returned by an endpoint, and never included in a log line.
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent

# 允许仓库根放一个 .env 方便本地起服务。它只填充尚未设置的变量，因此真实的
# 进程环境（systemd / Docker -e / CI secrets）永远优先于文件。
DOTENV_PATH = BASE_DIR / ".env"


def load_dotenv(path: Optional[Path] = None) -> List[str]:
    """Minimal .env reader (stdlib only). Returns the keys it filled.

    Values are never echoed; only key names are reported, so a mistaken log of this
    return value cannot leak a secret.
    """
    loaded: List[str] = []
    env_file = path or DOTENV_PATH
    if not env_file.exists():
        return loaded

    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        if key and key not in os.environ:
            os.environ[key] = value
            loaded.append(key)
    return loaded


load_dotenv()


def _env_str(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


def _env_float(key: str, default: float) -> float:
    raw = _env_str(key)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(key: str, default: int) -> int:
    raw = _env_str(key)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


# ─── Who is doing the selling ─────────────────────────────────────────────────
# The defaults are deliberately blank-looking placeholders rather than any real
# company: a fresh clone must not appear to belong to somebody else's business.
VENDOR_NAME = _env_str("CRADILOT_VENDOR_NAME", "Your Company")
VENDOR_DOMAIN = _env_str("CRADILOT_VENDOR_DOMAIN", "your-company.example")
VENDOR_TAGLINE = _env_str("CRADILOT_VENDOR_TAGLINE", "Digital Growth Advisory")


# Product list quoted in the roadmap, the cart and the PDF. Replace this file with
# your own SKUs; the schema is documented in docs/ADAPTING.md.
PRODUCT_CATALOG_PATH = Path(
    _env_str("CRADILOT_PRODUCT_CATALOG", str(BASE_DIR / "data" / "product_catalog.json"))
)
KNOWLEDGE_DIR = Path(_env_str("CRADILOT_KNOWLEDGE_DIR", str(BASE_DIR / "data" / "knowledge_base")))


def branding() -> Dict[str, Any]:
    """Public identity block handed to the UI so no page hardcodes a company name."""
    return {
        "vendor_name": VENDOR_NAME,
        "vendor_domain": VENDOR_DOMAIN,
        "tagline": VENDOR_TAGLINE,
    }


# ─── Which engine answers ─────────────────────────────────────────────────────
PROVIDER_OLLAMA = "ollama"
PROVIDER_GEMINI = "gemini"
PROVIDER_OPENAI = "openai"
PROVIDER_OFF = "off"
KNOWN_PROVIDERS = (PROVIDER_OLLAMA, PROVIDER_GEMINI, PROVIDER_OPENAI, PROVIDER_OFF)

DEFAULT_MODELS = {
    PROVIDER_OLLAMA: "gemma3:12b",
    PROVIDER_GEMINI: "gemini-2.5-flash",
    PROVIDER_OPENAI: "gpt-4o-mini",
    PROVIDER_OFF: "",
}

GEMINI_API_KEY = _env_str("GEMINI_API_KEY") or _env_str("GOOGLE_API_KEY")
OPENAI_API_KEY = _env_str("OPENAI_API_KEY")
OLLAMA_BASE_URL = _env_str("CRADILOT_OLLAMA_URL")
OPENAI_BASE_URL = _env_str("CRADILOT_OPENAI_BASE_URL", "https://api.openai.com/v1")


def resolve_provider(explicit: Optional[str] = None) -> str:
    """Pick the engine. An explicit CRADILOT_LLM_PROVIDER always wins; otherwise the
    first configured backend is used, and 'off' keeps the rule-based fallback honest."""
    choice = (explicit if explicit is not None else _env_str("CRADILOT_LLM_PROVIDER")).lower()
    if choice in KNOWN_PROVIDERS:
        return choice
    if GEMINI_API_KEY:
        return PROVIDER_GEMINI
    if OPENAI_API_KEY:
        return PROVIDER_OPENAI
    if OLLAMA_BASE_URL:
        return PROVIDER_OLLAMA
    return PROVIDER_OFF


def model_for(provider: str) -> str:
    return _env_str("CRADILOT_MODEL") or DEFAULT_MODELS.get(provider, "")


def api_key_present(provider: str) -> bool:
    if provider == PROVIDER_GEMINI:
        return bool(GEMINI_API_KEY)
    if provider == PROVIDER_OPENAI:
        return bool(OPENAI_API_KEY)
    return True  # Ollama needs no key; 'off' never asks for one.


# ─── Engine behaviour ─────────────────────────────────────────────────────────
ENGINE_TIMEOUT_SECONDS = _env_int("CRADILOT_LLM_TIMEOUT", 120)
PROBE_TIMEOUT_SECONDS = _env_float("CRADILOT_PROBE_TIMEOUT", 5.0)
HEALTH_TTL_SECONDS = _env_float("CRADILOT_HEALTH_TTL", 60.0)
FAILURE_TTL_SECONDS = _env_float("CRADILOT_FAILURE_TTL", 5.0)


# ─── HTTP surface ─────────────────────────────────────────────────────────────
# CORS is same-origin by default: the UI is served by this very process, so an
# unset variable is the secure setting rather than a wildcard.
ALLOWED_ORIGINS: List[str] = [
    origin.strip()
    for origin in _env_str("CRADILOT_ALLOWED_ORIGINS").split(",")
    if origin.strip()
]

# Report identifiers carry this prefix; set it to your own case reference.
REPORT_PREFIX = _env_str("CRADILOT_REPORT_PREFIX", "CRDL")

# Where runtime state lands. Both files are gitignored; the leads file holds customer
# contact details and must never be committed.
DATA_DIR = Path(_env_str("CRADILOT_DATA_DIR", str(BASE_DIR / "data")))
SALES_LEADS_PATH = DATA_DIR / "sales_leads.jsonl"


def warn_if_unconfigured(stream=sys.stderr) -> None:
    provider = resolve_provider()
    if provider != PROVIDER_OFF:
        return
    print(
        "[cradilot] No AI engine configured: set CRADILOT_LLM_PROVIDER plus "
        "GEMINI_API_KEY, OPENAI_API_KEY or CRADILOT_OLLAMA_URL. "
        "Until then the app runs on its deterministic rule engine and labels every "
        "AI-written passage as degraded.",
        file=stream,
    )
