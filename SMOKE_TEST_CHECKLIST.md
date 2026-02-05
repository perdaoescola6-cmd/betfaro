# BetFaro Smoke Test Checklist

**Tempo estimado:** 15-20 minutos  
**Última atualização:** 2026-02-05  
**Versão:** 1.0.0

---

## 📋 Pré-requisitos

Antes de iniciar o smoke test:

- [ ] Backend rodando (`cd backend && uvicorn main:app --reload`)
- [ ] Frontend rodando (`cd frontend && npm run dev`)
- [ ] Supabase configurado e acessível
- [ ] Variáveis de ambiente configuradas (`.env` e `.env.local`)

---

## 1️⃣ Teste de Timezone

**Objetivo:** Confirmar que jogos exibem horário correto no fuso do usuário.

### Passos:

- [ ] Acessar `/picks` (Daily Picks)
- [ ] Verificar se os horários dos jogos estão em **America/Sao_Paulo** (ou timezone do navegador)
- [ ] Comparar com horário UTC da API (deve estar convertido corretamente)

### Expected Results:

- Horários exibidos no formato local (ex: "16:00" para jogo às 19:00 UTC)
- Nenhum horário mostrando "NaN" ou "Invalid Date"

### If fails:

- Verificar `lib/utils.ts` ou componentes de data
- Console do navegador para erros de parsing de data
- Logs do backend para formato de data retornado

---

## 2️⃣ Teste de Consistência Cross-User

**Objetivo:** Garantir que 2 usuários diferentes recebem o mesmo output para a mesma análise.

### Passos:

- [ ] Abrir 2 navegadores diferentes (ou janela anônima)
- [ ] Fazer login com **Conta A** no navegador 1
- [ ] Fazer login com **Conta B** no navegador 2
- [ ] Em ambos, ir para `/chat` (Chat de Análises)
- [ ] Digitar a mesma consulta: `Flamengo vs Palmeiras` (ou outro jogo)
- [ ] Comparar os outputs

### Expected Results:

| Campo | Conta A | Conta B | Match? |
|-------|---------|---------|--------|
| Forma Time A | V E V D V | V E V D V | ✅ |
| Forma Time B | V V E D V | V V E D V | ✅ |
| Over 2.5 % | 65% | 65% | ✅ |
| BTTS % | 55% | 55% | ✅ |
| Média Gols | 2.8 | 2.8 | ✅ |

### If fails:

- Verificar `analysis_logger.py` para logs de auditoria
- Comparar `fixture_ids` usados em cada análise
- Verificar se há cache por usuário interferindo

---

## 3️⃣ Teste de Tracking (Bets)

**Objetivo:** Validar fluxo completo de criação e resolução de bets.

### 3.1 Adicionar Bet Manual

- [ ] Ir para `/dashboard`
- [ ] Clicar em "Adicionar Aposta" (ou botão equivalente)
- [ ] Preencher:
  - Home Team: `Arsenal`
  - Away Team: `Chelsea`
  - Market: `Over 2.5`
  - Odds: `1.85`
  - Stake: `100`
- [ ] Salvar
- [ ] Verificar que bet aparece na lista com status **pending**

### 3.2 Adicionar Bet via Chat/Picks

- [ ] Ir para `/chat` ou `/picks`
- [ ] Fazer análise de um jogo
- [ ] Clicar em "Fiz a bet" ou "Adicionar aposta"
- [ ] Verificar que modal abre com dados pré-preenchidos
- [ ] Confirmar criação
- [ ] Verificar que bet aparece no `/dashboard` como **pending**

### 3.3 Resolver Bets (Simular)

- [ ] Aguardar jogo terminar OU simular via Supabase:
  ```sql
  UPDATE public.bets 
  SET status = 'won', 
      profit_loss = stake * (odds - 1),
      result_updated_at = NOW()
  WHERE id = '<bet_id>';
  ```
- [ ] Verificar que Dashboard atualiza:
  - Status: `won` ou `lost`
  - Profit/Loss calculado corretamente
  - Win Rate e ROI atualizados

### Expected Results:

- Bet manual criada com source = `manual`
- Bet via chat criada com source = `chat`
- Após resolução: status atualizado, profit_loss correto

### If fails:

- Verificar tabela `public.bets` no Supabase
- Verificar RLS policies estão ativas
- Console do navegador para erros de API

---

## 4️⃣ Teste de Edge Cases

**Objetivo:** Validar comportamento com dados incompletos ou inválidos.

### 4.1 Time com Poucos Jogos

- [ ] No `/chat`, digitar nome de time pequeno/novo
- [ ] Verificar mensagem de erro clara

### Expected Results:

- Mensagem: "Dados insuficientes (X/10 jogos)" ou similar
- **NÃO** deve mostrar estatísticas inventadas
- **NÃO** deve crashar

### 4.2 Jogo com Status Não-Finalizado

- [ ] Se possível, tentar analisar jogo que ainda não terminou
- [ ] Verificar que sistema não usa esse jogo nos cálculos

### Expected Results:

- Apenas jogos FT/AET/PEN são usados
- Jogos NS/TBD/CANC/PST são ignorados

### 4.3 Time Ambíguo

- [ ] No `/chat`, digitar nome ambíguo: `United`
- [ ] Verificar que sistema pede clarificação

### Expected Results:

- Mensagem pedindo para especificar qual time
- Lista de opções (Manchester United, Newcastle United, etc.)

### If fails:

- Verificar logs em `analysis_logger.py`
- Verificar `fixture_processor.py` para filtros
- Tabela `resolve_runs` para erros de resolução

---

## 5️⃣ Teste de UI

**Objetivo:** Validar que UI não quebra com dados variados.

### 5.1 Nomes Longos

- [ ] Verificar que times com nomes longos não quebram layout
- [ ] Exemplos: "Borussia Mönchengladbach", "Wolverhampton Wanderers"

### Expected Results:

- Texto truncado com "..." se necessário
- Layout não quebra
- Tooltip mostra nome completo (se implementado)

### 5.2 Botão "Adicionar Aposta"

- [ ] Verificar que botão aparece em todas as tips do `/picks`
- [ ] Verificar que botão aparece após análise no `/chat`

### Expected Results:

- Botão visível e clicável
- Abre modal de criação de bet

### 5.3 Sidebar/Navegação

- [ ] Verificar que sidebar aparece em todas as páginas:
  - [ ] `/` (Home)
  - [ ] `/chat`
  - [ ] `/picks`
  - [ ] `/dashboard`
  - [ ] `/account`

### Expected Results:

- Navegação consistente em todas as páginas
- Links funcionando corretamente

### If fails:

- Inspecionar elementos no DevTools
- Verificar CSS/Tailwind classes
- Verificar componentes de layout

---

## 6️⃣ Verificação Final

### Logs e Monitoramento

- [ ] Verificar que não há erros críticos no console do navegador
- [ ] Verificar logs do backend (uvicorn) para erros
- [ ] Verificar tabela `resolve_runs` no Supabase para erros de resolução

### Checklist de Sanidade

- [ ] Login/Logout funcionando
- [ ] Chat responde em < 5 segundos
- [ ] Dashboard carrega corretamente
- [ ] Picks do dia aparecem (se houver jogos)

---

## 📊 Resultado do Smoke Test

| Seção | Status | Notas |
|-------|--------|-------|
| 1. Timezone | ⬜ | |
| 2. Cross-User | ⬜ | |
| 3. Tracking | ⬜ | |
| 4. Edge Cases | ⬜ | |
| 5. UI | ⬜ | |
| 6. Final | ⬜ | |

**Status Geral:** ⬜ PENDENTE / ✅ APROVADO / ❌ BLOQUEADO

**Testado por:** _______________  
**Data:** _______________  
**Ambiente:** ⬜ Local / ⬜ Staging / ⬜ Produção

---

## 🔧 Troubleshooting

### Onde encontrar logs:

| Componente | Localização |
|------------|-------------|
| Backend | Terminal do uvicorn |
| Frontend | Console do navegador (F12) |
| Análises | `analysis_logger.py` → stdout |
| Bets | Supabase → `public.bets` |
| Resolução | Supabase → `public.resolve_runs` |
| Erros de API | Supabase → Logs |

### Comandos úteis:

```bash
# Ver logs do backend
cd backend && uvicorn main:app --reload --log-level debug

# Rodar testes unitários
cd backend && python -m pytest tests/ -v

# Verificar bets no Supabase
SELECT * FROM public.bets ORDER BY created_at DESC LIMIT 10;

# Verificar resolve_runs
SELECT * FROM public.resolve_runs ORDER BY created_at DESC LIMIT 5;
```

---

## 📝 Notas Adicionais

_Use este espaço para anotar observações durante o teste:_

```
[Data] - [Observação]


```
