from fastapi.testclient import TestClient

from app.main import app

# Deliberately NOT using `with TestClient(app) as client:` — that form triggers the
# app's lifespan, which starts the poller and makes real network calls to the live
# upstream platform. Instantiating without the context manager skips lifespan, so
# these tests exercise the route handlers in isolation, offline.
client = TestClient(app)


def test_health():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_cases_empty_list_by_default():
    resp = client.get("/api/cases")
    assert resp.status_code == 200
    assert resp.json() == []


def test_case_detail_not_found():
    resp = client.get("/api/cases/does-not-exist")
    assert resp.status_code == 404
    assert resp.json() == {"detail": "not found"}
