# TaskFlow: a multi-service Python app for practising DevOps

A small task manager split into independent services. It is built so you can write
a **Dockerfile per service**, a **docker-compose file**, and a **Jenkins pipeline**
yourself. No Docker or Jenkins files are included on purpose.

## Architecture

```
                    Browser
                       |
                       v
              +-----------------+
              |    frontend     |  Flask, port 3000
              |  (UI + proxy)   |
              +--------+--------+
        +--------------+---------------+
        v              v               v
 +-------------+ +--------------+ +----------------------+
 |   backend   | | report-svc   | | notification-service |
 | FastAPI     | | FastAPI      | | FastAPI              |
 | port 8000   | | port 8002    | | port 8001            |
 +--+-------+--+ +------+-------+ +----------+-----------+
    |       |           |  calls backend      |
    |       +-----------|---------------------+  backend -> notification (events)
    v                   v                     v
 Database          (reads tasks)          Redis (optional)
 SQLite / PostgreSQL                      cache + notification store
```

| Service | Tech | Port | Role |
|---|---|---|---|
| `frontend` | Flask + vanilla JS | 3000 | Web UI; proxies API calls to the other services |
| `backend` | FastAPI + SQLAlchemy | 8000 | Task CRUD, stats (cached in Redis) |
| `notification-service` | FastAPI | 8001 | Receives task events, keeps the latest 100 |
| `report-service` | FastAPI + httpx | 8002 | Summary stats and CSV export, built from backend data |
| database | SQLite (local) / PostgreSQL | 5432 | Persistent task storage |
| cache | Redis (optional) | 6379 | Stats cache and notification store |

## Project structure

```
taskflow/
├── backend/                 # FastAPI + database access
│   ├── app/                 # main.py, models.py, schemas.py, database.py, cache.py, notifier.py, config.py
│   ├── tests/
│   ├── pytest.ini
│   └── requirements.txt
├── notification-service/
│   ├── app/                 # main.py, store.py
│   ├── tests/
│   └── requirements.txt
├── report-service/
│   ├── app/                 # main.py
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── app.py               # Flask app + proxy routes
│   ├── templates/index.html
│   ├── static/              # app.js, style.css
│   ├── tests/
│   └── requirements.txt
├── scripts/                 # setup.sh, run_local.sh, test_all.sh
├── requirements-dev.txt     # pytest + httpx (test-only)
├── .env.example             # every environment variable, documented
└── README.md
```

Each service has its own `requirements.txt` and its own test suite, so each one
can become its own Docker image.

## Install dependencies

Requires Python 3.10+ (developed on 3.13).

```bash
cd taskflow
./scripts/setup.sh
```

This creates `.venv/` and installs all four services plus the test tools. To do it by hand:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt \
            -r notification-service/requirements.txt \
            -r report-service/requirements.txt \
            -r frontend/requirements.txt \
            -r requirements-dev.txt
```

## Run the application

### Option A: one command

```bash
./scripts/run_local.sh
```

Open http://localhost:3000. Press `Ctrl+C` to stop everything. Logs go to `logs/`.

### Option B: each service in its own terminal

```bash
source .venv/bin/activate

# terminal 1
cd notification-service && uvicorn app.main:app --port 8001

# terminal 2
cd backend && uvicorn app.main:app --port 8000

# terminal 3
cd report-service && uvicorn app.main:app --port 8002

# terminal 4
cd frontend && python app.py
```

Interactive API docs: http://localhost:8000/docs, http://localhost:8001/docs, http://localhost:8002/docs

By default the backend uses a local SQLite file and Redis is switched off, so nothing
else needs to be installed. Once you have containers, point the services at PostgreSQL
and Redis through environment variables (see `.env.example`).

## Run the tests

```bash
./scripts/test_all.sh
```

Or a single service: `cd backend && python -m pytest -q`

## Environment variables

| Variable | Used by | Default | Purpose |
|---|---|---|---|
| `DATABASE_URL` | backend | `sqlite:///./taskflow.db` | e.g. `postgresql+psycopg2://taskflow:taskflow@db:5432/taskflow` |
| `REDIS_URL` | backend, notification-service | empty (disabled) | e.g. `redis://redis:6379/0` |
| `CACHE_TTL_SECONDS` | backend | `30` | Stats cache lifetime |
| `NOTIFICATION_SERVICE_URL` | backend | `http://localhost:8001` | Where task events are sent |
| `DB_CONNECT_RETRIES` / `DB_CONNECT_DELAY_SECONDS` | backend | `15` / `2` | Wait for a slow-starting database |
| `BACKEND_URL` | report-service, frontend | `http://localhost:8000` | Backend address |
| `NOTIFICATION_URL` | frontend | `http://localhost:8001` | Notification service address |
| `REPORT_URL` | frontend | `http://localhost:8002` | Report service address |
| `HOST` / `PORT` | frontend | `0.0.0.0` / `3000` | Bind address of the Flask dev server |

## Notes for your DevOps exercises

- **Health checks:** every service exposes `GET /health` (the backend also reports database and cache state). Use these for Docker `HEALTHCHECK` and compose `depends_on: condition: service_healthy`.
- **Service names:** inside compose, services reach each other by service name. Set `BACKEND_URL=http://backend:8000` and so on instead of `localhost`.
- **Bind address:** inside a container, start uvicorn with `--host 0.0.0.0`. For the frontend, `gunicorn -b 0.0.0.0:3000 app:app` is the production-style command.
- **Startup order:** the backend retries the database connection, so it survives PostgreSQL starting later.
- **Graceful degradation:** with Redis or the notification service down, the app keeps working. Stop one container and watch the status pills in the UI.
- **Jenkins:** a pipeline can run `pip install -r ...`, then `./scripts/test_all.sh`, then build one image per service.
- **Database driver:** `psycopg2-binary` is already in `backend/requirements.txt`, so PostgreSQL works without extra packages.
