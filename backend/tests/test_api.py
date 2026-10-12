def make_task(client, **overrides):
    payload = {"title": "Write Dockerfile", "priority": "high", **overrides}
    response = client.post("/api/tasks", json=payload)
    assert response.status_code == 201
    return response.json()


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "backend"
    assert body["database"] == "up"


def test_create_and_get_task(client):
    task = make_task(client, description="for the backend")
    assert task["status"] == "todo"
    assert task["priority"] == "high"

    fetched = client.get(f"/api/tasks/{task['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["title"] == "Write Dockerfile"


def test_list_and_filter_by_status(client):
    make_task(client, title="a")
    done = make_task(client, title="b")
    client.put(f"/api/tasks/{done['id']}", json={"status": "done"})

    assert len(client.get("/api/tasks").json()) == 2
    only_done = client.get("/api/tasks", params={"status": "done"}).json()
    assert [t["title"] for t in only_done] == ["b"]


def test_update_task(client):
    task = make_task(client)
    response = client.put(f"/api/tasks/{task['id']}", json={"status": "in_progress"})
    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"
    assert response.json()["title"] == "Write Dockerfile"  # untouched fields stay


def test_delete_task(client):
    task = make_task(client)
    assert client.delete(f"/api/tasks/{task['id']}").status_code == 204
    assert client.get(f"/api/tasks/{task['id']}").status_code == 404


def test_not_found(client):
    assert client.get("/api/tasks/999").status_code == 404
    assert client.put("/api/tasks/999", json={"title": "x"}).status_code == 404
    assert client.delete("/api/tasks/999").status_code == 404


def test_validation_errors(client):
    assert client.post("/api/tasks", json={"title": ""}).status_code == 422
    assert client.post("/api/tasks", json={"title": "x", "status": "bogus"}).status_code == 422


def test_stats_are_cached_and_invalidated(client):
    make_task(client)
    first = client.get("/api/stats").json()
    assert first["total"] == 1 and first["cached"] is False
    assert client.get("/api/stats").json()["cached"] is True

    make_task(client, title="second")  # a write invalidates the cache
    after = client.get("/api/stats").json()
    assert after["total"] == 2 and after["cached"] is False


def test_notifications_are_sent(client, events):
    task = make_task(client)
    client.put(f"/api/tasks/{task['id']}", json={"status": "done"})
    client.delete(f"/api/tasks/{task['id']}")
    assert [e[0] for e in events] == ["task_created", "task_updated", "task_deleted"]
