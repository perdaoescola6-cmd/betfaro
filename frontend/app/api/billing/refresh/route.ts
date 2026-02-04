import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import { getStripe } from '@/lib/stripe'

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

    // Get current subscription from database
    const { data: subscription } = await supabase
      .from('subscriptions')
      .select('*')
      .eq('user_id', user.id)
      .single()

    // If we have a Stripe subscription ID, sync with Stripe
    if (subscription?.stripe_subscription_id) {
      try {
        const stripe = getStripe()
        const stripeSubscription = await stripe.subscriptions.retrieve(
          subscription.stripe_subscription_id
        ) as any

        // Map Stripe price to plan
        const priceId = stripeSubscription.items.data[0]?.price.id
        let plan = 'free'
        
        const proPriceId = process.env.STRIPE_PRO_PRICE_ID
        const elitePriceId = process.env.STRIPE_ELITE_PRICE_ID
        
        if (priceId === elitePriceId) {
          plan = 'elite'
        } else if (priceId === proPriceId) {
          plan = 'pro'
        }

        // Update database with latest Stripe data
        const { error: updateError } = await supabase
          .from('subscriptions')
          .update({
            plan,
            status: stripeSubscription.status,
            current_period_end: new Date(stripeSubscription.current_period_end * 1000).toISOString(),
            updated_at: new Date().toISOString(),
          })
          .eq('user_id', user.id)

        if (updateError) {
          console.error('Error updating subscription:', updateError)
        }

        return NextResponse.json({
          success: true,
          plan,
          status: stripeSubscription.status,
          synced: true,
        })
      } catch (stripeError) {
        console.error('Error fetching Stripe subscription:', stripeError)
        // Return current database state if Stripe fails
        return NextResponse.json({
          success: true,
          plan: subscription.plan,
          status: subscription.status,
          synced: false,
        })
      }
    }

    // No Stripe subscription, return current state
    return NextResponse.json({
      success: true,
      plan: subscription?.plan || 'free',
      status: subscription?.status || 'active',
      synced: false,
    })

  } catch (error) {
    console.error('Error in billing refresh:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
