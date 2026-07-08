import asyncio

from app.models import IncidentCase


class AppState:
    def __init__(self) -> None:
        self.cases: dict[str, IncidentCase] = {}
        self.open_case_by_channel: dict[str, str] = {}  # channel -> case id
        self.subscribers: set[asyncio.Queue] = set()
        self.lock = asyncio.Lock()

    async def add_case(self, case: IncidentCase) -> None:
        async with self.lock:
            self.cases[case.id] = case
            self.open_case_by_channel[case.channel] = case.id
        await self.publish({"type": "case_opened", "data": case.to_dict()})

    async def update_case(self, case: IncidentCase) -> None:
        await self.publish({"type": "case_updated", "data": case.to_dict()})

    async def resolve_case(self, channel: str) -> None:
        async with self.lock:
            case_id = self.open_case_by_channel.pop(channel, None)
            case = self.cases.get(case_id) if case_id else None
        if case:
            from app.models import now

            case.resolved_at = now()
            await self.publish({"type": "case_resolved", "data": case.to_dict()})

    def recent_cases(self, limit: int = 50) -> list[IncidentCase]:
        return sorted(self.cases.values(), key=lambda c: c.detected_at, reverse=True)[:limit]

    async def publish(self, message: dict) -> None:
        dead = []
        for q in self.subscribers:
            try:
                q.put_nowait(message)
            except asyncio.QueueFull:
                dead.append(q)
        for q in dead:
            self.subscribers.discard(q)


state = AppState()
