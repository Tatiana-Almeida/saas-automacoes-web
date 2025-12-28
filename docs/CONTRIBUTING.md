# Contributing

Obrigado por contribuir! Este guia descreve como colaborar com este repositório.

## Fluxo de Trabalho
- Abra uma issue para discutir mudanças significativas.
- Crie uma branch descritiva: `feature/...`, `fix/...`, `docs/...`.
- Faça commits seguindo a convenção: veja [COMMITS.md](./COMMITS.md).
- Abra um Pull Request (PR) com descrição clara, screenshots (se aplicável) e referência à issue.

## Requisitos de PR
- Todos os testes devem passar (se disponíveis).
- Código Python deve seguir PEP8; use linters (`ruff`, `flake8`) e `black` para formatação.
- APIs devem incluir serializers/permissions/urls consistentes.
- Atualize docs se houver mudanças relevantes.

## Segurança
- Evite credenciais em código; use `.env` (confira [.gitignore](../.gitignore)).
- Execute Snyk localmente para mudanças significativas:
  - Python (backend-starter): scan de código
  - Node (backend-node): `npm audit` e Snyk Code se aplicável

## Hooks de Commit (opcionais)
- Husky + commitlint: ver instruções em [COMMITS.md](./COMMITS.md).
- Alternativa: `git config core.hooksPath .githooks` para usar o validador local.

## Ambiente
- Consulte `backend-starter/.env.example` e README para variáveis.
- Use Docker para isolamento quando necessário.

## Revisão
- Mantenha PRs focados e pequenos quando possível.
- Responda revisões rapidamente; faça follow-up com commits claros.
