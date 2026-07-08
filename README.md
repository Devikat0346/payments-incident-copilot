# AI Payments Incident Copilot

Watches the [Multi-Rail Payments Observability Platform](https://github.com/Devikat0346/payments-observability-platform) live, and the moment a channel's health degrades, pulls its telemetry and uses an LLM to independently diagnose the likely root cause — without ever being told what the injected fault actually was.

**Live demo:** https://payments-incident-copilot.vercel.app
**API:** https://payments-incident-copilot-api.fly.dev/api/health

## Why this exists

MTTD (mean time to detect) and MTTR (mean time to resolve) are the two numbers that matter most in an SRE's day. Detection is usually automatable — an alert fires. Diagnosis is the slower, more human part: an on-call engineer has to look at metrics, cross-reference recent errors, and form a hypothesis before they can even start fixing anything. This project automates that second step: it treats an LLM as a first-pass on-call analyst that turns raw telemetry into a hypothesis in seconds, not minutes.

The design constraint that makes this a real test of reasoning, not a party trick: **the model is deliberately not given the incident's ground-truth type.** The upstream platform tags each injected incident internally as a `latency_spike` or `failure_spike`, but that label is stripped out before the model ever sees the case — it only gets the same raw signals (latency percentiles vs. baseline, success rate vs. SLO, a sample of failed transactions with their decline/return codes) a human on-call engineer would have. It has to figure out which kind of problem it's looking at from the symptoms, and reason about *why*, the way the failure pattern in the sample data points.

## How it works

```
┌────────────────────────────┐   poll every 5s    ┌─────────────────────────────┐
│ Payments Observability      │◀────────────────────│  Incident Copilot backend   │
│ Platform (external, live)   │  metrics + txns     │  (FastAPI, asyncio poller)  │
└────────────────────────────┘─────────────────────▶│                             │
                                                      │  on health degradation:    │
                                                      │  build context → call LLM  │
                                                      └──────────────┬──────────────┘
                                                                     │ WebSocket
                                                                     ▼
                                                      ┌─────────────────────────────┐
                                                      │  Next.js incident timeline  │
                                                      └─────────────────────────────┘
```

1. A background poller hits the observability platform's public REST API every 5 seconds.
2. When a channel's health flips to `degraded` or `breached`, it opens a **case**: pulls that channel's SLO targets, current windowed SLIs, and a sample of its most recent failed transactions (via a channel-scoped query — see *Design decisions*).
3. That context (metrics + failure sample + a plain-English baseline description) is sent to an LLM with a system prompt instructing it to reason like an on-call SRE and return structured JSON: a summary, a root-cause hypothesis, confidence, severity, and recommended actions.
4. The case is pushed live to the frontend over WebSocket, along with a **time-to-insight** metric — the gap between detection and diagnosis.
5. When the channel recovers, the case is marked resolved.

## Pluggable LLM backend

The LLM call is behind a small provider abstraction (`app/llm_client.py`) rather than hardcoded to one vendor:

- **`ollama`** (default) — a local, open-source model (Llama 3.1 8B) running on the developer's machine via [Ollama](https://ollama.com). Zero cost, zero API key, fully offline.
- **`groq`** — a free-tier cloud API serving open-source models (Llama 3.3 70B), used for the live-deployed version since a hosted backend can't reach a laptop's local Ollama instance.

Switch providers with one env var (`LLM_PROVIDER=ollama|groq`) — no code changes.

## Design decisions

- **The model never sees the injected incident's ground-truth label.** Passing it through would turn "diagnose this" into "repeat this back to me." Only the observable symptoms are passed in.
- **Channel-scoped transaction queries.** The upstream platform's `/api/transactions/recent` originally returned the N most recent events across *all* channels. For a low-frequency rail like ACH batch, that window could be scrolled past entirely by high-frequency card traffic before the copilot ever looked at it — so the sample of "recent failures" would silently come back empty for exactly the channels most likely to need it. Fixed by adding `channel`/`status` query params upstream so this project (and future ones) can pull a channel's own recent history directly rather than filtering a shared firehose.
- **Structured JSON output, not free text.** Ollama's `format: "json"` mode (and Groq's `response_format: json_object`) constrain the model to valid JSON matching the documented schema, so the frontend can render fields directly instead of parsing prose.

## Tech stack

- **Backend:** Python 3.12, FastAPI, asyncio, httpx (both for polling the upstream platform and for calling the LLM APIs)
- **Frontend:** Next.js 16 (App Router), TypeScript, Tailwind CSS
- **LLM:** Llama 3.1 8B via Ollama (local dev) / Llama 3.3 70B via Groq (deploy)

## Running locally

**Backend:**
```bash
# 1. Install Ollama and pull a model
brew install ollama
brew services start ollama
ollama pull llama3.1:8b

# 2. Run the backend
cd backend
python3.12 -m venv venv
./venv/bin/pip install -r requirements.txt
./venv/bin/uvicorn app.main:app --port 8001
```

**Frontend:**
```bash
cd frontend
npm install
# .env.local: NEXT_PUBLIC_API_URL=http://localhost:8001, NEXT_PUBLIC_WS_URL=ws://localhost:8001/ws/live
npm run dev
```

## Caveats

This is a demonstration of an AI-assisted triage workflow, not a production incident-response tool. Diagnoses come from a general-purpose LLM reasoning over a small telemetry snapshot — they're plausible hypotheses to accelerate a human's first look, not verified findings.

**Known limitation:** a case opens the instant the upstream platform reports a channel as `degraded`, which can be within a second of the underlying fault starting — before enough failed transactions have accumulated in the rolling window to actually show a pattern. In that situation the model correctly reports "no anomaly visible in the data yet" rather than fabricating a cause, which is the right behavior, but it means very fresh incidents sometimes get a low-signal first analysis. A production version would debounce analysis by a few seconds, or re-analyze once more failure data has accumulated.
