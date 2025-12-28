# Tutoriais

1. Enviar uma mensagem via API

Exemplo mínimo (autenticado):

```
POST /api/v1/core/messages/
{
  "to": "+5511999999999",
  "channel": "whatsapp",
  "body": "Olá!"
}
```

2. Criar workflow simples

- Entre na área de workflows no painel, clique em "Novo workflow" e adicione passos.
