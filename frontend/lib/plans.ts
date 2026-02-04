/**
 * Plan Configuration - Single Source of Truth
 * 
 * This file defines all plan limits and features.
 * Backend and frontend should use these values consistently.
 */

export type PlanType = 'free' | 'pro' | 'elite'

export interface PlanLimits {
  dailyChat: number | 'unlimited'
  picksAccess: boolean
  autoTrack: boolean
  features: string[]
}

export const PLAN_CONFIG: Record<PlanType, PlanLimits> = {
  free: {
    dailyChat: 5,
    picksAccess: false,
    autoTrack: false,
    features: ['basic_analysis']
  },
  pro: {
    dailyChat: 25,
    picksAccess: false,
    autoTrack: false,
    features: ['basic_analysis', 'advanced_stats', 'export']
  },
  elite: {
    dailyChat: 'unlimited',
    picksAccess: true,
    autoTrack: true,
    features: ['basic_analysis', 'advanced_stats', 'export', 'picks', 'auto_track', 'priority_support']
  }
}

/**
 * Get plan limits for a given plan
 */
export function getPlanLimits(plan: string | null | undefined): PlanLimits {
  const normalizedPlan = (plan?.toLowerCase() || 'free') as PlanType
  return PLAN_CONFIG[normalizedPlan] || PLAN_CONFIG.free
}

/**
 * Check if a plan has unlimited chat
 */
export function hasUnlimitedChat(plan: string | null | undefined): boolean {
  const limits = getPlanLimits(plan)
  return limits.dailyChat === 'unlimited'
}

/**
 * Get the daily chat limit for a plan (returns Infinity for unlimited)
 */
export function getDailyChatLimit(plan: string | null | undefined): number {
  const limits = getPlanLimits(plan)
  return limits.dailyChat === 'unlimited' ? Infinity : limits.dailyChat
}

/**
 * Format limits for API response
 */
export function formatLimitsForApi(plan: string | null | undefined) {
  const limits = getPlanLimits(plan)
  return {
    chat: limits.dailyChat === 'unlimited' ? 'unlimited' : limits.dailyChat,
    picks: limits.picksAccess,
    autoTrack: limits.autoTrack,
    features: limits.features
  }
}
