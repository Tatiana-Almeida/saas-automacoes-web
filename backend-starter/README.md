# Starter Backend (Django + DRF + python-decouple)

Este diretório contém uma configuração inicial e escalável para um SaaS de automações, usando Django, Django REST Framework e variáveis de ambiente com python-decouple.

## Principais pontos
- Separação de settings: base/dev/prod
- Variáveis via `.env` (python-decouple)
- DRF pronto e endpoint de saúde em `/health/`
- Banco PostgreSQL por padrão
- Dockerfile + docker-compose para subir localmente

## Como rodar

### Sem Docker
```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env  # crie seu .env
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

### Com Docker
```bash
copy .env.example .env
docker compose up --build
```

Acesse: http://localhost:8000/health/

## Produção
- Use `starter.settings.prod` via `DJANGO_SETTINGS_MODULE` no ambiente do servidor
- Sirva arquivos estáticos via CDN ou servidor web
- Utilize Gunicorn (já configurado no Dockerfile)

## Contribuição & Commits
- Siga a convenção em [docs/COMMITS.md](../docs/COMMITS.md).
- Opcional: habilite hooks locais com Husky ou `.githooks` (veja o guia).

## Estrutura
- `starter/settings/base.py`: configurações base
- `starter/settings/dev.py`: desenvolvimento
- `starter/settings/prod.py`: produção
- `starter/core`: app inicial com rota de saúde

```text
backend-starter/
  Dockerfile
  docker-compose.yml
  manage.py
  requirements.txt
  .env.example
  starter/
    __init__.py
    asgi.py
    wsgi.py
    urls.py
    settings/
      __init__.py
      base.py
      dev.py
      prod.py
    core/
      __init__.py
      apps.py
      urls.py
      views.py
```

> Observação: Este starter não altera o projeto que já existe em `backend/`. Ele é um template minimalista pronto para uso.

## Auth & CORS
- JWT Endpoints: `/api/auth/token/` (obtain), `/api/auth/refresh/` (refresh)
- Endpoint protegido: `/api/users/me` retorna informações do usuário autenticado
- Envie `Authorization: Bearer <access_token>` em requisições protegidas
- CORS configurável via `CORS_ALLOWED_ORIGINS` no `.env`
- Tempos de token via `ACCESS_TOKEN_LIFETIME_MIN` e `REFRESH_TOKEN_LIFETIME_DAYS`

## DRF
- Permissões padrão: `IsAuthenticated` (em dev: `AllowAny`)
- Autenticação preparada: `JWTAuthentication` como padrão
- Estrutura base: `starter/api/serializers.py` e `starter/api/views.py` para herança comum
 - Regras: APIs CRUD usam `IsAdminOrReadOnly` (admin escreve; cliente leitura)

## Email
- Configure `EMAIL_*` no `.env`
- Teste rápido:
```ps1
cd "C:\Users\Tatiana Almeida\Documents\SAAS\SAAS DE AUTOMAÇÕES WEB\backend-starter"
python manage.py send_test_email --to teste@exemplo.com --subject "Hello" --body "Email de teste"
```

## Tenants
- CRUD básico em `/api/tenants` (autenticado via JWT)
- Modelo: `Tenant` com `id` (UUID), `name`, `slug`, `is_active`, timestamps
- Admin: gerencie tenants via `/admin/`

### Exemplos (curl)
Criar tenant:
```bash
curl -X POST http://localhost:8000/api/tenants/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{"name": "Acme", "slug": "acme"}'
```

Listar tenants:
```bash
curl http://localhost:8000/api/tenants/ \
  -H "Authorization: Bearer <access_token>"
```

## E-commerce APIs
- Products: `/api/products` (CRUD)
- Orders: `/api/orders` (CRUD)
- Automations: `/api/automations` (CRUD)
- Subscriptions: `/api/subscriptions` (CRUD)
- Notifications: `/api/notifications` (CRUD)

Todos exigem JWT (`Authorization: Bearer <access_token>`)

### Exemplos (curl)
Obter token (email + senha):
```bash
curl -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@exemplo.com", "password": "<sua_senha>"}'
```

Resposta inclui tokens e info do usuário:
```json
{
  "refresh": "<refresh_token>",
  "access": "<access_token>",
  "user": { "id": 1, "email": "admin@exemplo.com", "role": "admin", "is_staff": true }
}
```

Usar token para acessar `/api/users/me`:
```bash
curl http://localhost:8000/api/users/me \
  -H "Authorization: Bearer <access_token>"
```

### Variáveis de Ambiente relevantes
- `CORS_ALLOWED_ORIGINS`: lista de origens permitidas (ex.: `http://localhost:3000`)
- `ACCESS_TOKEN_LIFETIME_MIN`: minutos para expiração do access token (ex.: `15`)
- `REFRESH_TOKEN_LIFETIME_DAYS`: dias para expiração do refresh token (ex.: `7`)
 - `DATABASE_URL`: URL única do banco (ex.: `postgres://user:pass@host:5432/db`)
 - `EMAIL_*`: configurações de email (host/porta/TLS/SSL/credenciais)
