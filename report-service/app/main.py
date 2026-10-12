import csv
import io
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("taskflow.reports")

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

app = FastAPI(title="TaskFlow Report Service", version="1.0.0")


def fetch_tasks() -> List[Dict[str, Any]]:
    """Pull all tasks from the backend service."""
    try:
        response = httpx.get(f"{BACKEND_URL}/api/tasks", timeout=5.0)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as exc:
        logger.warning("backend unavailable: %s", exc)
        raise HTTPException(status_code=502, detail="Backend service unavailable") from exc


def build_summary(tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_status = {"todo": 0, "in_progress": 0, "done": 0}
    by_priority = {"low": 0, "medium": 0, "high": 0}
    for task in tasks:
        by_status[task["status"]] = by_status.get(task["status"], 0) + 1
        by_priority[task["priority"]] = by_priority.get(task["priority"], 0) + 1

    total = len(tasks)
    completion_rate = round(by_status["done"] / total * 100, 1) if total else 0.0
    return {
        "total": total,
        "by_status": by_status,
        "by_priority": by_priority,
        "completion_rate": completion_rate,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _csv_safe(value: Any) -> Any:
    """Stop spreadsheet apps from executing cells that start with = + - @."""
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@"):
        return "'" + value
    return value


@app.get("/health")
def health():
    return {"status": "ok", "service": "report-service"}


@app.get("/api/reports/summary")
def summary():
    return build_summary(fetch_tasks())


@app.get("/api/reports/export.csv")
def export_csv():
    tasks = fetch_tasks()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["id", "title", "status", "priority", "created_at"])
    for task in tasks:
        writer.writerow(
            [
                task["id"],
                _csv_safe(task["title"]),
                task["status"],
                task["priority"],
                task["created_at"],
            ]
        )
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="tasks.csv"'},
    )
