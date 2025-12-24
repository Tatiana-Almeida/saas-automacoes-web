# Backend Node (Runner Intermediário)

Serviço Express minimalista para validação local enquanto a stack Django roda via Docker. Oferece autenticação, health, RBAC simples e rate limiting por plano usando o header `x-plan`.

## Requisitos
- Node.js 18+
- Windows PowerShell (para o smoke test)

## Instalação e Execução
```powershell
cd "c:\\Users\\Tatiana Almeida\\Documents\\SAAS\\SAAS DE AUTOMAÇÕES WEB\\backend-node"
npm ci
npm start
```
- Servidor: http://127.0.0.1:3001
- Variáveis de ambiente (opcional):
  - `JWT_SECRET`: chave usada para assinar JWT (defina em produção)
  - `TOKEN_TTL`: tempo de vida do token (ex.: `1h`)
  - `PORT`: porta do servidor (padrão `3001`)

## Smoke Test
Com o servidor em execução:
```powershell
npm run smoke
```
O teste valida: `/api/v1/health`, registro e login, `Authorization: Bearer <token>`, `/api/v1/users/me` e `/api/v1/auth/admin/ping`.

## Endpoints
- GET `/api/v1/health` → `{ status: "ok" }`
- POST `/api/v1/auth/register` corpo: `{ email, password, role? }`
- POST `/api/v1/auth/login` corpo: `{ email, password }` → `{ token, user }`
- GET `/api/v1/users/me` cabeçalho: `Authorization: Bearer <token>`
- GET `/api/v1/auth/admin/ping` cabeçalho: `Authorization: Bearer <token>` (requer `role` = `admin`)

## Rate Limiting por Plano
Use o header `x-plan` com valores `free`, `pro` ou `enterprise`.
Exemplo: `x-plan: pro`.

## Segurança
- Em produção, defina `JWT_SECRET` diferente de `dev-secret-change-me` (o serviço encerra se `NODE_ENV=production` e a secret padrão for usada).
- Este serviço mantém usuários em memória e destina-se apenas a validações locais.
- Limitação defensiva: há um guard de tamanho de URL (2048 caracteres) para reduzir superfície de ReDoS em roteamento.

```
Estrutura relevante
- src/server.js        # inicialização, middlewares, rotas básicas
- src/auth.js          # registro, login, JWT e RBAC
- src/config.js        # variáveis e limites por plano
- scripts/smoke.ps1    # teste rápido (PowerShell)
 - scripts/start-bg.ps1 # inicia servidor em background + health check
 - scripts/stop-bg.ps1  # encerra jobs em background (PowerShell)
```

## Modo Dev e Background

```powershell
# Executa com nodemon (auto-reload; primeira vez instale deps)
npm install
npm run dev

# Inicia em background + health check
npm run start:bg

# Para o background job atual
npm run stop:bg
```