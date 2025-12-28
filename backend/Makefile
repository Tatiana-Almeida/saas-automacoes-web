.PHONY: up down logs migrate createsuperuser shell build scan smoke

COMPOSE=docker compose

up:
	$(COMPOSE) up -d --build

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f django

build:
	$(COMPOSE) build django

migrate:
	$(COMPOSE) exec django python manage.py migrate

createsuperuser:
	$(COMPOSE) exec django python manage.py createsuperuser

shell:
	$(COMPOSE) exec django python manage.py shell

scan:
	# Runs Snyk code scan if Snyk CLI is installed
	@snyk code test ./ || echo "snyk not installed or scan failed"

smoke:
	# Runs PowerShell smoke test against local Django on Docker
	@powershell -ExecutionPolicy Bypass -File scripts/smoke.ps1 -BaseUrl http://localhost:8000

openapi:
	# Generate OpenAPI schema file via drf-spectacular (Docker required)
	$(COMPOSE) run --rm django python manage.py spectacular --file openapi.yaml
	@echo "OpenAPI generated at backend/openapi.yaml"
