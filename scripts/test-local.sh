#!/usr/bin/env bash
set -euo pipefail

# Script to run tests inside the `backend` container (interactive dev container)
# Usage: ./scripts/test-local.sh [pytest-args]

cd "$(dirname "$0")/.."

echo "Starting backend-dev container (detached) if not already running..."
docker compose up -d backend || true

echo "Opening one-off exec to run pytest inside backend service..."
docker exec backend-dev sh -c "cd /code && export DATABASE_URL='postgres://postgres:postgres@postgres:5432/saas' DB_HOST=postgres && python -m pytest $* --ds=saas_backend.settings"
