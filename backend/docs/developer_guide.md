# Guia do Desenvolvedor

Estrutura do projeto:

- `saas_backend/` — configurações do Django e URLs públicas
- `apps/` — apps Django por domínio (core, users, tenants, rbac, auditing, support, ...)
- `tests/` — testes com pytest
- `scripts/` — utilitários (criar DB de testes, seeds)

Como rodar localmente (resumo):

1. Configure `.env` com `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`.
2. Crie DB Postgres e execute migrations: `python manage.py migrate`.
3. Execute Celery em desenvolvimento: `celery -A saas_backend worker -l info`.

Testes:
- Unitários rápidos: use `saas_backend.settings_test` (SQLite) via `pytest -q`.
- Integração multi-tenant: use `saas_backend.settings_test_pg` com Postgres local.
