#!/usr/bin/env bash
# Starts all four services locally. Press Ctrl+C to stop them all.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/.venv/bin/activate"
mkdir -p "$ROOT/logs"

pids=()
cleanup() {
  echo
  echo "Stopping services..."
  kill "${pids[@]}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

start() {
  local name=$1 dir=$2
  shift 2
  (cd "$ROOT/$dir" && exec "$@") >"$ROOT/logs/$name.log" 2>&1 &
  pids+=($!)
  echo "started $name (pid $!) -> logs/$name.log"
}

export NOTIFICATION_SERVICE_URL="${NOTIFICATION_SERVICE_URL:-http://localhost:8001}"
export BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
export NOTIFICATION_URL="${NOTIFICATION_URL:-http://localhost:8001}"
export REPORT_URL="${REPORT_URL:-http://localhost:8002}"

start notification-service notification-service uvicorn app.main:app --port 8001
start backend              backend              uvicorn app.main:app --port 8000
start report-service       report-service       uvicorn app.main:app --port 8002
start frontend             frontend             python app.py

echo
echo "TaskFlow is starting:"
echo "  Frontend            http://localhost:3000"
echo "  Backend API docs    http://localhost:8000/docs"
echo "  Notification docs   http://localhost:8001/docs"
echo "  Report docs         http://localhost:8002/docs"
wait
