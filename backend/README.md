Testes automatizados (pytest)

```powershell
```
```powershell
# Windows (sem Docker): criar venv e instalar dependências
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Executar testes (usa settings saas_backend.settings)
pytest
```

Observações:
- Os testes cobrem: login com Cookie + acesso a /users/me e criação de logs pela auditoria.
- Para cenários multi-tenant avançados, execute via Docker/compose para isolar schemas.
Tenant suspenso retorna 403 em todas as rotas (middleware `EnforceActiveTenantMiddleware`)

CLI de tenants (atalhos):
```powershell
```
Exemplos (cURL - Linux/macOS):
```bash
# Health
curl -s http://localhost:8000/api/v1/health | jq

# Auditoria: filtros combinados
curl -s -H "Authorization: Bearer $ACCESS" \
	"http://localhost:8000/api/v1/auditing/logs?user_id=42&method=GET&created_after=2025-06-01T00:00:00Z&page=2&page_size=25&ordering=-created_at" | jq
```
# Backend (Django + DRF, Multi-tenant)

Quickstart (API-first)
- Docker (recommended):
```powershell
cd backend
cp .env.example .env
docker compose up -d --build
```
- Health check:
```powershell
Invoke-RestMethod -Method GET "http://localhost:8000/api/v1/health"
```
- Swagger docs:
```powershell
Start-Process "http://localhost:8000/api/docs"  # drf-spectacular
Start-Process "http://localhost:8000/api/swagger/"  # drf-yasg
```
- Local (without Docker): see section "Opção 2: Local (Python + Postgres + Redis)" abaixo.


Arquitetura:
- API-first com Django 5 + DRF (sem templates/views server-side para páginas)
- Multi-tenancy com `django-tenants` (schemas PostgreSQL), `Tenant`/`Domain`
- JWT com `djangorestframework-simplejwt` (registro, login, refresh, logout, blacklist)
- Cookies HttpOnly/Secure para Access Token (além de Authorization header)
- OpenAPI/Swagger com `drf-spectacular`
 - Swagger/OpenAPI alternativo com `drf-yasg`
- Variáveis via `.env` com `django-environ`
- Redis para cache (throttling multi-worker)
- Throttling per-tenant/plan com `PlanScopedRateThrottle` + limites diários via `PlanLimitMiddleware`
- Módulos: `apps.core`, `apps.users`, `apps.tenants`
 - Módulos adicionais: `apps.whatsapp`, `apps.mailer`, `apps.sms`, `apps.chatbots`, `apps.workflows`, `apps.ai`

Endpoints:
- GET `/api/v1/health` (público)
- POST `/api/v1/auth/register` (público)
- POST `/api/v1/auth/token` (login, username ou email)
- POST `/api/v1/auth/refresh` (renova access)
- POST `/api/v1/auth/logout` (blacklist refresh, JWT)
- Login/Refresh também definem cookie `access_token` (HttpOnly + Secure configurável)
- GET `/api/v1/users/me` (JWT)
- GET `/api/v1/admin/ping` (JWT + admin)
- GET `/api/v1/core/throttle/status` (JWT + admin, mostra uso de rate limits)
- GET `/api/v1/core/throttle/daily/summary` (JWT + admin, resumo diário por categoria)
- GET `/api/v1/core/queues/status` (JWT + admin, status de Redis/Celery/filas e DLQ)
	- Inclui profundidade de filas (best-effort) e inspeção Celery (workers e tarefas ativas), quando disponível.
- GET `/api/v1/auditing/logs` (JWT + admin, filtros: `user_id`, `method`, `source`, `action`, `tenant_schema`, `status_code`, `path_contains`, `created_after`, `created_before`)
	- Paginação e ordenação: use `?page=1&page_size=50&ordering=-created_at` (campos permitidos para `ordering`: `created_at`, `method`, `path`, `user`)

Exemplos (Auditoria):
Padrão de respostas (DRF)
- Sucesso (2xx):
```json
{
	"success": true,
	"message": "OK",
	"data": { /* payload original */ }
}
```
- Erro (4xx/5xx):
```json
{
	"success": false,
	"error": {
		"code": "validation_error | not_authenticated | permission_denied | not_found | error",
		"message": "Descrição do problema",
		"details": { /* payload original do DRF */ }
	}
}
```
- Implementação:
	- Sucesso: renderer global `apps.core.renderers.StandardJSONRenderer`
	- Erros: handler global `saas_backend.exceptions.custom_exception_handler`


```powershell
# Últimos 50 logs (mais recentes primeiro)
Invoke-RestMethod -Method GET "http://localhost:8000/api/v1/auditing/logs?page=1&page_size=50&ordering=-created_at" -Headers @{ Authorization = "Bearer <access>" }

# Filtrar por usuário específico (user_id=42)
Invoke-RestMethod -Method GET "http://localhost:8000/api/v1/auditing/logs?user_id=42&ordering=-created_at" -Headers @{ Authorization = "Bearer <access>" }

# Filtrar por método HTTP e trecho do path
Invoke-RestMethod -Method GET "http://localhost:8000/api/v1/auditing/logs?method=POST&path_contains=/auth/" -Headers @{ Authorization = "Bearer <access>" }

# Filtrar por intervalo de datas (ISO 8601) + ordenação ascendente
Invoke-RestMethod -Method GET "http://localhost:8000/api/v1/auditing/logs?created_after=2025-01-01T00:00:00Z&created_before=2025-12-31T23:59:59Z&ordering=created_at" -Headers @{ Authorization = "Bearer <access>" }

# Combinação: user_id + método + intervalo + paginação
Invoke-RestMethod -Method GET "http://localhost:8000/api/v1/auditing/logs?user_id=42&method=GET&created_after=2025-06-01T00:00:00Z&page=2&page_size=25&ordering=-created_at" -Headers @{ Authorization = "Bearer <access>" }

Exportar auditoria (Admin): selecione entradas em `/admin/apps_auditing/auditlog/` e use a ação "Export selected as CSV".

Retenção e limpeza de logs
- Comando para limpar logs antigos (usa valores do `settings` se `--days` não for fornecido):
```powershell
cd backend
python manage.py purge_audit_logs
```
- Configuração:
	- `AUDIT_RETENTION_DEFAULT_DAYS=90` (padrão global)
	- `AUDIT_RETENTION_TENANT_DAYS={ 'acme': 30, 'beta': 120 }` (mapa por `schema_name`)
- Opcional: `--days <n>` força o valor global (ignora o padrão do settings), mantendo os overrides por tenant.
- Admin via API:
	- CRUD em `/api/v1/auditing/retention-policies` (lista/cria) e `/api/v1/auditing/retention-policies/{id}` (atualiza/exclui)
	- Permissão requerida: `manage_auditing`

DLQ (Dead-Letter Queue)
- Purga via Admin: ação "Purge DLQ older than N days" em AuditLog (ignora seleção), usa `AUDIT_DLQ_PURGE_DAYS`.
- Purga via CLI:
```powershell
cd backend
python manage.py purge_dlq --days 10
# ou sem --days, usa o padrão do settings
python manage.py purge_dlq
```
- Configuração: `AUDIT_DLQ_PURGE_DAYS=30` (padrão). Pode ser alterado via `.env`.
 - Agendamento: Celery Beat executa a tarefa diária `purge-dlq-daily` (chama `apps.auditing.tasks.purge_dlq_older_than_default`).

LOGGING/ELK
- Logs de aplicação são enviados ao console (stdout). Ajuste nível com `DJANGO_LOG_LEVEL` (ex.: `INFO`, `DEBUG`).
- Para ELK, coletores (Filebeat/Logstash) podem ingerir stdout do container.
- Habilite logs estruturados JSON com `USE_JSON_LOGS=true`.
- Exportação opcional para Elasticsearch via Celery (bulk):
	- Variáveis: `AUDIT_EXPORT_ENABLED=true`, `ELASTICSEARCH_URL=http://elasticsearch:9200`, `AUDIT_EXPORT_INDEX_PREFIX=audit`.
	- Tarefa: `apps.auditing.tasks.export_audit_logs_to_elasticsearch` (agendada a cada 5min).
	- Autenticação (opcional):
		- Basic: `ELASTICSEARCH_USERNAME`, `ELASTICSEARCH_PASSWORD`.
		- API Key: `ELASTICSEARCH_API_KEY` (valor base64 `id:key`).
	- Confiabilidade: tentativas com backoff exponencial (padrão 3 tentativas).

Alertas via Webhook (ações críticas)
- Habilitar: `ALERT_WEBHOOK_ENABLED=true` e `ALERT_WEBHOOK_URL=https://hooks.slack.com/services/...` (ou outro endpoint HTTP).
- Ações críticas padrão: `AUDIT_CRITICAL_ACTIONS=rbac_change,plan_change,suspend_tenant,reactivate_tenant`.
- Disparo: ao criar `AuditLog` com `action` crítico, um task Celery envia um payload simples (`text`) com `tenant`, `action`, `user`, `path`, `status`.
- Supressão/antispam: `ALERT_WEBHOOK_QUIET_MINUTES=10` evita alertas repetidos para o mesmo `tenant_schema + action` dentro da janela configurada.
 - Bypass: `ALERT_WEBHOOK_QUIET_BYPASS_ACTIONS=security_incident,...` permite ignorar a supressão para ações específicas.

Eventos e Filas (Celery)
- Configuração já inclusa: Celery + Redis. Rotas: fila `events` para processamento, `dlq` para Dead-Letter.
- Eager mode (testes locais): `CELERY_TASK_ALWAYS_EAGER=true` executa tarefas inline.
- Emissões automáticas:
	- Tenant: `TenantCreated` após criação (ver tenants API).
	- Plano: `PlanUpgraded` após alteração de plano.
	- Usuário: `UserCreated` em `post_save`.
- DLQ: entradas são registradas em `AuditLog` com `action=event_DLQ`.
- Admin: no `AuditLog` existe o filtro "DLQ" para exibir apenas entradas de DLQ.
- Reprocessar DLQ (Admin): selecione entradas de DLQ e use a ação "Requeue selected DLQ events"; o sistema reemite o evento com payload mínimo (`tenant_schema`, `tenant_id`).
	- Observação: se a entrada de DLQ possuir `payload` salvo (JSON), esse payload é reutilizado na reemissão (com `requeued_from_dlq=true`).
- Workers (Docker):
```powershell
docker compose up -d redis postgres
docker compose up django
docker compose up celery
```

Testes de eventos
- Em modo eager (sem worker):
```powershell
setx CELERY_TASK_ALWAYS_EAGER "true"
Push-Location .\backend
python -m pytest -q tests\test_events.py
Pop-Location
```
- Endpoints que disparam eventos:
	- Tenant criado (POST): `/api/v1/tenants` → emite `TenantCreated`
	- Alteração de plano (POST): `/api/v1/tenants/{tenant_id}/plan` → emite `PlanUpgraded`
- Emissão manual (console Django):
```powershell
Push-Location .\backend
python manage.py shell
>>> from apps.events.events import emit_event, TENANT_CREATED
>>> emit_event(TENANT_CREATED, {"tenant_id": 1, "tenant_schema": "acme"})
Pop-Location
```
```
- Docs: `/api/schema` e `/api/docs`

OpenAPI / Swagger
- Gerar arquivo de schema OpenAPI (YAML) com drf-spectacular:
```powershell
Push-Location .\backend
python manage.py spectacular --file openapi.yaml
Pop-Location
```
- O arquivo será criado em `backend/openapi.yaml`. Você pode abrir em um editor ou importar em Postman/Insomnia.
- A UI do Swagger está disponível em `/api/docs`. O endpoint bruto do schema está em `/api/schema`.
- Dica: valide o YAML com `spectacular --validate` (requer drf-spectacular >= 0.27):
```powershell
Push-Location .\backend
python manage.py spectacular --file openapi.yaml --validate
Pop-Location
```

- Alternativa com `drf-yasg`:
	- Swagger UI: acesse `/api/swagger/` (drf-yasg)
	- Redoc: acesse `/api/redoc/`
	- Schema bruto: `/api/swagger.json` ou `/api/swagger.yaml`
	- Instalação: pacote `drf-yasg` já incluso em `requirements.txt`
	- Observação: o projeto disponibiliza tanto drf-spectacular quanto drf-yasg para flexibilidade.
	- Exemplos em endpoints RBAC: os endpoints de atribuição de role/permissão e operação em lote incluem parâmetros e payloads de exemplo.
 - Serviços:
	 - GET `/api/v1/whatsapp/status` (JWT)
	 - POST `/api/v1/whatsapp/messages/send` (JWT, throttle per plan)
	 - GET `/api/v1/email/status` (JWT)
	 - POST `/api/v1/email/messages/send` (JWT, throttle per plan)
	 - GET `/api/v1/sms/status` (JWT)
	 - POST `/api/v1/sms/messages/send` (JWT, throttle per plan)
	 - GET `/api/v1/chatbots/status` (JWT)
	 - POST `/api/v1/chatbots/messages/send` (JWT, throttle per plan)
	 - GET `/api/v1/workflows/status` (JWT)
	 - POST `/api/v1/workflows/execute` (JWT, throttle per plan)
	 - GET `/api/v1/ai/status` (JWT)
	 - POST `/api/v1/ai/infer` (JWT, throttle per plan)

Publicação de OpenAPI (CI / Pages / Releases)
- GitHub Pages: o workflow `publish-openapi.yml` gera `backend/openapi.yaml` e publica em `docs/api/openapi.yaml` junto com `docs/api/index.html` (ReDoc). Habilite Pages no repositório (Source: GitHub Actions) e acesse a página de documentação pelo URL de Pages do repositório, no caminho `/api/`.
- Releases: o workflow `release-openapi.yml` anexa `backend/openapi.yaml` às releases (gatilho: `release: created`).
- Validação/Lint: o workflow `openapi.yml` valida o schema com `openapi-spec-validator` e faz lint com `@redocly/cli`.
- Local (Docker): gere o schema com Makefile
```powershell
cd backend
make openapi
```
O arquivo será gravado em `backend/openapi.yaml`. Para visualizar via ReDoc local, abra `docs/api/index.html` e aponte para o arquivo gerado.

Limites por Plano (diários)
- Configuração: `TENANT_PLAN_DAILY_LIMITS` em `saas_backend/settings.py`
- Validação: `apps.core.middleware.PlanLimitMiddleware` bloqueia com `429` quando o limite diário é atingido, por tenant e categoria (ex.: `send_whatsapp`).
- Identificação de categoria: usa `view.throttle_scope` dos endpoints.
- Contadores: armazenados em cache até o fim do dia.

Alertas de "perto do limite" (Near-limit)
- Agendados via Celery Beat (`CELERY_BEAT_SCHEDULE`) a cada ~10min.
- Tarefa: `apps.core.tasks.check_daily_limit_warns` percorre tenants ativos e cria alertas quando `percent_used_today` ≥ `TENANT_PLAN_DAILY_WARN_THRESHOLD`.
- Observabilidade: cria entrada de auditoria (`source='alert'`) com path `/alerts/daily_limit_near/<categoria>`.
- Opcional: envio de email se `TENANT_ALERTS_EMAIL_TO` estiver definido no `.env`.

Reset de contadores diários
- Endpoint: POST `/api/v1/core/throttle/daily/reset` (perm: `manage_tenants`)
- Body opcional:
```json
{ "categories": ["send_whatsapp", "send_email"] }
```
- Se ausente, reseta todas as categorias definidas pelo plano do tenant.
- Exemplo PowerShell:
```powershell
Invoke-RestMethod -Method POST "http://localhost:8000/api/v1/core/throttle/daily/reset" \
	-Headers @{ Authorization = "Bearer <access>" } \
	-ContentType "application/json" \
	-Body '{"categories":["send_whatsapp"]}'
```

Resumo diário (PowerShell):
```powershell
Invoke-RestMethod -Method GET "http://localhost:8000/api/v1/core/throttle/daily/summary" \
	-Headers @{ Authorization = "Bearer <access>" }
```
Campos retornados por categoria:
- **category**: identificador (ex.: `send_whatsapp`)
- **limit_per_day**: limite diário configurado
- **used_today**: total consumido hoje
- **remaining_today**: quanto resta hoje
- **percent_used_today**: porcentagem usada (0–100)
- **near_limit**: alerta (true/false) quando `percent_used_today` ≥ `threshold_percent`
- **threshold_percent**: valor de alerta configurável (padrão 80; env `TENANT_PLAN_DAILY_WARN_THRESHOLD`)

Relacionamento Tenant↔Plano
- Campo `tenant.plan` (código: `free`, `pro`, `enterprise`) define qual conjunto de limites aplicar.
- CLI para atualizar plano:
```powershell
cd backend
python manage.py set_tenant_plan --schema acme --plan pro
```

Admin e Seed de Planos
- Admin: gerencie `Plan`, `Tenant` e `Domain` pelo Django Admin.
- Ação Admin: selecione tenants e use "Reset daily plan counters" para limpar os contadores do dia.
- Seed: popular planos padrão com limites diários:
```powershell
cd backend
python manage.py migrate tenants
python manage.py seed_plans
```

Arquivos de exemplo (REST Client):
- backend/docs/services.http — exemplos de chamadas com permissões exigidas (send_whatsapp, email_send, sms_send, chatbots_send, workflows_execute, ai_infer).
- backend/docs/core_reset.http — status de throttling e reset diário por categoria.
- backend/docs/auditing.http — exemplos de filtros de auditoria (inclusive `source`).

Estrutura:
- manage.py
- saas_backend/settings.py | urls.py | asgi.py | wsgi.py
- apps/core (health)
- apps/users (JWT e perfil)
- apps/tenants (Tenant/Domain)
- .env.example (SECRET_KEY, DATABASE_URL etc.)

Multi-tenancy:
- `TENANT_MODEL = tenants.Tenant`, `DOMAIN_MODEL = tenants.Domain`
- `TenantMainMiddleware` e `TenantSyncRouter` configurados
- Requer PostgreSQL (DATABASE_URL no .env)

Gestão de Tenants (admin):
- Criar tenant (cria schema e domínio principal): `POST /api/v1/tenants` body `{ name, schema_name, domain, plan? }`
- Suspender/reativar: `POST /api/v1/tenants/{tenant_id}/actions` body `{ "action": "suspend" | "reactivate" }`
- Alterar plano do tenant: `POST /api/v1/tenants/{tenant_id}/plan` body `{ "plan": "pro" }`
	- Atualiza `tenant.plan` e `tenant.plan_ref` (Plan code → FK), cria `AuditLog(action='plan_change')` e dispara webhook (se habilitado).
- Conveniência no request: `tenant_id` e `tenant_schema` disponíveis via middleware `TenantContextMiddleware`

Migrations específicas:
```powershell
docker compose exec django python manage.py makemigrations tenants
docker compose exec django python manage.py migrate
```

Tenants Quickstart:
```bash
# Criar tenant
curl -X POST "http://localhost:8000/api/v1/tenants" \
	-H "Content-Type: application/json" \
	-H "Authorization: Bearer <JWT_ADMIN_TOKEN>" \
	-d '{
		"name": "Acme Corp",
		"schema_name": "acme",
		"domain": "acme.local",
		"plan": "pro"
	}'

# Suspender tenant
curl -X POST "http://localhost:8000/api/v1/tenants/<TENANT_ID>/actions" \
	-H "Content-Type: application/json" \
	-H "Authorization: Bearer <JWT_ADMIN_TOKEN>" \
	-d '{ "action": "suspend" }'

# Reativar tenant
curl -X POST "http://localhost:8000/api/v1/tenants/<TENANT_ID>/actions" \
	-H "Content-Type: application/json" \
	-H "Authorization: Bearer <JWT_ADMIN_TOKEN>" \
	-d '{ "action": "reactivate" }'

# Alterar plano
curl -X POST "http://localhost:8000/api/v1/tenants/<TENANT_ID>/plan" \
	-H "Content-Type: application/json" \
	-H "Authorization: Bearer <JWT_ADMIN_TOKEN>" \
	-d '{ "plan": "pro" }'
```

Notas:
- Endpoints requerem credenciais administrativas (JWT) e obedecem ao middleware de tenant ativo.
- A mudança de plano cria `AuditLog(action='plan_change')` e pode disparar webhooks/exports se configurados.
- Veja exemplos prontos em `backend/docs/tenants.http`.

Gerar migrations (atalho PowerShell):
```powershell
# Tenta Python local, senão usa Docker Compose
cd backend
./scripts/gen_tenant_migrations.ps1
```

Como rodar:

## Opção 1: Docker Compose (recomendado)

Requer Docker Desktop instalado.

```powershell
cd backend
cp .env.example .env

# Inicia Postgres, Redis e Django
docker compose up -d --build

# Acompanha logs
docker compose logs -f django

# Cria superuser (opcional)
docker compose exec django python manage.py createsuperuser
docker compose exec django python manage.py makemigrations auditing
docker compose exec django python manage.py migrate

# Celery Beat/Worker (alertas):
docker compose exec django celery -A saas_backend.celery.app beat -l info
docker compose exec django celery -A saas_backend.celery.app worker -l info

# Admin RBAC
# Após migrar, acesse /admin e gerencie Roles/Permissions.
# Comando para popular roles/permissões padrão:
docker compose exec django python manage.py seed_roles
```

Ou use o Makefile:
```powershell
make up          # inicia tudo
make logs        # acompanha logs
make createsuperuser
make down        # para tudo
```

## Opção 2: Local (Python + Postgres + Redis)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate
pip install -r requirements.txt
cp .env.example .env
# Configure DATABASE_URL e REDIS_URL no .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8000
```

Teste:
- Registro: `POST /api/v1/auth/register` com `{"username":"test","password":"Test123!"}`
- Login: `POST /api/v1/auth/token` com `{"username":"test","password":"Test123!"}` → retorna `access` e `refresh`
- Protegido: `GET /api/v1/users/me` com header `Authorization: Bearer <access>`
- Throttle status: `GET /api/v1/core/throttle/status` (admin JWT)

Smoke test (PowerShell):

```powershell
cd backend
.\scripts\smoke.ps1 -BaseUrl "http://localhost:8000"
```

Executar testes rapidamente (PowerShell):

```powershell
cd backend
./scripts/run_tests.ps1
```

Cache opcional por view
- Para reduzir carga em endpoints administrativos de status/resumo, é possível habilitar cache por alguns segundos via variáveis no `.env`:
	- `CACHE_TTL_TENANT_STATUS` (segundos) — aplica em `GET /api/v1/core/throttle/status`
	- `CACHE_TTL_TENANT_DAILY_SUMMARY` (segundos) — aplica em `GET /api/v1/core/daily/summary`
- Por padrão, ambos são `0` (desabilitado). Se habilitar, prefira TTLs curtos (ex.: 5–30s).

Webhooks
- Endpoint genérico: `POST /api/v1/core/webhooks/{provider}` (sem autenticação; verificação via assinatura HMAC)
- Assinatura: header `X-Signature` = HMAC-SHA256(hex) do corpo bruto usando o segredo do provider.
- Proteção de replay: header opcional `X-Timestamp` (unix seconds), validado contra `WEBHOOK_MAX_SKEW_SECONDS`.
- Configure segredos no `.env`:
	- `STRIPE_WEBHOOK_SECRET`, `PAYPAL_WEBHOOK_SECRET`, `CUSTOM_WEBHOOK_SECRET`
	- `WEBHOOK_MAX_SKEW_SECONDS=300` (padrão)
- Observação: provedores como Stripe e PayPal têm formatos próprios de assinatura; este endpoint oferece verificação HMAC genérica. Integrações específicas podem ser adicionadas como handlers dedicados.

Reset diário via CLI (management command):

```powershell
cd backend
# Reset para um tenant específico (por schema), categorias escolhidas
python manage.py reset_daily_counters --schema acme --categories send_whatsapp send_email

# Reset de todas as categorias definidas pelo plano do tenant
python manage.py reset_daily_counters --schema acme

# Reset para todos os tenants
python manage.py reset_daily_counters --all
```

Decisões técnicas (resumo):
- API-first: DRF com autenticação JWT por padrão e permissões seguras
- Autenticação via Cookie/Authorization: classe `CookieJWTAuthentication` permite validar JWT presente em cookie HttpOnly
- Auditoria de requests autenticadas: `apps.auditing` (modelo `AuditLog` + middleware)
- Multi-tenant: `django-tenants` pelo suporte ativo e esquema por tenant
- Documentação pronta: drf-spectacular para schema e Swagger UI
- Config centralizada por ambiente: `.env` e `django-environ`

Controle de Acesso (RBAC)
- Models: `apps.rbac` com `Permission`, `Role`, `UserRole`, `UserPermission`
- Middleware: `PermissionMiddleware` (nega acesso 403 se faltar `required_permission`)
- DRF: `HasPermission` verifica `view.required_permission`
- Roles iniciais: Admin, Manager, Operator, Viewer (com permissões básicas)
- Seed:
```powershell
cd backend
docker compose exec django python manage.py migrate rbac
docker compose exec django python manage.py seed_roles
```
- Exemplo: `/api/v1/auditing/logs` requer `view_audit_logs`; endpoints de tenants requerem `manage_tenants`
 - Endpoints:
	 - GET `/api/v1/rbac/users/{user_id}/roles` (perm: `view_users`) — lista roles do usuário no tenant atual
	 - POST `/api/v1/rbac/users/{user_id}/roles/assign` (perm: `manage_users`) — atribui role no tenant atual `{ "role": "Viewer" }`
	 - GET `/api/v1/rbac/users/{user_id}/permissions` (perm: `view_users`) — lista permissões do usuário no tenant atual
	 - POST `/api/v1/rbac/users/{user_id}/permissions/assign` (perm: `manage_users`) — atribui permissão `{ "permission": "send_whatsapp" }`
	 - POST `/api/v1/rbac/users/{user_id}/permissions/revoke` (perm: `manage_users`) — revoga permissão `{ "permission": "send_whatsapp" }`
	 - POST `/api/v1/rbac/bulk/apply` (perm: `manage_users`) — aplica operações em lote no tenant atual.
	   - Request (JSON):
	   ```json
	   {
	     "assign": {
	       "roles": [ { "username": "u1", "role": "Viewer" } ],
	       "permissions": [ { "username": "u1", "permission": "send_sms" } ]
	     },
	     "revoke": {
	       "roles": [ { "username": "u2", "role": "Operator" } ],
	       "permissions": [ { "username": "u3", "permission": "email_send" } ]
	     }
	   }
	   ```
	   - Response: `200` quando todas as operações são aplicadas; `207` quando há erros parciais (campo `errors`).

 Arquivos de exemplo (REST Client):
 - `backend/docs/rbac_endpoints.http` — exemplos de listar/atribuir/revogar roles e permissões.
 - `backend/docs/rbac_bulk.http` — exemplo de requisição em lote.
	- Serviços (permissões exigidas):
		 - CLI (atalhos RBAC):
		 ```powershell
		 # Atribuir role a usuário em um tenant
		 docker compose exec django python manage.py assign_role --username admin --role Viewer --tenant acme

		 # Conceder permissão a usuário em um tenant
		 docker compose exec django python manage.py grant_permission --username operator --permission send_whatsapp --tenant acme

			# Revogar role/permissão
			docker compose exec django python manage.py revoke_role --username admin --role Viewer --tenant acme
			docker compose exec django python manage.py revoke_permission --username operator --permission send_whatsapp --tenant acme

			# Aplicar em lote (JSON)
			# Arquivo exemplo (rbac.json):
			# {
			#   "tenant": "acme",
			#   "assign": {
			#     "roles": [ { "username": "u1", "role": "Viewer" } ],
			#     "permissions": [ { "username": "u1", "permission": "send_whatsapp" } ]
			#   },
			#   "revoke": {
			#     "roles": [ { "username": "u2", "role": "Operator" } ],
			#     "permissions": [ { "username": "u3", "permission": "email_send" } ]
			#   }
			# }
			docker compose exec django python manage.py bulk_apply_rbac --file /code/rbac.json
		 ```
		- POST `/api/v1/whatsapp/messages/send` (perm: `send_whatsapp`)
		- POST `/api/v1/email/messages/send` (perm: `email_send`)
		- POST `/api/v1/sms/messages/send` (perm: `sms_send`)
		- POST `/api/v1/chatbots/messages/send` (perm: `chatbots_send`)
		- POST `/api/v1/workflows/execute` (perm: `workflows_execute`)
		- POST `/api/v1/ai/infer` (perm: `ai_infer`)
 - Escopo por tenant: atribuições (`UserRole`, `UserPermission`) são vinculadas ao tenant atual e verificadas pelo middleware/DRF

Exemplos (cURL - Auth via Cookie)

```bash
# Registro (username e senha)
curl -s -X POST http://localhost:8000/api/v1/auth/register \
	-H "Content-Type: application/json" \
	-d '{"username":"testuser","password":"Test123!"}' | jq

# Login (salva cookie access_token em cookiejar)
curl -s -c cookiejar.txt -X POST http://localhost:8000/api/v1/auth/token \
	-H "Content-Type: application/json" \
	-d '{"username":"testuser","password":"Test123!"}' | jq

# Rota protegida com Cookie (sem header Authorization)
curl -s -b cookiejar.txt http://localhost:8000/api/v1/users/me | jq

# Refresh (atualiza cookie access_token)
curl -s -c cookiejar.txt -b cookiejar.txt -X POST http://localhost:8000/api/v1/auth/refresh \
	-H "Content-Type: application/json" \
	-d '{"refresh":"<coloque_o_refresh_token_aqui_se_necessário>"}' | jq

# Logout (apaga cookie no response)
curl -s -b cookiejar.txt -X POST http://localhost:8000/api/v1/auth/logout \
	-H "Content-Type: application/json" \
	-d '{"refresh":"<coloque_o_refresh_token_aqui_se_necessário>"}' | jq
```

Exemplos (cURL - Gestão de Tenants)

```bash
# Criar tenant (requer JWT admin; ajuste domínio conforme ambiente)
curl -s -H "Authorization: Bearer $ACCESS" -H "Content-Type: application/json" \
	-X POST http://localhost:8000/api/v1/tenants \
	-d '{"name":"Tenant ACME","schema_name":"acme","domain":"acme.localhost","plan":"pro"}' | jq

# Suspender tenant via API (tenant_id=1)
curl -s -H "Authorization: Bearer $ACCESS" -H "Content-Type: application/json" \
	-X POST http://localhost:8000/api/v1/tenants/1/actions \
	-d '{"action":"suspend"}' | jq

# Reativar tenant via API
curl -s -H "Authorization: Bearer $ACCESS" -H "Content-Type: application/json" \
	-X POST http://localhost:8000/api/v1/tenants/1/actions \
	-d '{"action":"reactivate"}' | jq
```
