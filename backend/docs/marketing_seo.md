# Marketing & SEO básico

- Título da página principal: inclua palavras-chave (ex: "SaaS de automações | Mensagens, Workflows e Integrações").
- Meta description curta e convincente.
- Uso de header tags (`h1`, `h2`) e conteúdo legível.
- Links socials, plano e CTA visíveis.

Analytics:
- Insira Google Analytics / GA4 com `G-XXXXXX` e registre eventos: `sign_up`, `login`, `purchase`, `support_ticket`.

Server-side events:
- To send server-side events (recommended for purchases), set the env vars `GA_MEASUREMENT_ID` and `GA_API_SECRET` and use the helper `apps.core.analytics.track_event(event_name, user, params)`.
- Example events to track: `sign_up`, `login`, `purchase`, `support_ticket`.
