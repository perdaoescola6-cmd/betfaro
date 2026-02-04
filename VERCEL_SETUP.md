# Vercel Deploy Setup - Configuração Obrigatória

## Problema Identificado
O Vercel não está sincronizado com o GitHub - faz redeploy de commits antigos em vez de buscar o código mais recente.

## Solução: Deploy via GitHub Actions + Vercel CLI

O GitHub Actions faz checkout do código atual e usa o Vercel CLI para fazer deploy diretamente.

### Passo 1: Criar Token no Vercel

1. Vá em: https://vercel.com/account/tokens
2. Clique em **Create Token**
3. Nome: `github-actions-betfaro`
4. Scope: Full Account
5. Clique **Create**
6. **COPIE O TOKEN** (só aparece uma vez!)

### Passo 2: Obter IDs do Projeto

1. Vá em: https://vercel.com/leonardos-projects-87c281c0/betfaro/settings
2. Role até **Project ID** e copie
3. O **Org ID** está em: https://vercel.com/account → General → Your ID

Ou use o Vercel CLI localmente:
```bash
cd frontend
npx vercel link
cat .vercel/project.json
```

### Passo 3: Adicionar Secrets no GitHub

Vá em: https://github.com/perdaoescola6-cmd/betfaro/settings/secrets/actions

Adicione **3 secrets**:

| Name | Valor |
|------|-------|
| `VERCEL_TOKEN` | Token criado no passo 1 |
| `VERCEL_ORG_ID` | Seu Org/Team ID |
| `VERCEL_PROJECT_ID` | Project ID do betfaro (ex: `prj_A2sAqXIEXJZa5SKxbOQeMZQqHkx5`) |

### Passo 4: Pronto!

Agora todo push na branch `main` vai:
1. Fazer checkout do código atual do GitHub
2. Instalar Vercel CLI
3. Build do projeto localmente
4. Deploy para Vercel com o código correto
5. Verificar se o site responde HTTP 200
6. Verificar se a API retorna o formato correto

### Como validar em 30 segundos

1. Faça um push
2. Vá em https://github.com/perdaoescola6-cmd/betfaro/actions
3. Veja o workflow "Vercel Deploy" rodando
4. Quando terminar com ✅, o deploy está feito e verificado

## Checklist de Configuração

- [ ] Token criado no Vercel
- [ ] Secret `VERCEL_TOKEN` adicionado no GitHub
- [ ] Secret `VERCEL_ORG_ID` adicionado no GitHub  
- [ ] Secret `VERCEL_PROJECT_ID` adicionado no GitHub
- [ ] Workflow `.github/workflows/vercel-deploy.yml` existe no repo
- [ ] Push de teste feito
- [ ] Workflow rodou com sucesso
- [ ] API retorna formato `items` (não `suggestions`)
