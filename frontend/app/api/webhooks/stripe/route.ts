import { NextRequest, NextResponse } from 'next/server'
import { headers } from 'next/headers'
import Stripe from 'stripe'
import { createAdminClient } from '@/lib/supabase/admin'
import { getPlanFromPriceId } from '@/lib/stripe'

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!)

const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET!

export async function POST(request: NextRequest) {
  const body = await request.text()
  const headersList = await headers()
  const signature = headersList.get('stripe-signature')!

  let event: Stripe.Event

  try {
    event = stripe.webhooks.constructEvent(body, signature, webhookSecret)
  } catch (err: any) {
    console.error('Webhook signature verification failed:', err.message)
    return NextResponse.json(
      { error: 'Webhook signature verification failed' },
      { status: 400 }
    )
  }

  const supabase = createAdminClient()

  try {
    switch (event.type) {
      case 'checkout.session.completed': {
        const session = event.data.object as any
        const userId = session.metadata?.user_id
        const subscriptionId = session.subscription as string

        if (userId && subscriptionId) {
          const subscription = await stripe.subscriptions.retrieve(subscriptionId) as any
          const priceId = subscription.items.data[0]?.price.id
          const plan = getPlanFromPriceId(priceId) || 'pro'
          const periodEnd = subscription.current_period_end 
            ? new Date(subscription.current_period_end * 1000).toISOString()
            : new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString()

          await supabase
            .from('subscriptions')
            .upsert({
              user_id: userId,
              plan: plan,
              status: subscription.status || 'active',
              provider: 'stripe',
              stripe_customer_id: session.customer as string,
              stripe_subscription_id: subscriptionId,
              stripe_price_id: priceId,
              current_period_end: periodEnd,
              updated_at: new Date().toISOString(),
            })

          console.log(`✅ Checkout completed: User ${userId} -> Plan ${plan}`)
        } else {
          console.log(`⚠️ Checkout session missing userId (${userId}) or subscriptionId (${subscriptionId})`)
        }
        break
      }

      case 'customer.subscription.created':
      case 'customer.subscription.updated': {
        const subscription = event.data.object as any
        let userId = subscription.metadata?.user_id
        const priceId = subscription.items.data[0]?.price.id
        const plan = getPlanFromPriceId(priceId) || 'pro'
        const customerId = subscription.customer as string

        // If no user_id in metadata, try to find by customer_id
        if (!userId && customerId) {
          const { data: existingSub } = await supabase
            .from('subscriptions')
            .select('user_id')
            .eq('stripe_customer_id', customerId)
            .single()
          
          userId = existingSub?.user_id
        }

        if (userId) {
          const periodEnd = subscription.current_period_end 
            ? new Date(subscription.current_period_end * 1000).toISOString()
            : null

          await supabase
            .from('subscriptions')
            .upsert({
              user_id: userId,
              plan: plan,
              status: subscription.status,
              provider: 'stripe',
              stripe_customer_id: customerId,
              stripe_subscription_id: subscription.id,
              stripe_price_id: priceId,
              current_period_end: periodEnd,
              updated_at: new Date().toISOString(),
            })

          console.log(`✅ Subscription ${event.type}: User ${userId} -> Plan ${plan}, Status ${subscription.status}`)
        }
        break
      }

      case 'customer.subscription.deleted': {
        const subscription = event.data.object as any
        const userId = subscription.metadata?.user_id

        if (userId) {
          await supabase
            .from('subscriptions')
            .update({
              plan: 'free',
              status: 'canceled',
              current_period_end: new Date().toISOString(),
              updated_at: new Date().toISOString(),
            })
            .eq('user_id', userId)

          console.log(`✅ Subscription canceled: User ${userId} -> Free`)
        }
        break
      }

      case 'invoice.paid': {
        const invoice = event.data.object as any
        const subscriptionId = invoice.subscription as string

        if (subscriptionId) {
          const subscription = await stripe.subscriptions.retrieve(subscriptionId) as any
          const userId = subscription.metadata?.user_id

          if (userId) {
            await supabase
              .from('subscriptions')
              .update({
                status: 'active',
                current_period_end: new Date(subscription.current_period_end * 1000).toISOString(),
                updated_at: new Date().toISOString(),
              })
              .eq('user_id', userId)

            console.log(`✅ Invoice paid: User ${userId}`)
          }
        }
        break
      }

      case 'invoice.payment_failed': {
        const invoice = event.data.object as any
        const subscriptionId = invoice.subscription as string

        if (subscriptionId) {
          const subscription = await stripe.subscriptions.retrieve(subscriptionId) as any
          const userId = subscription.metadata?.user_id

          if (userId) {
            await supabase
              .from('subscriptions')
              .update({
                status: 'past_due',
                updated_at: new Date().toISOString(),
              })
              .eq('user_id', userId)

            console.log(`⚠️ Payment failed: User ${userId}`)
          }
        }
        break
      }

      default:
        console.log(`Unhandled event type: ${event.type}`)
    }

    return NextResponse.json({ received: true })
  } catch (error) {
    console.error('Webhook processing error:', error)
    return NextResponse.json(
      { error: 'Webhook processing failed' },
      { status: 500 }
    )
  }
}
