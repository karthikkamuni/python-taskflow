"""TaskFlow frontend: serves the web UI and proxies API calls to the other
services, so the browser only ever talks to this one origin."""
import os

import requests
from flask import Flask, Response, jsonify, render_template, request

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
NOTIFICATION_URL = os.getenv("NOTIFICATION_URL", "http://localhost:8001")
REPORT_URL = os.getenv("REPORT_URL", "http://localhost:8002")

SERVICES = {
    "backend": BACKEND_URL,
    "notifications": NOTIFICATION_URL,
    "reports": REPORT_URL,
}

app = Flask(__name__)


def proxy(method: str, url: str, passthrough_headers=(), **kwargs):
    try:
        upstream = requests.request(method, url, timeout=5, **kwargs)
    except requests.RequestException:
        return jsonify({"detail": "Upstream service unavailable"}), 502
    response = Response(
        upstream.content,
        status=upstream.status_code,
        content_type=upstream.headers.get("Content-Type", "application/json"),
    )
    for header in passthrough_headers:
        if header in upstream.headers:
            response.headers[header] = upstream.headers[header]
    return response


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "frontend"})


@app.get("/api/services")
def services_status():
    result = {"frontend": "up"}
    for name, base_url in SERVICES.items():
        try:
            ok = requests.get(f"{base_url}/health", timeout=2).status_code == 200
        except requests.RequestException:
            ok = False
        result[name] = "up" if ok else "down"
    return jsonify(result)


@app.route("/api/tasks", methods=["GET", "POST"])
def tasks():
    if request.method == "POST":
        return proxy("POST", f"{BACKEND_URL}/api/tasks", json=request.get_json(silent=True))
    return proxy("GET", f"{BACKEND_URL}/api/tasks", params=request.args)


@app.route("/api/tasks/<int:task_id>", methods=["PUT", "DELETE"])
def task_detail(task_id: int):
    if request.method == "PUT":
        return proxy("PUT", f"{BACKEND_URL}/api/tasks/{task_id}", json=request.get_json(silent=True))
    return proxy("DELETE", f"{BACKEND_URL}/api/tasks/{task_id}")


@app.get("/api/stats")
def stats():
    return proxy("GET", f"{BACKEND_URL}/api/stats")


@app.get("/api/notifications")
def notifications():
    return proxy("GET", f"{NOTIFICATION_URL}/api/notifications", params={"limit": 10})


@app.get("/api/reports/summary")
def report_summary():
    return proxy("GET", f"{REPORT_URL}/api/reports/summary")


@app.get("/reports/export.csv")
def report_export():
    return proxy(
        "GET",
        f"{REPORT_URL}/api/reports/export.csv",
        passthrough_headers=("Content-Disposition",),
    )


if __name__ == "__main__":
    app.run(host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", "3000")))
