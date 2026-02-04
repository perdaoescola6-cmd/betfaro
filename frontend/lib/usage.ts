/**
 * Daily Usage Service
 * 
 * Manages daily usage tracking and limit checking.
 * Uses Supabase table: daily_usage
 */

import { SupabaseClient } from '@supabase/supabase-js'
import { getDailyChatLimit, hasUnlimitedChat } from './plans'

export interface DailyUsage {
  user_id: string
  date: string // YYYY-MM-DD
  chat_requests: number
  picks_clicked: number
  bets_added: number
  last_updated: string
}

export interface UsageCheckResult {
  allowed: boolean
  currentUsage: number
  limit: number | 'unlimited'
  remaining: number | 'unlimited'
  reason?: string
}

/**
 * Get today's date in YYYY-MM-DD format (UTC)
 */
export function getTodayDate(): string {
  return new Date().toISOString().split('T')[0]
}

/**
 * Get or create daily usage record for a user
 */
export async function getDailyUsage(
  supabase: SupabaseClient,
  userId: string
): Promise<DailyUsage | null> {
  const today = getTodayDate()
  
  const { data, error } = await supabase
    .from('daily_usage')
    .select('*')
    .eq('user_id', userId)
    .eq('date', today)
    .maybeSingle()
  
  if (error) {
    console.error('Error fetching daily usage:', error)
    return null
  }
  
  return data
}

/**
 * Initialize or get daily usage for a user
 */
export async function getOrCreateDailyUsage(
  supabase: SupabaseClient,
  userId: string
): Promise<DailyUsage> {
  const today = getTodayDate()
  
  // Try to get existing record
  const { data: existing } = await supabase
    .from('daily_usage')
    .select('*')
    .eq('user_id', userId)
    .eq('date', today)
    .maybeSingle()
  
  if (existing) {
    return existing
  }
  
  // Create new record for today
  const newUsage: Partial<DailyUsage> = {
    user_id: userId,
    date: today,
    chat_requests: 0,
    picks_clicked: 0,
    bets_added: 0,
    last_updated: new Date().toISOString()
  }
  
  const { data, error } = await supabase
    .from('daily_usage')
    .upsert(newUsage, { onConflict: 'user_id,date' })
    .select()
    .single()
  
  if (error) {
    console.error('Error creating daily usage:', error)
    // Return a default object if insert fails
    return {
      user_id: userId,
      date: today,
      chat_requests: 0,
      picks_clicked: 0,
      bets_added: 0,
      last_updated: new Date().toISOString()
    }
  }
  
  return data
}

/**
 * Check if user can make a chat request based on their plan and usage
 * 
 * IMPORTANT: Elite users NEVER get blocked
 */
export async function checkChatLimit(
  supabase: SupabaseClient,
  userId: string,
  plan: string
): Promise<UsageCheckResult> {
  // Elite users have unlimited access - bypass all checks
  if (hasUnlimitedChat(plan)) {
    return {
      allowed: true,
      currentUsage: 0, // Don't even check
      limit: 'unlimited',
      remaining: 'unlimited'
    }
  }
  
  const limit = getDailyChatLimit(plan)
  const usage = await getOrCreateDailyUsage(supabase, userId)
  const currentUsage = usage.chat_requests
  
  if (currentUsage >= limit) {
    return {
      allowed: false,
      currentUsage,
      limit,
      remaining: 0,
      reason: `Você atingiu o limite diário de ${limit} análises do plano ${plan.toUpperCase()}. Faça upgrade para continuar.`
    }
  }
  
  return {
    allowed: true,
    currentUsage,
    limit,
    remaining: limit - currentUsage
  }
}

/**
 * Increment chat usage ONLY after successful analysis
 * 
 * This should be called ONLY when:
 * - API-Football returned valid data
 * - Fixture was found
 * - Analysis was successfully built
 * 
 * Errors should NOT consume usage.
 */
export async function incrementChatUsage(
  supabase: SupabaseClient,
  userId: string,
  plan: string
): Promise<boolean> {
  // Elite users don't need tracking (but we track anyway for analytics)
  const today = getTodayDate()
  
  const { error } = await supabase.rpc('increment_chat_usage', {
    p_user_id: userId,
    p_date: today
  })
  
  if (error) {
    // Fallback to manual increment if RPC doesn't exist
    console.warn('RPC increment_chat_usage not found, using fallback:', error.message)
    
    const usage = await getOrCreateDailyUsage(supabase, userId)
    
    const { error: updateError } = await supabase
      .from('daily_usage')
      .upsert({
        user_id: userId,
        date: today,
        chat_requests: usage.chat_requests + 1,
        picks_clicked: usage.picks_clicked,
        bets_added: usage.bets_added,
        last_updated: new Date().toISOString()
      }, { onConflict: 'user_id,date' })
    
    if (updateError) {
      console.error('Error incrementing chat usage:', updateError)
      return false
    }
  }
  
  return true
}

/**
 * Get usage summary for a user (for display in UI)
 */
export async function getUsageSummary(
  supabase: SupabaseClient,
  userId: string,
  plan: string
): Promise<{
  chatUsed: number
  chatLimit: number | 'unlimited'
  chatRemaining: number | 'unlimited'
  picksClicked: number
  betsAdded: number
}> {
  const usage = await getOrCreateDailyUsage(supabase, userId)
  const limit = getDailyChatLimit(plan)
  const isUnlimited = hasUnlimitedChat(plan)
  
  return {
    chatUsed: usage.chat_requests,
    chatLimit: isUnlimited ? 'unlimited' : limit,
    chatRemaining: isUnlimited ? 'unlimited' : Math.max(0, limit - usage.chat_requests),
    picksClicked: usage.picks_clicked,
    betsAdded: usage.bets_added
  }
}
