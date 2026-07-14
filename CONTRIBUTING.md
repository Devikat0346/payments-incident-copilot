# Contributing

This is a personal portfolio project, not under active development for outside contributions — but issues and suggestions are genuinely welcome if something looks wrong or could be better.

## Local setup

See the README's "Running locally" section. You'll need Ollama running locally (default) or a Groq API key (`LLM_PROVIDER=groq`).

## Before submitting a PR

- Run `pytest tests/ -v` from `backend/` — CI runs the same suite on every push (it does not call a live LLM; the eval harness below is separate and manual).
- If you change the system prompt, the context shape sent to the model, or the LLM provider, run `python -m eval.run_eval` and check the score didn't regress.
- Adding a new upstream channel? Update `config.CHANNEL_BASELINES` — `tests/test_config.py` will fail if you forget, which is exactly the bug this test exists to catch.

## Reporting a bug

Open an issue with what you expected vs. what happened.
