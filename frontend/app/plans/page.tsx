'use client'

import { Suspense, useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { 
  Check,
  Zap,
  Crown,
  Star,
  Loader2,
  X
} from 'lucide-react'
import { createClient } from '@/lib/supabase/client'
import AppShell from '@/components/AppShell'

const plans = [
  {
    id: 'free',
    name: 'Free',
    price: 'R$0',
    period: '',
    headline: 'Para começar',
    description: 'Ideal para testar a plataforma',
    features: [
      '5 análises por dia',
      'Estatísticas básicas',
      'Suporte por email'
    ],
    icon: Zap,
    color: 'gray',
    gradient: 'from-gray-500 to-gray-600',
    cta: 'Começar grátis'
  },
  {
    id: 'pro',
    name: 'Pro',
    price: 'R$49',
    period: '/mês',
    headline: 'Para apostadores que querem vantagem real',
    description: 'Mais dados. Mais vantagem.',
    features: [
      '25 análises por dia',
      'Odds de valor',
      'Histórico de análises',
      'Estatísticas avançadas',
      'Suporte prioritário'
    ],
    icon: Star,
    color: 'blue',
    gradient: 'from-caramelo to-caramelo-accent',
    popular: true,
    cta: 'Assinar Pro'
  },
  {
    id: 'elite',
    name: 'Elite',
    price: 'R$99',
    period: '/mês',
    headline: 'Para quem aposta como um profissional',
    description: 'Máximo poder de análise',
    features: [
      '100 análises por dia',
      'Picks automáticos diários',
      'Alertas personalizados',
      'Dashboard exclusivo',
      'Suporte 24/7 prioritário'
    ],
    icon: Crown,
    color: 'yellow',
    gradient: 'from-yellow-500 to-orange-500',
    cta: 'Assinar Elite'
  }
]

function PlansContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [user, setUser] = useState<any>(null)
  const [processingPlan, setProcessingPlan] = useState<string | null>(null)
  const [showSuccessModal, setShowSuccessModal] = useState(false)
  const [showCanceledModal, setShowCanceledModal] = useState(false)
  const [selectedPlanName, setSelectedPlanName] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const supabase = createClient()

  useEffect(() => {
    const checkAuth = async () => {
      const { data: { user: authUser } } = await supabase.auth.getUser()
      
      if (!authUser) {
        router.push('/auth/login')
        return
      }

      // Get subscription data
      const { data: subscription } = await supabase
        .from('subscriptions')
        .select('plan, status, current_period_end')
        .eq('user_id', authUser.id)
        .maybeSingle()

      setUser({
        id: authUser.id,
        email: authUser.email,
        subscription: subscription
      })
      setIsLoading(false)
    }

    checkAuth()

    // Check URL params for success/canceled
    if (searchParams.get('success') === 'true') {
      setSelectedPlanName(searchParams.get('plan') || '')
      setShowSuccessModal(true)
    }
    if (searchParams.get('canceled') === 'true') {
      setShowCanceledModal(true)
    }
  }, [router, searchParams, supabase])

  const handleSelectPlan = async (planId: string, planName: string) => {
    if (planId === 'free') return
    
    setProcessingPlan(planId)
    setSelectedPlanName(planName)
    setError('')
    
    try {
      const response = await fetch('/api/billing/checkout', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ plan: planId }),
      })

      const data = await response.json()

      if (response.ok && data.url) {
        // Redirect to Stripe Checkout
        window.location.href = data.url
      } else {
        setError(data.error || 'Erro ao processar pagamento')
        setProcessingPlan(null)
      }
    } catch (err) {
      setError('Erro de conexão. Tente novamente.')
      setProcessingPlan(null)
    }
  }

  if (isLoading) {
    return (
      <AppShell title="Planos">
        <div className="flex items-center justify-center h-full">
          <Loader2 className="w-8 h-8 text-caramelo animate-spin" />
        </div>
      </AppShell>
    )
  }

  return (
    <AppShell title="Planos">
      <div className="max-w-7xl mx-auto p-4 sm:p-6">
        {/* Hero Section */}
        <div className="text-center mb-12">
          <h2 className="text-4xl font-bold mb-4 bg-gradient-to-r from-blue-400 to-green-400 bg-clip-text text-transparent">
            Escolha o plano ideal para sua estratégia
          </h2>
          <p className="text-xl text-gray-400 max-w-2xl mx-auto">
            Mais dados. Mais vantagem. Mais lucro.
          </p>
        </div>

        {/* Error Message */}
        {error && (
          <div className="max-w-md mx-auto mb-8 p-4 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 text-center">
            {error}
          </div>
        )}

        {/* Plans Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto">
          {plans.map((plan) => {
            const Icon = plan.icon
            const isCurrentPlan = user?.subscription?.plan?.toLowerCase() === plan.id
            const isProcessing = processingPlan === plan.id
            
            return (
              <div 
                key={plan.name}
                className={`relative bg-dark-surface border rounded-2xl p-8 transition-all duration-300 hover:scale-[1.02] ${
                  plan.popular 
                    ? 'border-caramelo ring-2 ring-caramelo/20 shadow-lg shadow-caramelo/10' 
                    : 'border-dark-border hover:border-gray-600'
                }`}
              >
                {plan.popular && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                    <span className="bg-gradient-to-r from-caramelo to-caramelo-accent text-white text-xs font-bold px-4 py-1.5 rounded-full shadow-lg">
                      🔥 MAIS POPULAR
                    </span>
                  </div>
                )}

                <div className="text-center mb-6">
                  <div className={`inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br ${plan.gradient} mb-4 shadow-lg`}>
                    <Icon className="text-white" size={28} />
                  </div>
                  <h3 className="text-2xl font-bold">{plan.name}</h3>
                  <p className="text-sm text-gray-500 font-medium">{plan.headline}</p>
                  <p className="text-gray-400 text-sm mt-1">{plan.description}</p>
                </div>

                <div className="text-center mb-6">
                  <span className="text-5xl font-bold">{plan.price}</span>
                  <span className="text-gray-400 text-lg">{plan.period}</span>
                </div>

                <ul className="space-y-3 mb-8">
                  {plan.features.map((feature, index) => (
                    <li key={index} className="flex items-center text-sm">
                      <div className="w-5 h-5 rounded-full bg-green-500/20 flex items-center justify-center mr-3 flex-shrink-0">
                        <Check className="text-green-400" size={12} />
                      </div>
                      <span className="text-gray-300">{feature}</span>
                    </li>
                  ))}
                </ul>

                <button
                  onClick={() => handleSelectPlan(plan.id, plan.name)}
                  disabled={isCurrentPlan || isProcessing || plan.id === 'free'}
                  className={`w-full py-4 rounded-xl font-semibold transition-all duration-300 flex items-center justify-center space-x-2 ${
                    isCurrentPlan
                      ? 'bg-green-600 text-white cursor-default'
                      : plan.id === 'free'
                        ? 'bg-dark-border text-gray-500 cursor-default'
                        : plan.popular
                          ? 'bg-gradient-to-r from-caramelo to-caramelo-accent hover:from-caramelo-hover hover:to-caramelo text-white shadow-lg shadow-caramelo/25 hover:shadow-caramelo/40'
                          : 'bg-dark-border hover:bg-gray-700 text-white'
                  }`}
                >
                  {isProcessing ? (
                    <>
                      <Loader2 size={18} className="animate-spin" />
                      <span>Redirecionando...</span>
                    </>
                  ) : isCurrentPlan ? (
                    <>
                      <Check size={18} />
                      <span>Plano Atual</span>
                    </>
                  ) : (
                    <span>{plan.cta}</span>
                  )}
                </button>
              </div>
            )
          })}
        </div>

        {/* Trust Badges */}
        <div className="mt-12 text-center">
          <div className="flex items-center justify-center gap-8 text-gray-500 text-sm">
            <div className="flex items-center gap-2">
              <span>🔒</span>
              <span>Pagamento seguro via Stripe</span>
            </div>
            <div className="flex items-center gap-2">
              <span>💳</span>
              <span>Cancele quando quiser</span>
            </div>
            <div className="flex items-center gap-2">
              <span>⚡</span>
              <span>Ativação instantânea</span>
            </div>
          </div>
        </div>

        {/* FAQ */}
        <div className="mt-16 max-w-2xl mx-auto">
          <h3 className="text-xl font-bold text-center mb-8">Perguntas Frequentes</h3>
          <div className="space-y-4">
            <div className="bg-dark-surface border border-dark-border rounded-xl p-5">
              <h4 className="font-semibold mb-2">Posso cancelar a qualquer momento?</h4>
              <p className="text-gray-400 text-sm">Sim! Você pode cancelar sua assinatura a qualquer momento. O acesso continua até o fim do período pago.</p>
            </div>
            <div className="bg-dark-surface border border-dark-border rounded-xl p-5">
              <h4 className="font-semibold mb-2">Como funciona a cobrança?</h4>
              <p className="text-gray-400 text-sm">A cobrança é mensal e automática. Você será notificado antes de cada renovação.</p>
            </div>
            <div className="bg-dark-surface border border-dark-border rounded-xl p-5">
              <h4 className="font-semibold mb-2">Posso fazer upgrade ou downgrade?</h4>
              <p className="text-gray-400 text-sm">Sim! Você pode mudar de plano a qualquer momento. O valor será ajustado proporcionalmente.</p>
            </div>
          </div>
        </div>

        {/* Contact */}
        <div className="mt-12 text-center">
          <p className="text-gray-400">
            Dúvidas? Entre em contato: <span className="text-caramelo">suporte@betfaro.com</span>
          </p>
        </div>
      </div>

      {/* Success Modal */}
      {showSuccessModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-dark-surface border border-dark-border rounded-2xl p-8 max-w-sm w-full shadow-2xl text-center">
            <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
              <Check className="text-green-400" size={32} />
            </div>
            <h3 className="text-xl font-bold mb-2">🎉 Assinatura ativada com sucesso!</h3>
            <p className="text-gray-400 mb-6">
              Seu plano {selectedPlanName} já está ativo. Aproveite todos os recursos!
            </p>
            <button
              onClick={() => {
                setShowSuccessModal(false)
                router.push('/')
              }}
              className="w-full py-3 rounded-xl bg-gradient-to-r from-green-500 to-green-600 hover:from-green-600 hover:to-green-700 text-white font-semibold transition-all"
            >
              Começar a usar
            </button>
          </div>
        </div>
      )}

      {/* Canceled Modal */}
      {showCanceledModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-dark-surface border border-dark-border rounded-2xl p-8 max-w-sm w-full shadow-2xl text-center">
            <div className="w-16 h-16 bg-yellow-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
              <X className="text-yellow-400" size={32} />
            </div>
            <h3 className="text-xl font-bold mb-2">Pagamento cancelado</h3>
            <p className="text-gray-400 mb-6">
              Você cancelou o processo de pagamento. Pode tentar novamente quando quiser.
            </p>
            <button
              onClick={() => setShowCanceledModal(false)}
              className="w-full py-3 rounded-xl bg-dark-border hover:bg-gray-700 text-white font-semibold transition-all"
            >
              Fechar
            </button>
          </div>
        </div>
      )}
    </AppShell>
  )
}

export default function PlansPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-dark-bg">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
          <p className="text-gray-400">Carregando planos...</p>
        </div>
      </div>
    }>
      <PlansContent />
    </Suspense>
  )
}
