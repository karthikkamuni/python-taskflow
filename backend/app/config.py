"""All configuration comes from environment variables (12-factor style)."""
import os

# SQLite by default so the app runs with zero setup.
# For PostgreSQL use: postgresql+psycopg2://user:password@host:5432/dbname
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./taskflow.db")

# Redis cache is optional: leave REDIS_URL empty to disable caching.
REDIS_URL = os.getenv("REDIS_URL", "")
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "30"))

NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://localhost:8001")

# The database container may start slower than the API, so retry on startup.
DB_CONNECT_RETRIES = int(os.getenv("DB_CONNECT_RETRIES", "15"))
DB_CONNECT_DELAY_SECONDS = float(os.getenv("DB_CONNECT_DELAY_SECONDS", "2"))
