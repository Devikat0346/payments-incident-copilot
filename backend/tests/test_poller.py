import asyncio
import time

import pytest

from app.poller import Poller
from app.state import AppState


class FakeResponse:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self._data


class FakeClient:
    """Stands in for httpx.AsyncClient without making real network calls."""

    def __init__(self, metrics_summary):
        self.metrics_summary = metrics_summary

    async def get(self, path, params=None):
        if path == "/api/metrics/summary":
            return FakeResponse(self.metrics_summary)
        if path == "/api/transactions/recent":
            return FakeResponse([])
        raise AssertionError(f"unexpected path requested in test: {path}")


def _degraded_metric(channel: str, rail: str) -> dict:
    return {
        "channel": channel,
        "rail": rail,
        "health": "breached",
        "window_seconds": 300,
        "total": 10,
        "success": 5,
        "failure": 5,
        "success_rate": 0.5,
        "p50_latency_ms": 100,
        "p95_latency_ms": 200,
        "p99_latency_ms": 300,
        "slo_success_rate": 0.99,
        "slo_latency_p99_ms": 1000,
        "error_budget_burn_pct": 500,
    }


@pytest.mark.asyncio
async def test_simultaneous_incidents_are_diagnosed_concurrently_not_serially(monkeypatch):
    metrics_summary = {
        "channels": {
            "pos": _degraded_metric("pos", "CARD"),
            "wire_branch": _degraded_metric("wire_branch", "WIRE"),
            "zelle_mobile": _degraded_metric("zelle_mobile", "ZELLE"),
        }
    }
    client = FakeClient(metrics_summary)

    call_count = 0
    ANALYSIS_DELAY = 0.2

    async def fake_analyze_incident(context):
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(ANALYSIS_DELAY)
        return {
            "summary": "test",
            "likely_root_cause": "test",
            "confidence": "low",
            "recommended_actions": [],
            "severity": "low",
        }

    monkeypatch.setattr("app.poller.analyze_incident", fake_analyze_incident)

    state = AppState()
    poller = Poller(state)

    start = time.monotonic()
    await poller._poll_once(client)
    elapsed = time.monotonic() - start

    assert call_count == 3
    assert len(state.cases) == 3
    # Serial execution would take >= 3 * ANALYSIS_DELAY (0.6s). Concurrent
    # execution should finish in roughly one delay's worth of time.
    assert elapsed < ANALYSIS_DELAY * 2, (
        f"took {elapsed:.2f}s for 3 concurrent diagnoses — looks serial, not concurrent"
    )


@pytest.mark.asyncio
async def test_resolves_case_when_channel_recovers(monkeypatch):
    healthy_metric = _degraded_metric("pos", "CARD")
    healthy_metric["health"] = "healthy"
    client = FakeClient({"channels": {"pos": healthy_metric}})

    state = AppState()
    from app.models import IncidentCase

    existing_case = IncidentCase.new(channel="pos", rail="CARD")
    state.cases[existing_case.id] = existing_case
    state.open_case_by_channel["pos"] = existing_case.id

    poller = Poller(state)
    await poller._poll_once(client)

    assert "pos" not in state.open_case_by_channel
    assert existing_case.resolved_at is not None
