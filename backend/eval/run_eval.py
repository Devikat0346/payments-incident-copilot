"""
Evaluation harness for the incident copilot's LLM diagnostic reasoning.

Replays a fixed set of synthetic scenarios with known ground truth (see
scenarios.py) through the real `analyze_incident()` call, and scores whether
the model's response engages with the actual cause — not just whether it
returns well-formed JSON.

This is a manual/periodic check, not wired into CI: each run makes real calls
to whichever LLM_PROVIDER is configured (Ollama locally, free; Groq in
deployment, also free-tier but rate-limited), so it isn't run on every push.

Usage:
    ./venv/bin/python -m eval.run_eval
"""

import asyncio
import sys
import time

sys.path.insert(0, ".")

from app.llm_client import analyze_incident  # noqa: E402
from eval.scenarios import SCENARIOS  # noqa: E402


def _scores_as_expected(result: dict, expected_keywords: list[str]) -> bool:
    haystack = f"{result.get('summary', '')} {result.get('likely_root_cause', '')}".lower()
    return any(kw.lower() in haystack for kw in expected_keywords)


async def run() -> None:
    results = []
    for scenario in SCENARIOS:
        name = scenario["name"]
        start = time.monotonic()
        try:
            result = await analyze_incident(scenario["context"])
            error = None
        except Exception as exc:
            result = {}
            error = str(exc)
        elapsed = time.monotonic() - start

        passed = bool(result) and _scores_as_expected(result, scenario["expected_keywords"])
        results.append(
            {
                "name": name,
                "expected_kind": scenario["expected_kind"],
                "passed": passed,
                "elapsed_s": elapsed,
                "error": error,
                "summary": result.get("summary"),
                "likely_root_cause": result.get("likely_root_cause"),
            }
        )

        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {name} ({scenario['expected_kind']}, {elapsed:.1f}s)")
        if error:
            print(f"  ERROR: {error}")
        else:
            print(f"  summary: {result.get('summary')}")
            print(f"  root cause: {result.get('likely_root_cause')}")
        print()

    total = len(results)
    passed_count = sum(1 for r in results if r["passed"])
    avg_latency = sum(r["elapsed_s"] for r in results) / total if total else 0

    print("=" * 60)
    print(f"Score: {passed_count}/{total} scenarios correctly diagnosed")
    print(f"Avg. latency: {avg_latency:.1f}s per diagnosis")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run())
