import httpx
import pytest
from fastapi.testclient import TestClient

from app import main

TASKS = [
    {"id": 1, "title": "a", "status": "done", "priority": "high", "created_at": "2026-01-01"},
    {"id": 2, "title": "=SUM(A1)", "status": "todo", "priority": "low", "created_at": "2026-01-02"},
    {"id": 3, "title": "c", "status": "done", "priority": "high", "created_at": "2026-01-03"},
    {"id": 4, "title": "d", "status": "in_progress", "priority": "medium", "created_at": "2026-01-04"},
]


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(main, "fetch_tasks", lambda: TASKS)
    return TestClient(main.app)


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_summary(client):
    body = client.get("/api/reports/summary").json()
    assert body["total"] == 4
    assert body["by_status"] == {"todo": 1, "in_progress": 1, "done": 2}
    assert body["by_priority"] == {"low": 1, "medium": 1, "high": 2}
    assert body["completion_rate"] == 50.0


def test_summary_empty(monkeypatch):
    monkeypatch.setattr(main, "fetch_tasks", lambda: [])
    body = TestClient(main.app).get("/api/reports/summary").json()
    assert body["total"] == 0 and body["completion_rate"] == 0.0


def test_csv_export_sanitises_formulas(client):
    response = client.get("/api/reports/export.csv")
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]
    lines = response.text.strip().splitlines()
    assert lines[0] == "id,title,status,priority,created_at"
    assert len(lines) == 5
    assert "'=SUM(A1)" in response.text


def test_backend_down_returns_502(monkeypatch):
    def boom(*args, **kwargs):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(main.httpx, "get", boom)
    assert TestClient(main.app).get("/api/reports/summary").status_code == 502
