from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal, Optional


def now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class IncidentCase:
    id: str
    channel: str
    rail: str
    detected_at: datetime
    resolved_at: Optional[datetime] = None

    # Populated once the LLM analysis completes.
    generated_at: Optional[datetime] = None
    summary: Optional[str] = None
    likely_root_cause: Optional[str] = None
    confidence: Optional[Literal["low", "medium", "high"]] = None
    recommended_actions: list[str] = field(default_factory=list)
    severity: Optional[Literal["low", "medium", "high"]] = None
    analysis_error: Optional[str] = None

    metrics_snapshot: dict = field(default_factory=dict)
    sample_failures: list[dict] = field(default_factory=list)

    @staticmethod
    def new(channel: str, rail: str) -> "IncidentCase":
        return IncidentCase(
            id=str(uuid.uuid4()),
            channel=channel,
            rail=rail,
            detected_at=now(),
        )

    @property
    def time_to_insight_seconds(self) -> Optional[float]:
        if self.generated_at is None:
            return None
        return (self.generated_at - self.detected_at).total_seconds()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "channel": self.channel,
            "rail": self.rail,
            "detected_at": self.detected_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
            "time_to_insight_seconds": self.time_to_insight_seconds,
            "summary": self.summary,
            "likely_root_cause": self.likely_root_cause,
            "confidence": self.confidence,
            "recommended_actions": self.recommended_actions,
            "severity": self.severity,
            "analysis_error": self.analysis_error,
            "metrics_snapshot": self.metrics_snapshot,
            "sample_failures": self.sample_failures,
            "active": self.resolved_at is None,
        }
