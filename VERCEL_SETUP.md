# Vercel Deploy Setup - Configuração Obrigatória

## Problema Identificado
O Vercel não está recebendo webhooks do GitHub automaticamente, causando deploys com commits antigos.

## Solução: Deploy via GitHub Actions + Deploy Hook

### Passo 1: Criar Deploy Hook no Vercel

1. Vá em: https://vercel.com/leonardos-projects-87c281c0/betfaro/settings/git
2. Role até **Deploy Hooks**
3. Preencha:
   - **Name:** `Production`
   - **Branch:** `main`
4. Clique em **Create Hook**
5. **COPIE A URL** que aparecer (ex: `https://api.vercel.com/v1/integrations/deploy/...`)

### Passo 2: Adicionar Secret no GitHub

1. Vá em: https://github.com/perdaoescola6-cmd/betfaro/settings/secrets/actions
2. Clique em **New repository secret**
3. Preencha:
   - **Name:** `VERCEL_DEPLOY_HOOK`
   - **Secret:** (cole a URL do Deploy Hook)
4. Clique em **Add secret**

### Passo 3: Pronto!

Agora todo push na branch `main` vai:
1. Triggerar o GitHub Actions workflow
2. Chamar o Deploy Hook do Vercel
3. Aguardar 90 segundos
4. Verificar se o site está respondendo HTTP 200
5. Verificar se a API está funcionando

### Como validar em 30 segundos

1. Faça um push
2. Vá em https://github.com/perdaoescola6-cmd/betfaro/actions
3. Veja o workflow "Vercel Deploy" rodando
4. Quando terminar com ✅, o deploy está feito e verificado

## Checklist de Configuração

- [ ] Deploy Hook criado no Vercel
- [ ] Secret `VERCEL_DEPLOY_HOOK` adicionado no GitHub
- [ ] Workflow `.github/workflows/vercel-deploy.yml` existe no repo
- [ ] Push de teste feito
- [ ] Workflow rodou com sucesso
