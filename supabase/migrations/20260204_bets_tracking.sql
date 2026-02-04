-- ============================================
-- MIGRATION: Bets Tracking System
-- Date: 2026-02-04
-- Description: Tables for bet tracking from Chat and Daily Picks
-- ============================================

-- A1) Tabela bets - armazena apostas do usuário
CREATE TABLE IF NOT EXISTS public.bets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  
  -- Source tracking
  source TEXT NOT NULL CHECK (source IN ('chat', 'daily_picks', 'manual')),
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'won', 'lost', 'void', 'cashout')),
  
  -- Match info
  home_team TEXT NOT NULL,
  away_team TEXT NOT NULL,
  fixture_id TEXT,
  league TEXT,
  kickoff_at TIMESTAMPTZ,
  
  -- Bet details (REQUIRED)
  market TEXT NOT NULL,
  odds NUMERIC(6,2) NOT NULL CHECK (odds >= 1.01),
  
  -- Optional details
  stake NUMERIC(10,2),
  note TEXT,
  
  -- Bot recommendation metadata
  bot_reco JSONB,
  value_flag BOOLEAN DEFAULT FALSE,
  
  -- Result tracking
  result_updated_at TIMESTAMPTZ,
  profit_loss NUMERIC(10,2)
);

-- A2) Tabela bet_actions - registra ações (entered/skipped) para analytics
CREATE TABLE IF NOT EXISTS public.bet_actions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  
  -- Action type
  action TEXT NOT NULL CHECK (action IN ('entered', 'skipped')),
  source TEXT NOT NULL CHECK (source IN ('chat', 'daily_picks')),
  
  -- Match info
  home_team TEXT NOT NULL,
  away_team TEXT NOT NULL,
  fixture_id TEXT,
  
  -- Suggested market (if any)
  suggested_market TEXT,
  
  -- Additional metadata
  metadata JSONB
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_bets_user_id ON public.bets(user_id);
CREATE INDEX IF NOT EXISTS idx_bets_status ON public.bets(status);
CREATE INDEX IF NOT EXISTS idx_bets_created_at ON public.bets(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_bets_source ON public.bets(source);
CREATE INDEX IF NOT EXISTS idx_bet_actions_user_id ON public.bet_actions(user_id);
CREATE INDEX IF NOT EXISTS idx_bet_actions_created_at ON public.bet_actions(created_at DESC);

-- ============================================
-- RLS (Row Level Security)
-- ============================================

-- Enable RLS
ALTER TABLE public.bets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.bet_actions ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if any
DROP POLICY IF EXISTS "Users can view own bets" ON public.bets;
DROP POLICY IF EXISTS "Users can insert own bets" ON public.bets;
DROP POLICY IF EXISTS "Users can update own bets" ON public.bets;
DROP POLICY IF EXISTS "Users can delete own bets" ON public.bets;
DROP POLICY IF EXISTS "Users can view own bet_actions" ON public.bet_actions;
DROP POLICY IF EXISTS "Users can insert own bet_actions" ON public.bet_actions;

-- Bets policies
CREATE POLICY "Users can view own bets" ON public.bets
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own bets" ON public.bets
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own bets" ON public.bets
  FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own bets" ON public.bets
  FOR DELETE USING (auth.uid() = user_id);

-- Bet actions policies
CREATE POLICY "Users can view own bet_actions" ON public.bet_actions
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own bet_actions" ON public.bet_actions
  FOR INSERT WITH CHECK (auth.uid() = user_id);

-- ============================================
-- Realtime
-- ============================================

-- Enable realtime for bets table
ALTER PUBLICATION supabase_realtime ADD TABLE public.bets;

-- ============================================
-- Helper function for updated_at
-- ============================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for bets updated_at
DROP TRIGGER IF EXISTS update_bets_updated_at ON public.bets;
CREATE TRIGGER update_bets_updated_at
  BEFORE UPDATE ON public.bets
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();
