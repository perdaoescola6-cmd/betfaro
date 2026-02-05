# BetFaro E2E Tests

Testes End-to-End usando Playwright.

## Setup

```bash
cd e2e
npm install
npx playwright install
```

## Executar Testes

```bash
# Rodar todos os testes
npm test

# Rodar com browser visível
npm run test:headed

# Rodar em modo debug
npm run test:debug

# Abrir UI do Playwright
npm run test:ui

# Ver relatório
npm run report
```

## Variáveis de Ambiente

| Variável | Descrição | Default |
|----------|-----------|---------|
| `BASE_URL` | URL do frontend | `http://localhost:3000` |

## Estrutura

```
e2e/
├── playwright.config.ts    # Configuração do Playwright
├── package.json            # Dependências
├── tests/
│   ├── smoke.spec.ts       # Testes básicos de UI
│   ├── chat-flow.spec.ts   # Testes do chat de análise
│   └── bet-tracking.spec.ts # Testes de tracking de bets
└── README.md
```

## Pré-requisitos

1. Frontend rodando em `http://localhost:3000`
2. Backend rodando em `http://localhost:8000`
3. Supabase configurado

## Notas

- Os testes de smoke rodam sem autenticação
- Testes de chat e bet tracking podem requerer login
- Use `test.skip()` para pular testes que requerem auth em CI
