import logging
import time
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query, Response
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from . import cache, config, notifier
from .database import Base, engine, get_db
from .models import Task
from .schemas import Status, TaskCreate, TaskOut, TaskUpdate

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("taskflow.backend")

STATS_CACHE_KEY = "taskflow:stats"


def init_db() -> None:
    """Create tables, retrying while the database container is still booting."""
    for attempt in range(1, config.DB_CONNECT_RETRIES + 1):
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("database ready")
            return
        except OperationalError as exc:
            logger.warning(
                "database not ready (attempt %s/%s): %s",
                attempt,
                config.DB_CONNECT_RETRIES,
                exc.__class__.__name__,
            )
            time.sleep(config.DB_CONNECT_DELAY_SECONDS)
    raise RuntimeError("could not connect to the database")


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="TaskFlow Backend", version="1.0.0", lifespan=lifespan)


@app.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        database = "up"
    except Exception:  # noqa: BLE001 - any DB failure means unhealthy
        database = "down"
    body = {
        "status": "ok" if database == "up" else "degraded",
        "service": "backend",
        "database": database,
        "cache": cache.cache_status(),
    }
    return JSONResponse(body, status_code=200 if database == "up" else 503)


@app.get("/api/tasks", response_model=List[TaskOut])
def list_tasks(
    status: Optional[Status] = None,
    limit: int = Query(500, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    query = select(Task).order_by(Task.id.desc()).limit(limit)
    if status:
        query = query.where(Task.status == status)
    return db.scalars(query).all()


@app.post("/api/tasks", response_model=TaskOut, status_code=201)
def create_task(payload: TaskCreate, background: BackgroundTasks, db: Session = Depends(get_db)):
    task = Task(**payload.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    cache.cache_delete(STATS_CACHE_KEY)
    background.add_task(notifier.send_event, "task_created", task.id, f"Task created: {task.title}")
    return task


@app.get("/api/tasks/{task_id}", response_model=TaskOut)
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.put("/api/tasks/{task_id}", response_model=TaskOut)
def update_task(
    task_id: int,
    payload: TaskUpdate,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
):
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    cache.cache_delete(STATS_CACHE_KEY)
    background.add_task(
        notifier.send_event, "task_updated", task.id, f"Task updated: {task.title} ({task.status})"
    )
    return task


@app.delete("/api/tasks/{task_id}", status_code=204)
def delete_task(task_id: int, background: BackgroundTasks, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    title = task.title
    db.delete(task)
    db.commit()
    cache.cache_delete(STATS_CACHE_KEY)
    background.add_task(notifier.send_event, "task_deleted", task_id, f"Task deleted: {title}")
    return Response(status_code=204)


@app.get("/api/stats")
def stats(db: Session = Depends(get_db)):
    cached = cache.cache_get(STATS_CACHE_KEY)
    if cached is not None:
        return {**cached, "cached": True}

    rows = db.execute(select(Task.status, func.count()).group_by(Task.status)).all()
    by_status = {"todo": 0, "in_progress": 0, "done": 0}
    for status, count in rows:
        by_status[status] = count
    data = {"total": sum(by_status.values()), "by_status": by_status}
    cache.cache_set(STATS_CACHE_KEY, data)
    return {**data, "cached": False}
