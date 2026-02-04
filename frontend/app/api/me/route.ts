import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

// Plan limits configuration
const PLAN_LIMITS = {
  free: { dailyAnalyses: 5, features: ['basic_analysis'] },
  pro: { dailyAnalyses: 50, features: ['basic_analysis', 'advanced_stats', 'export'] },
  elite: { dailyAnalyses: 100, features: ['basic_analysis', 'advanced_stats', 'export', 'picks', 'priority_support'] },
}

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

    // Fetch subscription from database
    const { data: subscription, error: subError } = await supabase
      .from('subscriptions')
      .select('*')
      .eq('user_id', user.id)
      .single()

    // Determine plan (default to free if no subscription)
    const plan = subscription?.plan || 'free'
    const status = subscription?.status || 'active'
    const limits = PLAN_LIMITS[plan as keyof typeof PLAN_LIMITS] || PLAN_LIMITS.free

    // Return user data with no-cache headers
    return NextResponse.json(
      {
        userId: user.id,
        email: user.email,
        plan,
        status,
        limits,
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
