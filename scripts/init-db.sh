#!/bin/sh
set -euo pipefail

echo "[init-db] waiting for Postgres to become available..."

RETRIES=${RETRIES:-60}
SLEEP=${SLEEP:-1}

i=0
while [ $i -lt $RETRIES ]; do
  i=$((i + 1))
  # Use Python to test TCP connect so this script works even if pg_isready
  # or psql are not available in the image.
  if python - <<'PY' >/dev/null 2>&1; then
import socket,sys
try:
    s=socket.socket()
    s.settimeout(1)
    s.connect(("postgres", 5432))
    s.close()
    sys.exit(0)
except Exception:
    sys.exit(1)
PY
  then
    echo "[init-db] Postgres is available (attempt $i)"
    break
  fi
  echo "[init-db] Postgres not available yet (attempt $i/$RETRIES); sleeping ${SLEEP}s"
  sleep $SLEEP
done

if [ $i -eq $RETRIES ]; then
  echo "[init-db] timed out waiting for Postgres after ${RETRIES} attempts"
  exit 1
fi

echo "[init-db] running Django migrations (idempotent)..."

# Run standard migrations first; fail loudly if they error.
python manage.py migrate --noinput

# Run shared tenant migrations. Retry a few times to tolerate race
# conditions when multiple containers attempt migrations simultaneously.
# Make attempts and backoff configurable via env vars for CI/containers.
ATTEMPTS=${MIGRATE_ATTEMPTS:-6}
BACKOFF_BASE=${MIGRATE_BACKOFF_BASE:-2}
for a in $(seq 1 $ATTEMPTS); do
  echo "[init-db] running migrate_schemas --shared (attempt $a/$ATTEMPTS)"
  if python manage.py migrate_schemas --shared --noinput; then
    echo "[init-db] migrate_schemas --shared completed"
    break
  fi
  # Linear backoff: increase sleep each attempt. Using a configurable
  # base prevents extremely long sleeps in CI while still spacing retries.
  sleep_seconds=$((a * BACKOFF_BASE))
  echo "[init-db] migrate_schemas failed (attempt $a); retrying after ${sleep_seconds}s"
  sleep $sleep_seconds
  if [ $a -eq $ATTEMPTS ]; then
    echo "[init-db] migrate_schemas failed after ${ATTEMPTS} attempts"
    exit 1
  fi
done

echo "[init-db] database initialization complete"

exit 0
