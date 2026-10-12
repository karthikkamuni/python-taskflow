import pytest
from fastapi.testclient import TestClient

from app import main
from app.store import NotificationStore


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(main, "store", NotificationStore(None))  # fresh in-memory store
    return TestClient(main.app)


def test_health(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["storage"] == "memory"


def test_create_and_list_newest_first(client):
    for i in range(3):
        response = client.post(
            "/api/notifications",
            json={"event_type": "task_created", "task_id": i, "message": f"msg {i}"},
        )
        assert response.status_code == 201
        assert response.json()["id"]

    items = client.get("/api/notifications").json()
    assert [n["message"] for n in items] == ["msg 2", "msg 1", "msg 0"]


def test_limit(client):
    for i in range(5):
        client.post("/api/notifications", json={"event_type": "x", "message": str(i)})
    assert len(client.get("/api/notifications", params={"limit": 2}).json()) == 2


def test_validation(client):
    assert client.post("/api/notifications", json={"event_type": "x"}).status_code == 422
