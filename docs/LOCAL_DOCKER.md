# Local Docker Setup

This project ships with a Docker-based development environment for the Django backend + React frontend, plus PostgreSQL and Redis.

## Prerequisites
- Docker Desktop (Windows/macOS) or Docker Engine + Compose

## Services
- backend: Django app, exposed at http://localhost:8080
- frontend: Vite React app, exposed at http://localhost:5173
- postgres: Postgres 16 with database `saas`
- redis: Redis 7 for queues/cache
- celery: Celery worker for background tasks/events
- celery_beat: Celery Beat scheduler for periodic tasks
- flower: Celery monitoring UI at http://localhost:5555

## Start the stack
```powershell
# From the repository root
docker compose up -d --build
```
This will:
- Build backend and frontend images
- Run database and redis
- Apply shared tenant migrations
- Start Django dev server on 0.0.0.0:8000 (host: 8080)
- Start Vite dev server on 0.0.0.0:5173

Access:
- Backend API: http://localhost:8080/api/v1/health
- Frontend app: http://localhost:5173
- Flower (queues): http://localhost:5555

## Logs and troubleshooting
```powershell
# Tail logs for a service (backend, frontend, celery)
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f celery
docker compose logs -f celery_beat
docker compose logs -f flower

# Bring everything down
docker compose down

# Bring down and remove volumes (⚠ deletes DB data)
docker compose down -v
```

## Notes
- Frontend uses a dev proxy: all `/api` calls go to `http://backend:8000` inside the Compose network. Axios base URL is relative, so no CORS is required in dev.
- To change backend or frontend ports, edit `ports` in `docker-compose.yml` and update any env/proxy if needed.
- For first-time DB setup beyond shared tenant tables, run additional migrations/commands as required.

## Seeding (optional)
You can seed a localhost tenant and a test user from within the backend container:

```powershell
# Map localhost/testserver to the public tenant and create it if missing
docker compose exec -T backend sh -lc "python seed_localhost_tenant.py"

# Create a test user (see script for env-controlled password)
docker compose exec -T backend sh -lc "python create_test_user.py"
```

## Production notes (optional)
- Use Gunicorn image for backend: build with `backend/Dockerfile.prod`.
- Set security env vars in production: `IS_PRODUCTION=true`, `SECURE_SSL_REDIRECT=true`, `SESSION_COOKIE_SECURE=true`, `CSRF_COOKIE_SECURE=true`, and `CSRF_TRUSTED_ORIGINS` (e.g., `https://app.example.com`).
- If behind a proxy/load balancer, ensure `X-Forwarded-Proto` is passed; `SECURE_PROXY_SSL_HEADER` is already configured when `IS_PRODUCTION=true`.
