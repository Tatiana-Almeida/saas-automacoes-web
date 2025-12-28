# FAQ

Q: Como abro um chamado de suporte?
A: Use o formulário na landing page ou `POST /api/v1/support/tickets/`.

Q: Posso usar minha própria instância Postgres?
A: Sim — configure `DATABASE_URL` em `.env`.

Q: Como integrar com ferramentas de marketing?
A: O sistema envia eventos (cadastro, login, compra) para ferramentas via snippets de analytics; integrações com CRMs serão adicionadas via webhooks/integrações.
