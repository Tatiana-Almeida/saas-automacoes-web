# API Reference (resumo)

Base URL: `/api/v1/`

Autenticação:
- Suporta JWT em header `Authorization: Bearer <token>` e autenticação por cookie JWT.

Endpoints importantes:

- `POST /api/v1/support/tickets/` — criar ticket de suporte (público)
  - body: `{ "email": "...", "subject": "...", "message": "..." }`
  - resposta: `201` com objeto do ticket

- `GET /api/v1/support/tickets/` — listar tickets (admin)
- `GET /api/v1/support/tickets/{id}/` — ver ticket (admin)
- `POST /api/v1/support/tickets/{id}/respond/` — responder/atualizar status (admin)

Documentação OpenAPI disponível em `/api/docs/` e `/api/swagger/`.
