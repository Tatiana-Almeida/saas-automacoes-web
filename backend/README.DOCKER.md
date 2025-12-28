Docker Compose (Postgres + Redis + Django)
----------------------------------------

Quick steps to run the backend with Docker Compose (requires Docker Desktop):

1. Copy `.env.example` to `.env` and review values (optional):

   cp .env.example .env

2. Start services:

   docker compose up -d

   This will run Postgres, Redis and build the Django image, run migrations and start the dev server on port 8000.

3. Verify services are up:

   docker compose ps

4. To view logs:

   docker compose logs -f django

5. To stop and remove containers:

   docker compose down

Notes:
- Environment variables come from `.env`; `DATABASE_URL` and `REDIS_URL` are preconfigured in `.env.example`.
- The compose file runs `python manage.py migrate` on container start; you can run shell or createsuperuser by:

   docker compose exec django python manage.py createsuperuser

When Docker is installed, run the commands above and then test endpoints (e.g., register/login) at `http://localhost:8000`.
