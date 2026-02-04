# Vercel Deploy Setup - Configuração Obrigatória

## Problema Identificado
O Vercel não está recebendo webhooks do GitHub, causando deploys com commits antigos.

## Solução: Deploy via GitHub Actions

### Passo 1: Obter credenciais do Vercel

1. **VERCEL_TOKEN**: 
   - Vá em https://vercel.com/account/tokens
   - Clique em "Create Token"
   - Nome: `github-actions`
   - Copie o token gerado

2. **VERCEL_ORG_ID** e **VERCEL_PROJECT_ID**:
   - No terminal, na pasta `frontend/`, rode:
   ```bash
   npx vercel link
   ```
   - Isso vai criar um arquivo `.vercel/project.json` com os IDs
   - Ou vá em Vercel Dashboard → Settings → General → Project ID

### Passo 2: Adicionar Secrets no GitHub

Vá em: https://github.com/perdaoescola6-cmd/betfaro/settings/secrets/actions

Adicione 3 secrets:
- `VERCEL_TOKEN` = (token criado no passo 1)
- `VERCEL_ORG_ID` = (seu org/team ID do Vercel)
- `VERCEL_PROJECT_ID` = (project ID do betfaro)

### Passo 3: Testar

Faça um push na branch `main`. O GitHub Actions vai:
1. Fazer checkout do código
2. Instalar Vercel CLI
3. Build do projeto
4. Deploy para produção
5. Verificar se o site está respondendo HTTP 200

### Como validar em 30 segundos

1. Faça um push
2. Vá em https://github.com/perdaoescola6-cmd/betfaro/actions
3. Veja o workflow "Vercel Deploy" rodando
4. Quando terminar com ✅, o deploy está feito

## Alternativa: Usar Deploy Hook

Se preferir não usar GitHub Actions, crie um Deploy Hook no Vercel e adicione como webhook no GitHub:

1. Vercel → Settings → Git → Deploy Hooks → Create Hook (branch: main)
2. Copie a URL
3. GitHub → Settings → Webhooks → Add webhook
4. Payload URL: (cole a URL do hook)
5. Content type: application/json
6. Events: Just the push event
