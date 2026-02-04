-- Create daily_usage table for tracking user usage limits
-- This is the source of truth for daily usage tracking

CREATE TABLE IF NOT EXISTS public.daily_usage (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    chat_requests INTEGER NOT NULL DEFAULT 0,
    picks_clicked INTEGER NOT NULL DEFAULT 0,
    bets_added INTEGER NOT NULL DEFAULT 0,
    last_updated TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Unique constraint: one record per user per day
    CONSTRAINT daily_usage_user_date_unique UNIQUE (user_id, date)
);

-- Create index for fast lookups
CREATE INDEX IF NOT EXISTS idx_daily_usage_user_date ON public.daily_usage(user_id, date);
CREATE INDEX IF NOT EXISTS idx_daily_usage_date ON public.daily_usage(date);

-- Enable RLS
ALTER TABLE public.daily_usage ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their own usage
CREATE POLICY "Users can view own usage" ON public.daily_usage
    FOR SELECT USING (auth.uid() = user_id);

-- Policy: Users can insert their own usage
CREATE POLICY "Users can insert own usage" ON public.daily_usage
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Policy: Users can update their own usage
CREATE POLICY "Users can update own usage" ON public.daily_usage
    FOR UPDATE USING (auth.uid() = user_id);

-- Policy: Service role can do everything (for API routes)
CREATE POLICY "Service role full access" ON public.daily_usage
    FOR ALL USING (auth.role() = 'service_role');

-- Function to increment chat usage atomically
CREATE OR REPLACE FUNCTION public.increment_chat_usage(p_user_id UUID, p_date DATE)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    INSERT INTO public.daily_usage (user_id, date, chat_requests, last_updated)
    VALUES (p_user_id, p_date, 1, NOW())
    ON CONFLICT (user_id, date)
    DO UPDATE SET 
        chat_requests = daily_usage.chat_requests + 1,
        last_updated = NOW();
END;
$$;

-- Function to increment picks clicked atomically
CREATE OR REPLACE FUNCTION public.increment_picks_clicked(p_user_id UUID, p_date DATE)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    INSERT INTO public.daily_usage (user_id, date, picks_clicked, last_updated)
    VALUES (p_user_id, p_date, 1, NOW())
    ON CONFLICT (user_id, date)
    DO UPDATE SET 
        picks_clicked = daily_usage.picks_clicked + 1,
        last_updated = NOW();
END;
$$;

-- Function to increment bets added atomically
CREATE OR REPLACE FUNCTION public.increment_bets_added(p_user_id UUID, p_date DATE)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    INSERT INTO public.daily_usage (user_id, date, bets_added, last_updated)
    VALUES (p_user_id, p_date, 1, NOW())
    ON CONFLICT (user_id, date)
    DO UPDATE SET 
        bets_added = daily_usage.bets_added + 1,
        last_updated = NOW();
END;
$$;

-- Grant execute permissions
GRANT EXECUTE ON FUNCTION public.increment_chat_usage TO authenticated;
GRANT EXECUTE ON FUNCTION public.increment_picks_clicked TO authenticated;
GRANT EXECUTE ON FUNCTION public.increment_bets_added TO authenticated;

-- Comment for documentation
COMMENT ON TABLE public.daily_usage IS 'Tracks daily usage per user for rate limiting. Elite users bypass limits but usage is still tracked for analytics.';
