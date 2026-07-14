from datetime import timedelta

import pytest

from app.models import IncidentCase, now


class TestIncidentCase:
    def test_new_case_has_no_insight_yet(self):
        case = IncidentCase.new(channel="pos", rail="CARD")
        assert case.time_to_insight_seconds is None
        assert case.to_dict()["active"] is True

    def test_time_to_insight_computed_after_generation(self):
        case = IncidentCase.new(channel="pos", rail="CARD")
        case.generated_at = case.detected_at + timedelta(seconds=3.5)
        assert case.time_to_insight_seconds == pytest.approx(3.5)

    def test_resolved_case_is_not_active(self):
        case = IncidentCase.new(channel="wire_branch", rail="WIRE")
        case.resolved_at = now()
        assert case.to_dict()["active"] is False

    def test_to_dict_serializes_datetimes_as_iso_strings(self):
        case = IncidentCase.new(channel="zelle_mobile", rail="ZELLE")
        d = case.to_dict()
        assert isinstance(d["detected_at"], str)
        assert d["resolved_at"] is None
