#!/usr/bin/env bash
set -euo pipefail

# init-db.sh
# Idempotent script to ensure DB role, test DB and run migrations inside docker-compose
# Usage: ./scripts/init-db.sh [POSTGRES_CONTAINER] [DJANGO_CONTAINER]

POSTGRES_CONTAINER=${1:-postgres-saas}
DJANGO_CONTAINER=${2:-django}

echo "Postgres container: $POSTGRES_CONTAINER"
echo "Django container: $DJANGO_CONTAINER"

echo "==> Ensuring role 'saas_user' exists with CREATEDB"
# create or update role and grant CREATEDB
docker exec -i "$POSTGRES_CONTAINER" psql -U postgres -c "DO \$\$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='saas_user') THEN CREATE ROLE saas_user LOGIN PASSWORD '1234567890'; ELSE ALTER ROLE saas_user WITH PASSWORD '1234567890'; END IF; END \$\$;"

docker exec -i "$POSTGRES_CONTAINER" psql -U postgres -c "ALTER ROLE saas_user CREATEDB;"

echo "==> Ensuring test database exists and is owned by saas_user"
# Create DB only if missing
docker exec -i "$POSTGRES_CONTAINER" bash -c "psql -U postgres -tc \"SELECT 1 FROM pg_database WHERE datname='test_saas_automacoes_web'\" | grep -q 1 || psql -U postgres -c \"CREATE DATABASE test_saas_automacoes_web OWNER saas_user\""

echo "==> Running Django migrations (inside $DJANGO_CONTAINER if present)"
if docker ps --format "{{.Names}}" | grep -q "^$DJANGO_CONTAINER$"; then
  docker exec -i "$DJANGO_CONTAINER" python manage.py migrate --no-input
else
  echo "Django container '$DJANGO_CONTAINER' not found; skipping automatic migrate."
  echo "You can run migrations manually inside your Django environment:" 
  echo "  docker exec -it $DJANGO_CONTAINER python manage.py migrate --no-input"
fi

echo "==> Done."
