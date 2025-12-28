# MÓDULO 0 — Visão Geral do Projeto

## Objetivo do Projeto
- Entregar um backend SaaS para automações, escalável e pronto para produção.
- API REST com autenticação JWT, organização modular por apps e configuração via `.env`.
- Base adequada para e-commerce de automações: produtos, pedidos, assinaturas e notificações.

## Arquitetura Geral
- Monorepo com serviços principais e documentação.
- Backend Django + DRF em [backend-starter](../backend-starter/README.md) com split de settings:
  - Base: [starter/settings/base.py](../backend-starter/starter/settings/base.py)
  - Dev: [starter/settings/dev.py](../backend-starter/starter/settings/dev.py)
  - Prod: [starter/settings/prod.py](../backend-starter/starter/settings/prod.py)
- Autenticação JWT (email como login) e CORS habilitado:
  - Rotas JWT: definidas em [starter/urls.py](../backend-starter/starter/urls.py)
  - Serializer/endpoint custom: [starter/users/auth.py](../backend-starter/starter/users/auth.py)
- Estrutura de APIs por app sob `api/` (serializers, views, urls), com permissões e base compartilhada:
  - Shared: [starter/api/views.py](../backend-starter/starter/api/views.py), [starter/api/serializers.py](../backend-starter/starter/api/serializers.py), [starter/api/permissions.py](../backend-starter/starter/api/permissions.py)
- Banco de dados PostgreSQL via `DATABASE_URL` ou variáveis discretas; Email via `EMAIL_*`.
- Docker e Compose para desenvolvimento; Gunicorn para produção.

## Estrutura das Apps
- `starter/users` (principal de autenticação)
  - Modelo custom `User` com login por email: [starter/users/models.py](../backend-starter/starter/users/models.py)
  - API `me`: [starter/users/api/views.py](../backend-starter/starter/users/api/views.py) e [starter/users/api/urls.py](../backend-starter/starter/users/api/urls.py)
- `starter/tenants` (base de tenants)
  - Modelo `Tenant`: [starter/tenants/models.py](../backend-starter/starter/tenants/models.py)
  - API CRUD: [starter/tenants/api](../backend-starter/starter/tenants/api)
- `starter/products`
  - Modelo `Product`: [starter/products/models.py](../backend-starter/starter/products/models.py)
  - API CRUD: [starter/products/api](../backend-starter/starter/products/api)
- `starter/orders`
  - Modelo `Order` (FK `user`, total, status): [starter/orders/models.py](../backend-starter/starter/orders/models.py)
  - API CRUD: [starter/orders/api](../backend-starter/starter/orders/api)
- `starter/automations`
  - Modelo `Automation` (tipo): [starter/automations/models.py](../backend-starter/starter/automations/models.py)
  - API CRUD: [starter/automations/api](../backend-starter/starter/automations/api)
- `starter/subscriptions`
  - Modelo `Subscription` (FK `user`, plano, status): [starter/subscriptions/models.py](../backend-starter/starter/subscriptions/models.py)
  - API CRUD: [starter/subscriptions/api](../backend-starter/starter/subscriptions/api)
- `starter/notifications`
  - Modelo `Notification`: [starter/notifications/models.py](../backend-starter/starter/notifications/models.py)
  - API CRUD: [starter/notifications/api](../backend-starter/starter/notifications/api)

## Tecnologias Usadas
- Backend: Django 5, Django REST Framework, SimpleJWT, python-decouple, django-cors-headers, dj-database-url.
- Banco: PostgreSQL.
- Runtime: Gunicorn.
- Contêineres: Docker, Docker Compose.
- Segurança: Snyk (SAST/Policy) e boas práticas (HSTS/SSL/TLS).
- Editor: VS Code.

## Próximos Módulos
- Módulo 1 — Tenancy: FKs `tenant` nas entidades e filtragem no `TenantScopedViewSet`.
- Módulo 2 — RBAC: políticas por `role` (admin/cliente) e escopos por dono.
- Módulo 3 — E-commerce: lógica de pedidos, carrinho e integração de pagamentos.
- Módulo 4 — Automações: engine de workflows, webhooks e agendamentos.
- Módulo 5 — Observabilidade: auditoria, métricas e alertas.
- Módulo 6 — CI/CD: pipelines, versionamento e deploy.
- Módulo 7 — Frontend: app React, guards, integração com APIs.
