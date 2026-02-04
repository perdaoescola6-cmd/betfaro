-- Tabela locks para evitar execuções simultâneas do cron
CREATE TABLE IF NOT EXISTS public.locks (
  key TEXT PRIMARY KEY,
  run_id UUID,
  acquired_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMPTZ NOT NULL
);

-- Tabela resolve_runs para logs de execução
CREATE TABLE IF NOT EXISTS public.resolve_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  found INTEGER DEFAULT 0,
  processed INTEGER DEFAULT 0,
  resolved INTEGER DEFAULT 0,
  skipped INTEGER DEFAULT 0,
  errors INTEGER DEFAULT 0,
  duration_ms INTEGER DEFAULT 0,
  notes JSONB
);

-- Index para buscar runs recentes
CREATE INDEX IF NOT EXISTS idx_resolve_runs_created_at ON public.resolve_runs(created_at DESC);

-- Limpar runs antigos automaticamente (manter últimos 7 dias)
-- Pode ser executado manualmente ou via cron separado
CREATE OR REPLACE FUNCTION cleanup_old_resolve_runs()
RETURNS void AS $$
BEGIN
  DELETE FROM public.resolve_runs 
  WHERE created_at < NOW() - INTERVAL '7 days';
END;
$$ LANGUAGE plpgsql;
