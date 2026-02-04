import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import { formatLimitsForApi, getPlanLimits } from '@/lib/plans'
import { getUsageSummary } from '@/lib/usage'

export async function GET(request: NextRequest) {
  try {
    const supabase = await createClient()
    
    const { data: { user }, error: authError } = await supabase.auth.getUser()
    
    if (authError || !user) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      )
    }

    // Fetch subscription from database (SINGLE SOURCE OF TRUTH)
    const { data: subscription } = await supabase
      .from('subscriptions')
      .select('*')
      .eq('user_id', user.id)
      .maybeSingle()

    // Determine effective plan: if no active subscription, treat as free
    const hasActiveSubscription = subscription && subscription.status === 'active'
    const plan = hasActiveSubscription ? (subscription.plan || 'free') : 'free'
    const status = subscription?.status || 'inactive'
    
    // Get plan limits
    const limits = formatLimitsForApi(plan)
    const planConfig = getPlanLimits(plan)
    
    // Get today's usage
    const usage = await getUsageSummary(supabase, user.id, plan)

    // Return user data with no-cache headers
    return NextResponse.json(
      {
        userId: user.id,
        email: user.email,
        plan,
        status,
        isElite: plan.toLowerCase() === 'elite',
        limits: {
          chat: limits.chat,
          picks: limits.picks,
          autoTrack: limits.autoTrack,
          features: limits.features
        },
        usage: {
          chatUsed: usage.chatUsed,
          chatLimit: usage.chatLimit,
          chatRemaining: usage.chatRemaining
        },
        subscription: subscription ? {
          plan: subscription.plan,
          status: subscription.status,
          current_period_end: subscription.current_period_end,
          stripe_customer_id: subscription.stripe_customer_id,
          stripe_subscription_id: subscription.stripe_subscription_id,
        } : null,
        timestamp: new Date().toISOString(),
      },
      {
        headers: {
          'Cache-Control': 'no-store, no-cache, must-revalidate',
          'Pragma': 'no-cache',
        },
      }
    )
  } catch (error) {
    console.error('Error in /api/me:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
