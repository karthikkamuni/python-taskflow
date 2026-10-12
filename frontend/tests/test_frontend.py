import pytest
import requests

import app as frontend


class FakeResponse:
    def __init__(self, content=b"{}", status_code=200, headers=None):
        self.content = content
        self.status_code = status_code
        self.headers = headers or {"Content-Type": "application/json"}


@pytest.fixture()
def client():
    return frontend.app.test_client()


def test_index_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"TaskFlow" in response.data


def test_health(client):
    assert client.get("/health").get_json() == {"status": "ok", "service": "frontend"}


def test_tasks_proxy_forwards_query(client, monkeypatch):
    seen = {}

    def fake_request(method, url, **kwargs):
        seen.update(method=method, url=url, params=dict(kwargs["params"]))
        return FakeResponse(b"[]")

    monkeypatch.setattr(frontend.requests, "request", fake_request)
    response = client.get("/api/tasks?status=done")
    assert response.status_code == 200
    assert seen["url"].endswith("/api/tasks")
    assert seen["params"] == {"status": "done"}


def test_create_task_proxy(client, monkeypatch):
    seen = {}

    def fake_request(method, url, **kwargs):
        seen.update(method=method, json=kwargs["json"])
        return FakeResponse(b'{"id": 1}', status_code=201)

    monkeypatch.setattr(frontend.requests, "request", fake_request)
    response = client.post("/api/tasks", json={"title": "hello"})
    assert response.status_code == 201
    assert seen == {"method": "POST", "json": {"title": "hello"}}


def test_delete_proxy_passes_through_204(client, monkeypatch):
    monkeypatch.setattr(
        frontend.requests, "request", lambda *a, **k: FakeResponse(b"", status_code=204)
    )
    assert client.delete("/api/tasks/5").status_code == 204


def test_upstream_down_returns_502(client, monkeypatch):
    def boom(*args, **kwargs):
        raise requests.ConnectionError("down")

    monkeypatch.setattr(frontend.requests, "request", boom)
    response = client.get("/api/stats")
    assert response.status_code == 502
    assert "unavailable" in response.get_json()["detail"]


def test_csv_export_keeps_download_header(client, monkeypatch):
    headers = {"Content-Type": "text/csv", "Content-Disposition": 'attachment; filename="tasks.csv"'}
    monkeypatch.setattr(
        frontend.requests, "request", lambda *a, **k: FakeResponse(b"id,title\n", headers=headers)
    )
    response = client.get("/reports/export.csv")
    assert response.headers["Content-Disposition"] == 'attachment; filename="tasks.csv"'


def test_services_status(client, monkeypatch):
    def fake_get(url, **kwargs):
        if "8001" in url:
            raise requests.ConnectionError("down")
        return FakeResponse()

    monkeypatch.setattr(frontend.requests, "get", fake_get)
    body = client.get("/api/services").get_json()
    assert body["frontend"] == "up"
    assert body["backend"] == "up"
    assert body["notifications"] == "down"
