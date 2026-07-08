import os

from dotenv import load_dotenv

load_dotenv()

# "ollama" (local, free, default) or "groq" (free cloud API, needed for a live deployment
# since a deployed backend can't reach a laptop's local Ollama instance).
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "ollama")

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

PLATFORM_API_URL = os.environ.get(
    "PLATFORM_API_URL", "https://payments-observability-api.fly.dev"
)

POLL_INTERVAL_SECONDS = float(os.environ.get("POLL_INTERVAL_SECONDS", "5"))
MAX_SAMPLE_FAILURES = 8
RECENT_TXN_FETCH_LIMIT = 50

FAILURE_STATUSES = {"declined", "failed", "returned"}

# Descriptive normal-operating baselines, for grounding the model's reasoning —
# mirrors the upstream simulator's configured targets so the model is comparing
# against the same expectations a human SRE would have from a runbook or dashboard.
CHANNEL_BASELINES: dict[str, str] = {
    "pos": "Typically >99% success, ~150-250ms p50 authorization latency.",
    "ecommerce": "Typically >96% success (higher decline rate is normal here due to fraud screening), ~250-450ms p50 latency.",
    "mobile_wallet": "Typically >98% success, ~180-300ms p50 latency.",
    "wire_online": "Typically >99% success, ~700-1200ms p50 latency.",
    "wire_branch": "Typically >99.5% success, ~1100-1800ms p50 latency.",
    "ach_batch_file": "Typically >98% success per batch run; failures are returns (NSF, closed account) rather than latency.",
}
