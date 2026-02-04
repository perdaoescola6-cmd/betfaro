import Stripe from 'stripe'

let stripeInstance: Stripe | null = null

export function getStripe(): Stripe {
  if (!stripeInstance) {
    if (!process.env.STRIPE_SECRET_KEY) {
      throw new Error('STRIPE_SECRET_KEY is not set')
    }
    stripeInstance = new Stripe(process.env.STRIPE_SECRET_KEY, {
      apiVersion: '2026-01-28.clover',
      typescript: true,
    })
  }
  return stripeInstance
}

// Legacy export for compatibility
export const stripe = {
  get customers() { return getStripe().customers },
  get checkout() { return getStripe().checkout },
  get subscriptions() { return getStripe().subscriptions },
  get webhooks() { return getStripe().webhooks },
}

// Get price ID for a plan
export function getPriceIdForPlan(plan: 'pro' | 'elite'): string {
  const prices = {
    pro: process.env.STRIPE_PRICE_PRO || '',
    elite: process.env.STRIPE_PRICE_ELITE || '',
  }
  return prices[plan]
}

// Get plan from price ID
export function getPlanFromPriceId(priceId: string): 'pro' | 'elite' | null {
  if (priceId === process.env.STRIPE_PRICE_PRO) return 'pro'
  if (priceId === process.env.STRIPE_PRICE_ELITE) return 'elite'
  return null
}
