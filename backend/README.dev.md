# Development Quickstart

This file documents the minimal steps to get a clean dev/test environment and fix the immediate blockers observed when running tests locally.

Prerequisites
- Docker & Docker Compose (or `docker compose`)
- Python (for running tests locally) or run tests inside the `django` container

Quick setup (PowerShell)
```powershell
# from repo backend/ folder
cd "C:\Users\Tatiana Almeida\Documents\SAAS\SAAS DE AUTOMAÇÕES WEB\backend"

# 1) Start services
docker compose up -d --build

# 2) Ensure the non-superuser role exists and can CREATE DB
docker exec -it postgres-saas psql -U postgres -c "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='saas_user') THEN CREATE ROLE saas_user LOGIN PASSWORD '1234567890'; ELSE ALTER ROLE saas_user WITH PASSWORD '1234567890'; END IF; END $$;"
docker exec -it postgres-saas psql -U postgres -c "ALTER ROLE saas_user CREATEDB;"

# 3) Create test DB owned by saas_user (so Django doesn't need to CREATE it)
docker exec -it postgres-saas psql -U postgres -c "CREATE DATABASE test_saas_automacoes_web OWNER saas_user;"

# 4) Apply migrations (run in django container or locally using same DB settings)
# Option A: inside container
docker exec -it $(docker ps --filter "name=django" --format "{{.ID}}") python manage.py migrate --no-input
# Option B: locally (if you use DB host 127.0.0.1 and env configured)
# python manage.py migrate --no-input

# 5) Seed required data (tenants, RBAC)
docker exec -it postgres-saas psql -U postgres -c "\dt"  # sanity check
# Example: run management commands provided in the repo
docker exec -it $(docker ps --filter "name=django" --format "{{.ID}}") python manage.py seed_plans
docker exec -it $(docker ps --filter "name=django" --format "{{.ID}}") python manage.py seed_rbac

# 6) Run a focused test (from backend folder)
# Prefer running tests inside same network (host connects to 127.0.0.1:5432 which is published by Docker compose)
python -m pytest tests/test_events.py::test_plan_upgraded_event_emitted_on_plan_change -vv --ds=saas_backend.settings -s -x
```

Notes & Recommendations
- Do NOT use `--reuse-db` during debugging runs; it preserves inconsistent DB state and causes duplicate-key / missing-table issues.
- `apps.tenants.apps._ensure_public_domains_for_testing()` currently touches the DB during `AppConfig.ready()` and can cause tests to query DB before migrations run. Consider moving tenant seeding into a management command and running it after `migrate`.
- Add these automation steps to `docker-entrypoint` or an init script in CI so the role, test DB and migrations are always present for test runs.

Useful commands
- View Postgres logs:
```powershell
docker logs -f postgres-saas
```
- Drop test DB (if you need to recreate):
```powershell
docker exec -it postgres-saas psql -U postgres -c "DROP DATABASE IF EXISTS test_saas_automacoes_web;"
```
- Create test DB owner check:
```powershell
docker exec -it postgres-saas psql -U postgres -c "SELECT datname, pg_catalog.pg_get_userbyid(datdba) AS owner FROM pg_database WHERE datname='test_saas_automacoes_web';"
```

CI checklist (minimum)
- Start Postgres + Redis
- Ensure `saas_user` exists + CREATEDB
- Create or allow creation of `test_saas_automacoes_web`
- Run `python manage.py migrate`
- Run seed management commands (tenants, RBAC)
- Run `pytest` (no `--reuse-db`)

If you want, I can:
- add a small `scripts/` entry (bash/ps1) to automate steps 2–5, or
- create a `README.dev.md` improvement with WSL/Linux commands and a `Makefile`.

Which automation would you like next? (create scripts, add CI job template, or refactor `apps.tenants.apps._ensure_public_domains_for_testing()` now?)
