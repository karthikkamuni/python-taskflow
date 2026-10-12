import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Query
from pydantic import BaseModel, Field

from .store import NotificationStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("taskflow.notifications")

app = FastAPI(title="TaskFlow Notification Service", version="1.0.0")
store = NotificationStore(os.getenv("REDIS_URL", ""))


class NotificationIn(BaseModel):
    event_type: str = Field(min_length=1, max_length=50)
    task_id: Optional[int] = None
    message: str = Field(min_length=1, max_length=500)


@app.get("/health")
def health():
    return {"status": "ok", "service": "notification-service", "storage": store.backend}


@app.post("/api/notifications", status_code=201)
def create_notification(payload: NotificationIn):
    item = {
        "id": uuid.uuid4().hex[:12],
        "created_at": datetime.now(timezone.utc).isoformat(),
        **payload.model_dump(),
    }
    store.add(item)
    logger.info("notification: %s - %s", item["event_type"], item["message"])
    return item


@app.get("/api/notifications")
def list_notifications(limit: int = Query(20, ge=1, le=100)):
    return store.latest(limit)
