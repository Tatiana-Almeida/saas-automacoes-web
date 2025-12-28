# SAAS de Automações Web — Desenvolvimento Local

Este documento descreve passo a passo como levantar o projeto localmente, executar testes e trabalhar com tenants em um ambiente multi-tenant por host. As instruções são explícitas e copiáveis para Windows, macOS e Linux.

**Seções:**
- Seção 1 — Visão Geral do Projeto
- Seção 2 — Pré-requisitos
- Seção 3 — Setup Inicial (Docker)
- Seção 4 — Execução de Testes
- Seção 5 — Multi-Tenant (Como Funciona)
- Seção 6 — Frontend
- Seção 7 — Problemas Comuns (Troubleshooting)

**Seção 1 — Visão Geral do Projeto**

- Breve descrição: repositório de um SaaS multi-tenant que cria um schema PostgreSQL por tenant usando `django-tenants`. O backend é Django + DRF; o frontend é React + Vite.
- Stack tecnológica:
  - Backend: Python 3.11, Django, django-tenants, pytest/pytest-django
  - Frontend: React, Vite, TypeScript
  - Infra local: Docker + Docker Compose
  - Banco de dados: PostgreSQL
  - Cache / Broker: Redis
- Multi-tenant por host (resumo):
  - Tenant é resolvido pelo host HTTP (ex.: `acme.localhost`). Em desenvolvimento o header `X-TENANT-HOST` e `sessionStorage['tenant_host']` também são suportados.
  - O schema `public` contém tabelas compartilhadas; execute as migrações `shared/public` antes de usar tenants.

**Seção 2 — Pré-requisitos**

Instale as ferramentas abaixo antes de iniciar (versões recomendadas entre parênteses):

- Docker e Docker Compose (Docker Desktop com Compose v2+)
- Node.js (recomendado: 18 LTS ou 20 LTS)
- Git
- Python 3.11 — somente se rodar backend fora do Docker (opcional)

Ferramentas de desenvolvedor recomendadas:

- `pre-commit` — facilita aplicar `ruff`, `black` e `isort` localmente antes de commitar. Após instalar (ex.: `pip install pre-commit`), execute `pre-commit install` na raiz do repositório.

Com `pre-commit` instalado, os hooks definidos em `.pre-commit-config.yaml` (ruff/black/isort/prettier) rodarão automaticamente em cada commit.

Para rodar todos os hooks manualmente (útil antes de um PR):

```bash
pre-commit run --all-files
```

Observação: o guia assume uso de Docker Compose para Postgres e Redis em dev.

**Seção 3 — Setup Inicial (Docker)**

1) Clone o repositório

```bash
git clone <REPO_URL>
cd <REPO_DIR>
```

2) Copie `.env.example` para `.env` e ajuste valores

Windows PowerShell:
```powershell
Copy-Item .env.example .env -Force
notepad .env
```

macOS / Linux:
```bash
cp .env.example .env
${EDITOR:-nano} .env
```

3) Suba serviços (Postgres, Redis, backend, frontend opcional)

```bash
docker compose up -d
```

4) Execute migrações públicas/shared (obrigatório)

```bash
docker compose run --rm backend sh -lc "python manage.py migrate --noinput && python manage.py migrate_schemas --shared --noinput"
```

Nota: `migrate_schemas --shared` cria as tabelas no schema `public` necessárias para resolução de tenants.

5) (Opcional) Criar um tenant de exemplo

```bash
docker compose run --rm backend sh -lc "python manage.py shell -c \"from apps.tenants.models import Tenant, Domain; t=Tenant(schema_name='empresa', name='Empresa'); t.save(); Domain.objects.create(domain='empresa.localhost', tenant=t)\""
```

6) Iniciar backend para desenvolvimento

```bash
docker compose up -d backend
# ou rodar interativamente
docker compose run --rm backend sh -lc "python manage.py runserver 0.0.0.0:8000"
```

Tempo estimado: com imagens em cache, o setup completo costuma levar menos de 15 minutos.

**Seção 4 — Execução de Testes**

Rode os testes de maneira determinística seguindo estes passos.

- Executando `pytest` dentro do container (recomendado):

```bash
docker compose run --rm backend sh -lc "pip install -r requirements-dev.txt >/dev/null 2>&1 || true; export DJANGO_SETTINGS_MODULE=saas_backend.settings; python manage.py migrate --noinput; python manage.py migrate_schemas --shared --noinput; pytest -q"
```

- Variáveis importantes para testes:
  - `DJANGO_SETTINGS_MODULE`: tipicamente `saas_backend.settings` para Postgres; `saas_backend.settings_test` existe para runs rápidos com SQLite.
  - `REDIS_URL`: use um DB Redis separado em CI (ex.: `redis://redis:6379/9`) para isolamento.

- Garantir migrações antes dos testes:
  - Sempre execute `python manage.py migrate` e `python manage.py migrate_schemas --shared --noinput` em um DB limpo.
  - Em CI, aplique migrações no job antes de rodar `pytest`.

- Redis/cache durante testes:
  - O projeto contém fixtures que limpam Redis entre testes quando `REDIS_URL` está configurado.
  - Se usar Redis local, aponte `REDIS_URL` para um DB index dedicado para evitar interferência.

**Seção 5 — Multi-Tenant (Como Funciona)**

- Resolução de tenants:
  - Produção: por `HTTP_HOST` (subdomínio) — cada host mapeia para um `Domain` no schema `public`.
  - Desenvolvimento/testes: `X-TENANT-HOST` header e `sessionStorage['tenant_host']` são suportados.

- Criar tenant manualmente (exemplo):

```bash
docker compose run --rm backend sh -lc "python manage.py shell -c \"from apps.tenants.models import Tenant, Domain; t=Tenant(schema_name='acme', name='Acme'); t.save(); Domain.objects.create(domain='acme.localhost', tenant=t)\""
```

- Simular tenant no browser (dev):

Abra DevTools → Console e cole:

```javascript
sessionStorage.setItem('tenant_host', 'acme.localhost')
// reload page
```

Isto faz com que o frontend envie `X-TENANT-HOST: acme.localhost` nas requisições.

**Seção 6 — Frontend**

- Instalar e rodar localmente:

```bash
cd frontend
npm ci
npm run dev
```

- Variáveis importantes:
  - `VITE_API_URL` — URL base da API (ex.: `http://localhost:8000/api`).
  - `VITE_TENANT_HOST` (opcional) — tenant host padrão em dev.
  - Crie `frontend/.env.local` para variáveis locais (não comitar).

- Rodar build via Docker:

```bash
docker compose run --rm frontend sh -lc "npm ci && npm run build"
```

**Seção 7 — Problemas Comuns (Troubleshooting)**

- Porta já em uso (Docker): pare o processo que usa a porta ou altere as portas no `docker-compose.yml`.
- Erros de migration (`relation "tenants_tenant" does not exist`): execute `python manage.py migrate && python manage.py migrate_schemas --shared --noinput` antes de criar tenants/rodar testes.
- Tenant não resolvido: confirme `X-TENANT-HOST` header, `sessionStorage['tenant_host']` e existência de `Domain` no schema `public`.
- Redis causando 429: em testes use `saas_backend.settings_test` (LocMemCache) ou aponte `REDIS_URL` para um DB dedicado.
- Postgres não conectando: verifique `DATABASE_URL` em `.env` e `docker compose ps` para saúde do serviço.

Arquivos úteis no repositório:
- [backend/tests/helpers/tenant.py](backend/tests/helpers/tenant.py)
- [backend/tests/conftest.py](backend/tests/conftest.py)
- [backend/apps/core/middleware.py](backend/apps/core/middleware.py)
- [.github/workflows/ci.yml](.github/workflows/ci.yml)

Se precisar de ajustes para um ambiente específico, abra uma issue com o output do comando e eu ajusto o guia.
# SAAS de Automações Web — Desenvolvimento Local

Visão geral, setup e procedimentos para rodar o projeto localmente (backend Django multi-tenant, frontend React + Vite, Postgres e Redis via Docker).

---

**Seções:**
- Visão geral
- Pré-requisitos
- Setup inicial (Docker)
- Execução de testes
- Multi-tenant (como funciona)
- Frontend
- Troubleshooting

---

**Seção 1 — Visão Geral do Projeto**

- Breve descrição: este repositório implementa um SaaS multi-tenant por host. Cada tenant tem um schema Postgres separado (django-tenants). O backend fornece APIs (Django + DRF); o frontend é React + Vite.
- Stack:
  - Backend: Python 3.11, Django, django-tenants, pytest
  - Frontend: React, Vite, TypeScript
  - Infra local: Docker + docker-compose
  - Banco: PostgreSQL
  - Cache / Broker: Redis

- Multi-tenant por host: tenant é resolvido pelo host (ex.: `acme.localhost`) ou via header/sessionStorage em ambiente de desenvolvimento. Shared/public migrations são aplicadas no schema `public`.

---

**Seção 2 — Pré-requisitos**

- Instale:
  - Docker (Desktop) e Docker Compose (v2+). Testado em Windows, macOS, Linux.
  - Node.js (recomendado: 18+ / 20 LTS)
  - Git
  - (Opcional) Python 3.11 se rodar backend fora do Docker

---

**Seção 3 — Setup Inicial (Docker)**

Siga estes passos para preparar o ambiente do zero.

1) Clone o repositório:

```bash
git clone git@github.com:your-org/your-repo.git
cd your-repo
```

2) Copie o arquivo de ambiente e edite valores mínimos:

```bash
cp .env.example .env
# abra .env e ajuste se necessário
```

3) Suba os serviços com Docker Compose:

```bash
docker compose up -d
```

4) Aplique migrações iniciais (public/shared):

```bash
docker compose run --rm backend sh -lc "python manage.py migrate --noinput && python manage.py migrate_schemas --shared --noinput"
```

Observação: o comando `migrate_schemas --shared` cria as tabelas que residem no schema `public` e são necessárias para resolução de tenants.

5) Criar tenant de exemplo (exemplo fornecido no repositório):

```bash
# script que cria um tenant/local test tenant (opcional)
docker compose run --rm backend sh -lc "python scripts/seed_localhost_tenant.py"
```

6) Iniciar serviços (se precisar do server Django localmente):

```bash
docker compose up -d backend
# ou executar server interativamente
docker compose run --rm backend sh -lc "python manage.py runserver 0.0.0.0:8000"
```

Tempo estimado: com Docker Desktop e cache de imagens, o setup completo (downloading images + migrations) costuma ficar dentro de 15 minutos em conexões razoáveis.

---

**Seção 4 — Execução de Testes**

- Dentro do container (recomendado):

```bash
docker compose run --rm backend sh -lc "pip install -r requirements-dev.txt >/dev/null 2>&1 || true; export DJANGO_SETTINGS_MODULE=saas_backend.settings; python manage.py migrate --noinput; python manage.py migrate_schemas --shared --noinput; pytest -q"
```

- Explicação:
  - `migrate` e `migrate_schemas --shared` devem ser aplicados antes de `pytest` para garantir que o schema `public` e tabelas compartilhadas existam.
  - O repo contém fixtures que aplicam migrações de sessão automaticamente, mas em CI/containers execute os comandos acima para garantir consistência.

- Variáveis importantes durante testes:
  - `DJANGO_SETTINGS_MODULE` — em CI ou runs locais pode apontar para `saas_backend.settings` (Postgres) ou `saas_backend.settings_test` (modo SQLite para testes rápidos).
  - `REDIS_URL` — para garantir isolamento do Redis em CI, use um DB index separado (ex.: `redis://redis:6379/9`).

- Redis/cache nos testes:
  - O projeto inclui uma fixture que limpa a cache entre testes. Localmente, se usar um Redis compartilhado, configure `REDIS_URL` para apontar a um DB de teste para evitar interferência com outros ambientes.

---

**Seção 5 — Multi-Tenant (Como Funciona)**

- Resolução de tenants:
  - Produção: tenant é resolvido pelo host (ex.: `acme.example.com`).
  - Desenvolvimento/testes: o projeto aceita `X-TENANT-HOST` header e também a chave `tenantHost` em `sessionStorage` (frontend) para forçar um tenant sem mudar DNS.

- Criar um tenant manualmente (exemplo):

```bash
docker compose run --rm backend sh -lc "python manage.py shell -c \"from apps.tenants.models import Tenant, Domain; t=Tenant(schema_name='acme', name='Acme'); t.save(); Domain.objects.create(domain='acme.localhost', tenant=t)\""
```

- Simular tenant no browser (dev): abra DevTools → Console e execute:

```js
sessionStorage.setItem('tenantHost', 'acme.localhost')
```

Isso faz com que o frontend envie o `X-TENANT-HOST` header nas requests (projeto inclui utilitário/axios interceptor para isso).

---

**Seção 6 — Frontend**

- Instalar e rodar localmente (fora do Docker):

```bash
cd frontend
npm ci
npm run dev
```

- Variáveis:
  - `VITE_API_URL` — URL base para a API (ex.: `http://localhost:8000/api`)
  - Crie `frontend/.env.local` para valores locais (não comitar secrets)

- Rodar via Docker (opcional):

```bash
docker compose run --rm frontend sh -lc "npm ci && npm run build"
```

---

**Seção 7 — Problemas Comuns (Troubleshooting)**

- Porta em uso (Docker):
  - Erro: `bind: address already in use` → opção: pare o processo que usa a porta ou mude as portas no `docker-compose.yml`.

- Erros de migration (ex.: `relation "tenants_tenant" does not exist`):
  - Certifique-se que `python manage.py migrate` e `python manage.py migrate_schemas --shared` foram executados no DB usado pela sessão/CI.
  - Em ambientes concorrentes (tests paralelos), aguarde ou aplique migrações antes de spawnar threads/processos.

- Tenant não resolvido (requests retornam 404/tenant not found):
  - Verifique header `X-TENANT-HOST` e `sessionStorage['tenantHost']` no browser.
  - Verifique existência de `Domain` ligado ao `Tenant` no schema `public`.

- Redis causando 429 (throttling):
  - Em desenvolvimento, ajuste `REDIS_URL` para um DB separado ou use `LocMemCache` para testes rápidos (`saas_backend/settings_test.py` já configura isso).

- Postgres não conectando:
  - Verifique `DATABASE_URL`/`DATABASES` em `.env`. Se usar Docker, confirme que o serviço Postgres está `healthy` (`docker compose ps`).

---

Se algo faltar aqui ou se algum comando falhar no seu ambiente, abra uma issue com o output do comando (`stderr`/`stdout`) e eu o ajudarei a ajustar as instruções para seu sistema.
