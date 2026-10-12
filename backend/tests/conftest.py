import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import cache, notifier
from app.database import Base, get_db
from app.main import app


@pytest.fixture()
def events(monkeypatch):
    """Captures notification events instead of calling the real service."""
    captured = []
    monkeypatch.setattr(notifier, "send_event", lambda *args: captured.append(args))
    return captured


@pytest.fixture()
def client(monkeypatch, events):
    # Isolated in-memory database per test.
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    # In-memory stand-in for Redis.
    store = {}
    monkeypatch.setattr(cache, "cache_get", lambda key: store.get(key))
    monkeypatch.setattr(cache, "cache_set", lambda key, value, ttl=0: store.__setitem__(key, value))
    monkeypatch.setattr(cache, "cache_delete", lambda *keys: [store.pop(k, None) for k in keys])

    yield TestClient(app)  # no `with`: skips lifespan, so no real DB is touched
    app.dependency_overrides.clear()
