#!/usr/bin/env bash
# Runs the unit tests of every service (each in its own directory).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/.venv/bin/activate"

for service in backend notification-service report-service frontend; do
  echo "==> testing $service"
  (cd "$ROOT/$service" && python -m pytest -q)
done
echo "All tests passed."
