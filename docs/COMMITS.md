# Convenção de Commits

Formato: `tipo(escopo): assunto curto no imperativo`

## Tipos
- feat: nova funcionalidade
- fix: correção de bug
- docs: documentação
- style: formatação (sem alteração de lógica)
- refactor: refatoração interna
- perf: melhoria de performance
- test: testes
- build: mudanças em build/deps
- ci: pipelines de CI
- chore: manutenção geral
- revert: reverte commit anterior

## Escopos
Use nome da app/área:
- users, tenants, products, orders, automations, subscriptions, notifications
- api, settings, auth, docs, infra, ci

## Assunto
- Curto (até ~72 chars), no imperativo ("adicionar", "corrigir")
- Sem ponto final

## Quebra de compatibilidade
- `feat!:` ou `fix!:` para indicar breaking change
- Detalhar no rodapé:
  - BREAKING CHANGE: descrição do impacto e migração

## Exemplos
- feat(users): adicionar endpoint de perfil
- fix(orders): corrigir cálculo de total no serializer
- docs: atualizar README com variáveis de ambiente
- refactor(api): simplificar BaseViewSet para filtros
- chore(ci): atualizar pipeline para Python 3.12
- feat(auth)!: migrar tokens para SimpleJWT
- BREAKING CHANGE: tokens antigos deixam de funcionar

---

# Enforce local (opções)

## Opção A: Husky + Commitlint
1. Instalar dependências na raiz do repositório:
   ```bash
   npm install --save-dev @commitlint/cli @commitlint/config-conventional husky
   npx husky install
   npx husky add .husky/commit-msg "npx --no-install commitlint --edit $1"
   ```
2. Arquivo `commitlint.config.js` deve existir na raiz com:
   ```js
   module.exports = { extends: ['@commitlint/config-conventional'] };
   ```

## Opção B: Git hooks via core.hooksPath
1. Definir hooks path local:
   ```bash
   git config core.hooksPath .githooks
   ```
2. O hook `commit-msg` chama um validador Node (`tools/commit-msg.js`).

> Dica: em ambientes Windows, usar Git Bash para execução de hooks shell, ou a opção A com Husky.
