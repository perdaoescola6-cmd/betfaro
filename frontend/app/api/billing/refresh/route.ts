import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import { createAdminClient } from '@/lib/supabase/admin'
import { getStripe, getPlanFromPriceId } from '@/lib/stripe'

export async function POST(request: NextRequest) {
  try {
    const supabase = await createClient()
    
    const { data: { user }, error: authError } = await supabase.auth.getUser()
    
    if (authError || !user) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      )
    }

    console.log(`[REFRESH] Starting sync for user ${user.id} (${user.email})`)

    const stripe = getStripe()
    const adminSupabase = createAdminClient()

    // Get current subscription from database
    const { data: dbSubscription } = await adminSupabase
      .from('subscriptions')
      .select('*')
      .eq('user_id', user.id)
      .single()

    let customerId = dbSubscription?.stripe_customer_id

    // If no customer ID, search by email
    if (!customerId && user.email) {
      console.log(`[REFRESH] No customer ID, searching by email: ${user.email}`)
      const customers = await stripe.customers.list({
        email: user.email,
        limit: 1,
      })
      if (customers.data.length > 0) {
        customerId = customers.data[0].id
        console.log(`[REFRESH] Found customer by email: ${customerId}`)
      }
    }

    if (!customerId) {
      console.log(`[REFRESH] No Stripe customer found for user ${user.id}`)
      return NextResponse.json({
        success: true,
        plan: 'free',
        status: 'active',
        synced: false,
        message: 'No Stripe customer found',
      })
    }

    // Get active subscriptions for this customer
    const subscriptions = await stripe.subscriptions.list({
      customer: customerId,
      status: 'active',
      limit: 1,
    })

    // Also check for trialing subscriptions
    if (subscriptions.data.length === 0) {
      const trialingSubscriptions = await stripe.subscriptions.list({
        customer: customerId,
        status: 'trialing',
        limit: 1,
      })
      subscriptions.data = trialingSubscriptions.data
    }

    if (subscriptions.data.length === 0) {
      console.log(`[REFRESH] No active subscription for customer ${customerId}`)
      
      // Update to free if no active subscription
      await adminSupabase
        .from('subscriptions')
        .upsert({
          user_id: user.id,
          plan: 'free',
          status: 'canceled',
          stripe_customer_id: customerId,
          updated_at: new Date().toISOString(),
        })

      return NextResponse.json({
        success: true,
        plan: 'free',
        status: 'canceled',
        synced: true,
        message: 'No active subscription',
      })
    }

    // Get the active subscription
    const stripeSubscription = subscriptions.data[0] as any
    const priceId = stripeSubscription.items.data[0]?.price.id
    const plan = getPlanFromPriceId(priceId) || 'pro'
    const periodEnd = stripeSubscription.current_period_end 
      ? new Date(stripeSubscription.current_period_end * 1000).toISOString()
      : new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString()

    console.log(`[REFRESH] Found subscription: ${stripeSubscription.id}, plan: ${plan}, status: ${stripeSubscription.status}`)

    // Update database with Stripe data
    const { error: updateError } = await adminSupabase
      .from('subscriptions')
      .upsert({
        user_id: user.id,
        plan,
        status: stripeSubscription.status,
        provider: 'stripe',
        stripe_customer_id: customerId,
        stripe_subscription_id: stripeSubscription.id,
        stripe_price_id: priceId,
        current_period_end: periodEnd,
        updated_at: new Date().toISOString(),
      })

    if (updateError) {
      console.error('[REFRESH] Error updating subscription:', updateError)
      return NextResponse.json({
        success: false,
        error: 'Failed to update subscription',
        plan: dbSubscription?.plan || 'free',
      }, { status: 500 })
    }

    console.log(`[REFRESH] Successfully synced: user ${user.id} -> plan ${plan}`)

    return NextResponse.json({
      success: true,
      plan,
      status: stripeSubscription.status,
      synced: true,
    })

  } catch (error) {
    console.error('[REFRESH] Error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
