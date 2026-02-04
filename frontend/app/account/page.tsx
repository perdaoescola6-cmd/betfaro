'use client'

import { useEffect, useState, useCallback, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { 
  User,
  Mail,
  Calendar,
  Shield,
  CreditCard,
  LogOut,
  CheckCircle,
  Loader2
} from 'lucide-react'
import { createClient } from '@/lib/supabase/client'
import AppShell from '@/components/AppShell'

function AccountContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [user, setUser] = useState<any>(null)
  const [isPolling, setIsPolling] = useState(false)
  const [showSuccess, setShowSuccess] = useState(false)
  const supabase = createClient()

  const fetchUserData = useCallback(async () => {
    const { data: { user: authUser } } = await supabase.auth.getUser()
    
    if (!authUser) {
      router.push('/auth/login')
      return null
    }

    // Fetch subscription data
    const { data: subscription } = await supabase
      .from('subscriptions')
      .select('*')
      .eq('user_id', authUser.id)
      .maybeSingle()

    const userData = {
      id: authUser.id,
      email: authUser.email,
      created_at: authUser.created_at,
      subscription: subscription ? {
        plan: subscription.plan,
        expires_at: subscription.current_period_end,
        status: subscription.status
      } : undefined
    }
    
    setUser(userData)
    return userData
  }, [supabase, router])

  useEffect(() => {
    fetchUserData()
  }, [fetchUserData])

  // Handle checkout success - poll for subscription update
  useEffect(() => {
    const success = searchParams.get('success')
    const expectedPlan = searchParams.get('plan')
    
    if (success === 'true' && expectedPlan) {
      setIsPolling(true)
      setShowSuccess(true)
      
      let attempts = 0
      const maxAttempts = 20 // 40 seconds total
      
      const syncAndCheck = async () => {
        attempts++
        
        try {
          // Call refresh to sync with Stripe
          const refreshResponse = await fetch('/api/billing/refresh', { 
            method: 'POST',
            cache: 'no-store',
          })
          const refreshData = await refreshResponse.json()
          
          // If refresh succeeded and plan matches, we're done
          if (refreshData.success && refreshData.plan === expectedPlan) {
            await fetchUserData() // Refresh UI
            setIsPolling(false)
            router.replace('/account')
            return true
          }
        } catch (error) {
          console.error('[SYNC] Error:', error)
        }
        
        // Also check database directly
        const userData = await fetchUserData()
        if (userData?.subscription?.plan === expectedPlan) {
          setIsPolling(false)
          router.replace('/account')
          return true
        }
        
        return false
      }
      
      // Initial sync
      syncAndCheck()
      
      const pollInterval = setInterval(async () => {
        const done = await syncAndCheck()
        if (done || attempts >= maxAttempts) {
          clearInterval(pollInterval)
          if (attempts >= maxAttempts) {
            setIsPolling(false)
            router.replace('/account')
          }
        }
      }, 2000)
      
      return () => clearInterval(pollInterval)
    }
  }, [searchParams, fetchUserData, router])

  const handleLogout = async () => {
    const supabase = createClient()
    await supabase.auth.signOut()
    router.push('/auth/login')
  }

  if (!user) {
    return (
      <AppShell title="Minha Conta">
        <div className="flex items-center justify-center h-full">
          <Loader2 className="animate-spin text-caramelo" size={32} />
        </div>
      </AppShell>
    )
  }

  return (
    <AppShell title="Minha Conta">
      <div className="max-w-3xl mx-auto p-4 sm:p-6">
        {/* Success Banner after checkout */}
        {showSuccess && (
          <div className="bg-green-500/10 border border-green-500/30 rounded-xl p-4 mb-6 flex items-center">
            {isPolling ? (
              <>
                <Loader2 className="animate-spin text-green-400 mr-3" size={20} />
                <div>
                  <p className="text-green-400 font-medium">Ativando sua assinatura...</p>
                  <p className="text-green-400/70 text-sm">Aguarde enquanto processamos seu pagamento.</p>
                </div>
              </>
            ) : (
              <>
                <CheckCircle className="text-green-400 mr-3" size={20} />
                <div>
                  <p className="text-green-400 font-medium">Assinatura ativada com sucesso!</p>
                  <p className="text-green-400/70 text-sm">Aproveite todos os benefícios do seu novo plano.</p>
                </div>
              </>
            )}
          </div>
        )}

        {/* Profile Section */}
        <div className="bg-dark-surface border border-dark-border rounded-xl p-6 mb-6">
          <h2 className="text-lg font-semibold mb-6 flex items-center">
            <User className="mr-2 text-blue-400" size={20} />
            Informações do Perfil
          </h2>
          
          <div className="space-y-4">
            <div className="flex items-center justify-between py-3 border-b border-dark-border">
              <div className="flex items-center">
                <Mail className="text-gray-400 mr-3" size={18} />
                <span className="text-gray-400">Email</span>
              </div>
              <span className="font-medium">{user.email}</span>
            </div>

            <div className="flex items-center justify-between py-3 border-b border-dark-border">
              <div className="flex items-center">
                <Calendar className="text-gray-400 mr-3" size={18} />
                <span className="text-gray-400">Membro desde</span>
              </div>
              <span className="font-medium">
                {new Date(user.created_at || Date.now()).toLocaleDateString('pt-BR')}
              </span>
            </div>

            <div className="flex items-center justify-between py-3">
              <div className="flex items-center">
                <Shield className="text-gray-400 mr-3" size={18} />
                <span className="text-gray-400">Status</span>
              </div>
              <span className="text-green-400 font-medium">Ativo</span>
            </div>
          </div>
        </div>

        {/* Subscription Section */}
        <div className="bg-dark-surface border border-dark-border rounded-xl p-6 mb-6">
          <h2 className="text-lg font-semibold mb-6 flex items-center">
            <CreditCard className="mr-2 text-yellow-400" size={20} />
            Assinatura
          </h2>
          
          <div className="space-y-4">
            <div className="flex items-center justify-between py-3 border-b border-dark-border">
              <span className="text-gray-400">Plano atual</span>
              <span className="font-medium text-yellow-400">
                {user.subscription?.plan || 'Free'}
              </span>
            </div>

            <div className="flex items-center justify-between py-3 border-b border-dark-border">
              <span className="text-gray-400">Status</span>
              <span className={`font-medium ${
                user.subscription?.status === 'active' ? 'text-green-400' : 'text-gray-400'
              }`}>
                {user.subscription?.status === 'active' ? 'Ativo' : 'Inativo'}
              </span>
            </div>

            {user.subscription?.expires_at && (
              <div className="flex items-center justify-between py-3">
                <span className="text-gray-400">Expira em</span>
                <span className="font-medium">
                  {new Date(user.subscription.expires_at).toLocaleDateString('pt-BR')}
                </span>
              </div>
            )}
          </div>

          <div className="mt-6">
            <Link href="/plans" className="btn-primary w-full text-center block">
              Gerenciar Plano
            </Link>
          </div>
        </div>

        {/* Danger Zone */}
        <div className="bg-dark-surface border border-red-900/50 rounded-xl p-6">
          <h2 className="text-lg font-semibold mb-4 text-red-400">Zona de Perigo</h2>
          
          <button
            onClick={handleLogout}
            className="flex items-center justify-center w-full py-3 bg-red-600/20 hover:bg-red-600/30 text-red-400 rounded-lg transition-colors"
          >
            <LogOut className="mr-2" size={18} />
            Sair da Conta
          </button>
        </div>
      </div>
    </AppShell>
  )
}

// Wrap with Suspense to handle useSearchParams
export default function AccountPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-dark-bg flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    }>
      <AccountContent />
    </Suspense>
  )
}
