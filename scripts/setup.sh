#!/usr/bin/env bash
# Creates a virtualenv in the project root and installs every service's dependencies.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python3 -m venv "$ROOT/.venv"
source "$ROOT/.venv/bin/activate"
python -m pip install --upgrade pip

for service in backend notification-service report-service frontend; do
  echo "==> installing $service"
  pip install -r "$ROOT/$service/requirements.txt"
done
pip install -r "$ROOT/requirements-dev.txt"

echo "Done. Next: ./scripts/run_local.sh"
