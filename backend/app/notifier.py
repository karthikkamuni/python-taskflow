"""Fire-and-forget calls to the notification service."""
import logging

import httpx

from .config import NOTIFICATION_SERVICE_URL

logger = logging.getLogger("taskflow.notifier")


def send_event(event_type: str, task_id: int, message: str) -> None:
    payload = {"event_type": event_type, "task_id": task_id, "message": message}
    try:
        httpx.post(f"{NOTIFICATION_SERVICE_URL}/api/notifications", json=payload, timeout=2.0)
    except httpx.HTTPError as exc:
        # A notification failure must never break the main request.
        logger.warning("could not reach notification service: %s", exc)
