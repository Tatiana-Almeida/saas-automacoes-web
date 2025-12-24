# Production Readiness Guide

## Overview
This project is configured for secure, scalable, and performant deployments.

## Security
- Rate limiting via DRF throttling (`anon`, `user`, `login`), configurable by env.
- CORS and CSRF configured with env allowlists.
- Security headers enabled in `starter/settings/prod.py` and env toggles (HSTS, SSL redirect, X-Frame-Options, Referrer-Policy).
- Separate `security` logger for sensitive events (login success/failure, etc.).

## Performance & Scalability
- Redis-backed cache when `REDIS_URL` is set; fallback to local memory.
- GZip compression enabled for dynamic responses.
- WhiteNoise serves static files with compressed manifest.
- Optional full-page cache middleware (enable via `CACHE_MIDDLEWARE_SECONDS` > 0).

## Docker & Compose
- `Dockerfile` installs dependencies, runs migrations, collects static, then starts Gunicorn.
- `docker-compose.yml` includes services: web (Django), postgres, redis.
- Uses `.env` for configuration, including DB, CORS/CSRF, throttling, and security flags.

## Environments
- `starter/settings/dev.py`: developer-friendly (DEBUG on, Browsable API).
- `starter/settings/prod.py`: hardened defaults and SSL/HSTS.
- Set `DJANGO_SETTINGS_MODULE` via env (e.g., `starter.settings.prod`).

## Static Files
- WhiteNoise enabled; static files collected into `staticfiles`.
- Configure CDN in front of the app for best performance.

## Load Testing
- `locustfile.py` included; run:

```bash
locust -f locustfile.py --host=http://localhost:8000
```

## Logging
- Structured logs available via `python-json-logger` (formatter `json`), console handlers by default.
- Separate `security` logger; use it in auth/payment/critical flows.

## Recommended Env
- `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`
- `DATABASE_URL` or discrete DB vars
- `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`
- Security toggles: `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `X_FRAME_OPTIONS`

## Deployment
- Containerize with provided Dockerfile.
- Use reverse proxy/ingress (NGINX/Load Balancer) to terminate TLS and forward traffic.
- Configure health checks and scaling via replicas.

