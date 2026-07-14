import asyncio
import json
import re

import httpx

from app import config

GROQ_MAX_ATTEMPTS = 3
GROQ_BACKOFF_SECONDS = 2.0


class LLMRateLimitedError(Exception):
    """Raised when the LLM provider is still rate-limiting us after retries.

    Kept distinct from a bare httpx.HTTPStatusError so callers can show a
    clean, honest message instead of the raw exception text (which for a
    429 includes the full request URL and an MDN troubleshooting link —
    fine in a log, not fine surfaced verbatim in a case's diagnosis field).
    """

SYSTEM_PROMPT = """You are an SRE incident analyst embedded in a payments platform's on-call \
workflow. You are shown live telemetry for one payment origination channel that has just \
crossed into a degraded or breached health state, plus a sample of its most recent failed \
transactions. You are NOT told what actually caused the incident — form your own hypothesis \
from the symptoms, the way an on-call engineer would when a page fires.

Respond with ONLY a JSON object (no markdown fences, no prose outside the JSON) matching \
exactly this schema:
{
  "summary": "one or two sentence plain-English summary of what's happening",
  "likely_root_cause": "your best hypothesis for the underlying cause, reasoned from the symptoms",
  "confidence": "low" | "medium" | "high",
  "recommended_actions": ["action 1", "action 2", "action 3"],
  "severity": "low" | "medium" | "high"
}

Ground your reasoning in the specific numbers given (latency percentiles vs baseline, success \
rate vs SLO, the decline/return reason codes in the failure sample). Distinguish between a pure \
latency problem (symptoms: elevated p95/p99 with success rate close to normal — suggests a slow \
downstream dependency or resource contention, not application logic) and a pure failure-rate \
problem (symptoms: normal latency but elevated declines/returns concentrated in one or two reason \
codes — suggests a logic, config, or upstream-dependency issue specific to that failure mode)."""


def _build_user_message(context: dict) -> str:
    return (
        "Channel telemetry snapshot:\n"
        f"{json.dumps(context, indent=2, default=str)}\n\n"
        "Analyze this and respond with the JSON object described in your instructions."
    )


def _extract_json(text: str) -> dict:
    text = text.strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in model response: {text[:200]}")
    return json.loads(match.group(0))


async def _call_ollama(user_message: str) -> str:
    async with httpx.AsyncClient(timeout=90.0) as client:
        resp = await client.post(
            f"{config.OLLAMA_BASE_URL}/api/chat",
            json={
                "model": config.OLLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                "stream": False,
                "format": "json",
            },
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"]


async def _call_groq(user_message: str) -> str:
    if not config.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set but LLM_PROVIDER=groq.")
    async with httpx.AsyncClient(timeout=30.0) as client:
        for attempt in range(GROQ_MAX_ATTEMPTS):
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {config.GROQ_API_KEY}"},
                json={
                    "model": config.GROQ_MODEL,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_message},
                    ],
                    "response_format": {"type": "json_object"},
                },
            )
            if resp.status_code == 429 and attempt < GROQ_MAX_ATTEMPTS - 1:
                # The free tier's rate limit is a rolling window, not a
                # concurrency cap — a short wait and retry usually clears it.
                # Honor Retry-After when Groq sends one; otherwise back off.
                retry_after = resp.headers.get("retry-after")
                delay = float(retry_after) if retry_after else GROQ_BACKOFF_SECONDS * (2**attempt)
                await asyncio.sleep(delay)
                continue
            if resp.status_code == 429:
                raise LLMRateLimitedError(
                    f"Groq rate-limited the request after {GROQ_MAX_ATTEMPTS} attempts."
                )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]


async def analyze_incident(context: dict) -> dict:
    user_message = _build_user_message(context)

    if config.LLM_PROVIDER == "groq":
        raw = await _call_groq(user_message)
    else:
        raw = await _call_ollama(user_message)

    return _extract_json(raw)
