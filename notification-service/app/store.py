"""Notification storage: Redis when REDIS_URL is set, in-memory otherwise."""
import json
import logging
from collections import deque
from typing import Deque, List, Optional

import redis

logger = logging.getLogger("taskflow.notifications")

REDIS_KEY = "taskflow:notifications"
MAX_ITEMS = 100


class NotificationStore:
    def __init__(self, redis_url: Optional[str] = None):
        self._memory: Deque[dict] = deque(maxlen=MAX_ITEMS)
        self._redis = (
            redis.Redis.from_url(
                redis_url, socket_connect_timeout=1, socket_timeout=1, decode_responses=True
            )
            if redis_url
            else None
        )

    @property
    def backend(self) -> str:
        return "redis" if self._redis else "memory"

    def add(self, item: dict) -> None:
        if self._redis:
            try:
                pipe = self._redis.pipeline()
                pipe.lpush(REDIS_KEY, json.dumps(item))
                pipe.ltrim(REDIS_KEY, 0, MAX_ITEMS - 1)
                pipe.execute()
                return
            except redis.RedisError as exc:
                logger.warning("redis unavailable, using memory: %s", exc)
        self._memory.appendleft(item)

    def latest(self, limit: int = 20) -> List[dict]:
        if self._redis:
            try:
                return [json.loads(x) for x in self._redis.lrange(REDIS_KEY, 0, limit - 1)]
            except redis.RedisError as exc:
                logger.warning("redis unavailable, using memory: %s", exc)
        return list(self._memory)[:limit]
