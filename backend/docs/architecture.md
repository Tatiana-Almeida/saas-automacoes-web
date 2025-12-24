# Arquitetura do Sistema

Resumo rápido:

- Backend: Django 5 + Django REST Framework
- Multi-tenancy: `django-tenants` (PostgreSQL schemas)
- Cache / Broker: Redis (caching, Celery broker)
- Tarefas em background: Celery
- Observabilidade: logging centralizado; exportador opcional para Elasticsearch

Componentes principais:

- `apps.core`: endpoints e infra comum (autenticação por cookie JWT, renderers, middlewares)
- `apps.users`: gestão de usuários
- `apps.tenants`: modelos de tenant e domain
- `apps.rbac`: permissões e roles
- `apps.auditing`: logs e DLQ
- `apps.support`: tickets de suporte (novo)

Fluxos principais:

- Autenticação: usuário obtém JWT via endpoints em `apps.core`, token armazenado em cookie seguro.
- Requests: `django-tenants` resolve tenant via hostname (Domain) e seleciona schema adequado.
- Webhooks: verificação HMAC/Stripe e idempotência via Redis.
