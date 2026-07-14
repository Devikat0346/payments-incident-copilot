# Diagnosis eval harness

Replays 6 synthetic incident scenarios with known ground truth through the real `analyze_incident()` call, and scores whether the model's diagnosis actually engages with the true cause — not just whether it returns valid JSON. The model is never told which kind of scenario it's looking at; only the raw telemetry shape it would see in production.

Scenarios cover both failure classes across multiple rails: pure latency spikes (POS, wire-branch) and pure failure-rate spikes with distinct causes (e-commerce fraud declines, Zelle recipient-not-enrolled, LoanIQ compliance holds, ACH NSF returns).

**Latest run** (Llama 3.1 8B via local Ollama): **6/6 scenarios correctly diagnosed**, ~6.7s average time per diagnosis.

## Running it

```bash
cd backend
./venv/bin/python -m eval.run_eval
```

Not wired into CI — each run makes real LLM calls, and running it on every push would burn through free-tier quota for no benefit. Run it manually after changing the system prompt, the LLM provider, or the context-building logic in `poller.py`.
