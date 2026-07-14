from fastapi.testclient import TestClient

from app.main import app
from app.models import IncidentCase
from app.state import state

# Deliberately not using `with TestClient(app) as client:` — see test_api.py:
# that form triggers the app's lifespan, which starts the poller and makes
# real network calls to the live upstream platform. Skipping the context
# manager exercises the websocket route in isolation, offline.
client = TestClient(app)


def test_websocket_sends_existing_cases_on_connect():
    case = IncidentCase.new(channel="pos", rail="CARD")
    case.summary = "test summary"
    state.cases[case.id] = case
    state.open_case_by_channel["pos"] = case.id
    try:
        with client.websocket_connect("/ws/live") as websocket:
            message = websocket.receive_json()
            assert message["type"] == "case_opened"
            assert message["data"]["channel"] == "pos"
            assert message["data"]["summary"] == "test summary"
    finally:
        state.cases.pop(case.id, None)
        state.open_case_by_channel.pop("pos", None)


def test_websocket_disconnect_removes_the_subscriber():
    before = len(state.subscribers)
    with client.websocket_connect("/ws/live") as websocket:
        # connecting with no existing cases: nothing to receive, just confirm
        # the subscriber queue was registered while the connection is open
        assert len(state.subscribers) == before + 1
    assert len(state.subscribers) == before
