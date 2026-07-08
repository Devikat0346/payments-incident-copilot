import asyncio
import logging

import httpx

from app import config
from app.llm_client import analyze_incident
from app.models import IncidentCase
from app.state import AppState

logger = logging.getLogger("poller")

DEGRADED_STATES = {"degraded", "breached"}


class Poller:
    def __init__(self, state: AppState) -> None:
        self.state = state
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        self._task = asyncio.create_task(self._loop())

    def stop(self) -> None:
        if self._task:
            self._task.cancel()

    async def _loop(self) -> None:
        async with httpx.AsyncClient(base_url=config.PLATFORM_API_URL, timeout=10.0) as client:
            while True:
                try:
                    await self._poll_once(client)
                except Exception:
                    logger.exception("poll cycle failed")
                await asyncio.sleep(config.POLL_INTERVAL_SECONDS)

    async def _poll_once(self, client: httpx.AsyncClient) -> None:
        metrics_resp = await client.get("/api/metrics/summary")
        metrics_resp.raise_for_status()
        summary = metrics_resp.json()

        for channel, metric in summary["channels"].items():
            is_degraded = metric["health"] in DEGRADED_STATES
            has_open_case = channel in self.state.open_case_by_channel

            if is_degraded and not has_open_case:
                await self._open_case(client, channel, metric)
            elif not is_degraded and has_open_case:
                await self.state.resolve_case(channel)

    async def _open_case(self, client: httpx.AsyncClient, channel: str, metric: dict) -> None:
        case = IncidentCase.new(channel=channel, rail=metric["rail"])
        case.metrics_snapshot = metric
        await self.state.add_case(case)

        try:
            txn_resp = await client.get(
                "/api/transactions/recent",
                params={"limit": config.RECENT_TXN_FETCH_LIMIT, "channel": channel},
            )
            txn_resp.raise_for_status()
            channel_transactions = txn_resp.json()
        except Exception:
            logger.exception("failed to fetch recent transactions for %s", channel)
            channel_transactions = []

        failures = [
            t for t in channel_transactions if t["status"] in config.FAILURE_STATUSES
        ][: config.MAX_SAMPLE_FAILURES]
        case.sample_failures = failures

        context = {
            "channel": channel,
            "rail": metric["rail"],
            "normal_baseline": config.CHANNEL_BASELINES.get(channel, "No baseline available."),
            "current_window_metrics": {
                "window_seconds": metric["window_seconds"],
                "total_transactions": metric["total"],
                "success_rate": metric["success_rate"],
                "p50_latency_ms": metric["p50_latency_ms"],
                "p95_latency_ms": metric["p95_latency_ms"],
                "p99_latency_ms": metric["p99_latency_ms"],
                "slo_success_rate_target": metric["slo_success_rate"],
                "slo_latency_p99_ms_target": metric["slo_latency_p99_ms"],
                "error_budget_burn_pct": metric["error_budget_burn_pct"],
            },
            "sample_recent_failures": [
                {
                    "status": t["status"],
                    "decline_reason": t.get("decline_reason"),
                    "return_code": t.get("return_code"),
                    "amount": t["amount"],
                    "auth_latency_ms": t.get("auth_latency_ms"),
                }
                for t in failures
            ],
        }

        try:
            result = await analyze_incident(context)
            case.summary = result.get("summary")
            case.likely_root_cause = result.get("likely_root_cause")
            case.confidence = result.get("confidence")
            case.recommended_actions = result.get("recommended_actions", [])
            case.severity = result.get("severity")
        except Exception as exc:
            logger.exception("analysis failed for case %s", case.id)
            case.analysis_error = str(exc)
        finally:
            from app.models import now

            case.generated_at = now()
            await self.state.update_case(case)
