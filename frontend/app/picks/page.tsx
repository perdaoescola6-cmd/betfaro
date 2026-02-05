'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { 
  MessageCircle, 
  BarChart3, 
  CreditCard, 
  User, 
  LogOut, 
  Menu, 
  X, 
  HelpCircle,
  Target,
  RefreshCw,
  TrendingUp,
  Clock,
  Shield,
  Zap,
  Crown,
  ChevronRight,
  AlertCircle,
  Loader2,
  Check
} from 'lucide-react'
import { createClient } from '@/lib/supabase/client'
import AddBetModal from '@/components/AddBetModal'

interface Pick {
  market: string
  confidence: number
  confidence_level: string
  justification: string
}

interface PickResult {
  fixture_id: number
  home_team: string
  away_team: string
  league: string
  league_country: string
  date: string
  date_iso: string
  picks: Pick[]
  games_analyzed: number
}

interface PicksResponse {
  picks: PickResult[]
  meta: {
    range: string
    generated_at: string
    total_fixtures_fetched: number
    priority_fixtures: number
    analyzed_success: number
    analyzed_failed: number
  }
}

interface UserData {
  id: number
  email: string
  subscription?: {
    plan: string
    expires_at: string
    status: string
  }
}

export default function PicksPage() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [user, setUser] = useState<UserData | null>(null)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isElite, setIsElite] = useState(false)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [picks, setPicks] = useState<PickResult[]>([])
  const [meta, setMeta] = useState<PicksResponse['meta'] | null>(null)
  const [activeTab, setActiveTab] = useState<'both' | 'today' | 'tomorrow'>('both')
  
  // Bet tracking state
  const [addedPicks, setAddedPicks] = useState<Set<number>>(new Set())
  const [skippedPicks, setSkippedPicks] = useState<Set<number>>(new Set())
  const [modalOpen, setModalOpen] = useState(false)
  const [selectedPick, setSelectedPick] = useState<{
    pick: PickResult
    market: string
    confidence: number
    valueFlag: boolean
  } | null>(null)
  const [skippingId, setSkippingId] = useState<number | null>(null)

  useEffect(() => {
    checkAuth()
  }, [])

  useEffect(() => {
    if (isElite) {
      fetchPicks(activeTab, false)
      
      // Auto-refresh every 10 minutes
      const interval = setInterval(() => {
        fetchPicks(activeTab, false)
      }, 10 * 60 * 1000)
      
      return () => clearInterval(interval)
    }
  }, [isElite, activeTab])

  const checkAuth = async () => {
    const supabase = createClient()
    
    try {
      const { data: { user: authUser } } = await supabase.auth.getUser()
      
      if (!authUser) {
        setIsAuthenticated(false)
        setLoading(false)
        return
      }

      // Fetch subscription data
      const { data: subscription } = await supabase
        .from('subscriptions')
        .select('*')
        .eq('user_id', authUser.id)
        .maybeSingle()

      const userData = {
        id: authUser.id,
        email: authUser.email || '',
        subscription: subscription ? {
          plan: subscription.plan,
          expires_at: subscription.current_period_end,
          status: subscription.status
        } : undefined
      }

      setUser(userData as any)
      setIsAuthenticated(true)
      
      // Check if Elite
      const isElitePlan = subscription?.plan?.toLowerCase() === 'elite'
      setIsElite(isElitePlan)
    } catch (error) {
      console.error('Auth check failed:', error)
      setIsAuthenticated(false)
    } finally {
      setLoading(false)
    }
  }

  const fetchPicks = async (range: string, forceRefresh: boolean) => {
    if (!isAuthenticated) return

    if (forceRefresh) {
      setRefreshing(true)
    } else {
      setLoading(true)
    }
    setError(null)

    try {
      const response = await fetch(`/api/picks?range=${range}&refresh=${forceRefresh}`, {
        cache: 'no-store'
      })

      if (response.ok) {
        const data: PicksResponse = await response.json()
        
        // Filter only future games (kickoff > now)
        const now = new Date()
        const futurePicks = data.picks.filter(pick => {
          const kickoff = new Date(pick.date_iso)
          return kickoff > now
        })
        
        setPicks(futurePicks)
        setMeta(data.meta)
      } else {
        const errorData = await response.json()
        setError(errorData.detail || 'Erro ao carregar picks')
      }
    } catch (err) {
      setError('Não consegui atualizar os picks agora. Tente novamente em instantes.')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  const handleRefresh = () => {
    fetchPicks(activeTab, true)
  }

  const handleLogout = async () => {
    const supabase = createClient()
    await supabase.auth.signOut()
    setUser(null)
    setIsAuthenticated(false)
    window.location.href = '/'
  }

  const handleEnterPick = (pick: PickResult, market: string, confidence: number) => {
    const valueFlag = confidence >= 70
    setSelectedPick({ pick, market, confidence, valueFlag })
    setModalOpen(true)
  }

  const handleSkipPick = async (pick: PickResult) => {
    setSkippingId(pick.fixture_id)
    try {
      const response = await fetch('/api/bets/skip', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source: 'daily_picks',
          homeTeam: pick.home_team,
          awayTeam: pick.away_team,
          fixtureId: pick.fixture_id.toString(),
          suggestedMarket: pick.picks[0]?.market,
          metadata: { picks: pick.picks, league: pick.league }
        })
      })

      if (response.ok) {
        setSkippedPicks(prev => new Set(Array.from(prev).concat(pick.fixture_id)))
      }
    } catch (error) {
      console.error('Error skipping pick:', error)
    } finally {
      setSkippingId(null)
    }
  }

  const handleBetSuccess = () => {
    if (selectedPick) {
      setAddedPicks(prev => new Set(Array.from(prev).concat(selectedPick.pick.fixture_id)))
    }
    setModalOpen(false)
    setSelectedPick(null)
  }

  const getConfidenceColor = (level: string) => {
    switch (level) {
      case 'ALTA': return 'text-green-400 bg-green-500/20'
      case 'MÉDIA': return 'text-yellow-400 bg-yellow-500/20'
      case 'BAIXA': return 'text-orange-400 bg-orange-500/20'
      default: return 'text-gray-400 bg-gray-500/20'
    }
  }

  const getConfidenceBarColor = (level: string) => {
    switch (level) {
      case 'ALTA': return 'bg-green-500'
      case 'MÉDIA': return 'bg-yellow-500'
      case 'BAIXA': return 'bg-orange-500'
      default: return 'bg-gray-500'
    }
  }

  // Loading state
  if (loading && !refreshing) {
    return (
      <div className="min-h-screen bg-dark-bg flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-blue-400 animate-spin mx-auto mb-4" />
          <p className="text-gray-400">Analisando jogos de hoje e amanhã…</p>
        </div>
      </div>
    )
  }

  // Not authenticated
  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-dark-bg flex items-center justify-center p-4">
        <div className="bg-dark-surface border border-dark-border rounded-2xl p-8 max-w-md w-full text-center">
          <Shield className="w-16 h-16 text-gray-500 mx-auto mb-4" />
          <h1 className="text-2xl font-bold mb-2">Acesso Restrito</h1>
          <p className="text-gray-400 mb-6">Faça login para acessar os Picks Diários</p>
          <Link href="/auth/login" className="btn-primary inline-flex items-center gap-2">
            Fazer Login
            <ChevronRight size={18} />
          </Link>
        </div>
      </div>
    )
  }

  // Not Elite - Paywall
  if (!isElite) {
    return (
      <div className="h-screen bg-dark-bg flex overflow-hidden">
        {/* Sidebar */}
        <Sidebar 
          sidebarOpen={sidebarOpen} 
          setSidebarOpen={setSidebarOpen} 
          user={user} 
          handleLogout={handleLogout}
          activePage="picks"
        />

        {/* Main Content - Paywall */}
        <div className="flex-1 flex flex-col h-screen overflow-hidden">
          <header className="bg-dark-surface border-b border-dark-border p-4 flex-shrink-0">
            <div className="flex items-center space-x-4">
              <button onClick={() => setSidebarOpen(true)} className="lg:hidden text-gray-400 hover:text-white">
                <Menu size={24} />
              </button>
              <h1 className="text-xl font-semibold flex items-center gap-2">
                <Target className="text-yellow-400" size={24} />
                Picks Diários
              </h1>
            </div>
          </header>

          <div className="flex-1 flex items-center justify-center p-6">
            <div className="bg-gradient-to-br from-yellow-500/10 to-orange-500/10 border border-yellow-500/30 rounded-2xl p-8 max-w-lg w-full text-center">
              <div className="w-20 h-20 bg-yellow-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
                <Crown className="w-10 h-10 text-yellow-400" />
              </div>
              <h2 className="text-2xl font-bold mb-3">Recurso Exclusivo Elite</h2>
              <p className="text-gray-400 mb-6">
                Picks Diários é exclusivo do plano Elite. Faça upgrade para receber as melhores oportunidades automaticamente.
              </p>
              
              <div className="bg-dark-bg/50 rounded-xl p-4 mb-6 text-left">
                <h3 className="font-semibold text-yellow-400 mb-3 flex items-center gap-2">
                  <Zap size={18} />
                  O que você ganha:
                </h3>
                <ul className="space-y-2 text-sm text-gray-300">
                  <li className="flex items-center gap-2">
                    <span className="text-green-400">✓</span>
                    Análise automática de 10+ jogos diários
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="text-green-400">✓</span>
                    Picks com alta confiança baseados em dados
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="text-green-400">✓</span>
                    Ligas principais: Brasil, Europa, Arábia Saudita
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="text-green-400">✓</span>
                    Atualização automática todo dia
                  </li>
                </ul>
              </div>

              <div className="flex flex-col sm:flex-row gap-3">
                <Link 
                  href="/plans" 
                  className="flex-1 bg-gradient-to-r from-yellow-500 to-orange-500 hover:from-yellow-400 hover:to-orange-400 text-black font-semibold py-3 px-6 rounded-xl transition-all flex items-center justify-center gap-2"
                >
                  <Crown size={18} />
                  Ver Planos
                </Link>
                <Link 
                  href="/" 
                  className="flex-1 bg-dark-border hover:bg-gray-700 text-white font-medium py-3 px-6 rounded-xl transition-colors flex items-center justify-center gap-2"
                >
                  <MessageCircle size={18} />
                  Voltar ao Chat
                </Link>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // Elite user - Show picks
  return (
    <div className="h-screen bg-dark-bg flex overflow-hidden">
      {/* Sidebar */}
      <Sidebar 
        sidebarOpen={sidebarOpen} 
        setSidebarOpen={setSidebarOpen} 
        user={user} 
        handleLogout={handleLogout}
        activePage="picks"
      />

      {/* Main Content */}
      <div className="flex-1 flex flex-col h-screen overflow-hidden">
        {/* Header */}
        <header className="bg-dark-surface border-b border-dark-border p-4 flex-shrink-0">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <button onClick={() => setSidebarOpen(true)} className="lg:hidden text-gray-400 hover:text-white">
                <Menu size={24} />
              </button>
              <h1 className="text-xl font-semibold flex items-center gap-2">
                <Target className="text-yellow-400" size={24} />
                Picks Diários
              </h1>
              <span className="text-xs bg-yellow-500/20 text-yellow-400 px-2 py-1 rounded-full font-medium">ELITE</span>
            </div>
            
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg text-sm font-medium transition-colors"
            >
              <RefreshCw size={16} className={refreshing ? 'animate-spin' : ''} />
              {refreshing ? 'Atualizando...' : 'Atualizar'}
            </button>
          </div>

          {/* Tabs */}
          <div className="flex gap-2 mt-4">
            {(['both', 'today', 'tomorrow'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  activeTab === tab 
                    ? 'bg-blue-600 text-white' 
                    : 'bg-dark-border text-gray-400 hover:text-white'
                }`}
              >
                {tab === 'both' ? 'Hoje + Amanhã' : tab === 'today' ? 'Hoje' : 'Amanhã'}
              </button>
            ))}
          </div>
        </header>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 md:p-6">
          {/* Meta info */}
          {meta && (
            <div className="mb-4 text-xs text-gray-500 flex items-center gap-4">
              <span className="flex items-center gap-1">
                <Clock size={12} />
                Atualizado: {new Date(meta.generated_at).toLocaleString('pt-BR', { timeZone: 'America/Sao_Paulo' })}
              </span>
              <span>{meta.analyzed_success} jogos analisados</span>
            </div>
          )}

          {/* Error state */}
          {error && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 mb-6 flex items-center gap-3">
              <AlertCircle className="text-red-400 flex-shrink-0" size={20} />
              <p className="text-red-400">{error}</p>
            </div>
          )}

          {/* Empty state */}
          {!error && picks.length === 0 && !loading && (
            <div className="text-center py-12">
              <Target className="w-16 h-16 text-gray-600 mx-auto mb-4" />
              <h3 className="text-xl font-semibold mb-2">Sem jogos principais</h3>
              <p className="text-gray-400">
                Sem jogos principais para o período selecionado.
              </p>
            </div>
          )}

          {/* Picks Grid */}
          <div className="grid gap-4 md:grid-cols-2">
            {picks.map((pick) => (
              <div 
                key={pick.fixture_id}
                className="bg-dark-surface border border-dark-border rounded-xl p-4 hover:border-blue-500/30 transition-colors"
              >
                {/* Match Header */}
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h3 className="font-semibold text-white">
                      {pick.home_team} <span className="text-gray-500">vs</span> {pick.away_team}
                    </h3>
                    <p className="text-xs text-gray-500 mt-1">
                      {pick.league} • {pick.date}
                    </p>
                  </div>
                  {pick.picks.some(p => p.confidence >= 70) && (
                    <span className="flex items-center gap-1 text-xs bg-green-500/20 text-green-400 px-2 py-1 rounded-full">
                      <TrendingUp size={12} />
                      Value
                    </span>
                  )}
                </div>

                {/* Picks */}
                <div className="space-y-3">
                  {pick.picks.map((p, idx) => (
                    <div key={idx} className="bg-dark-bg rounded-lg p-3">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-medium text-blue-400">{p.market}</span>
                        <span className={`text-xs px-2 py-0.5 rounded ${getConfidenceColor(p.confidence_level)}`}>
                          {p.confidence_level}
                        </span>
                      </div>
                      
                      {/* Confidence bar */}
                      <div className="flex items-center gap-2 mb-2">
                        <div className="flex-1 h-2 bg-dark-border rounded-full overflow-hidden">
                          <div 
                            className={`h-full ${getConfidenceBarColor(p.confidence_level)} transition-all`}
                            style={{ width: `${p.confidence}%` }}
                          />
                        </div>
                        <span className="text-xs text-gray-400 w-12 text-right">{p.confidence}%</span>
                      </div>
                      
                      {/* Justification */}
                      <p className="text-xs text-gray-400">{p.justification}</p>
                    </div>
                  ))}
                </div>

                {/* Footer with action buttons */}
                <div className="mt-3 pt-3 border-t border-dark-border">
                  <p className="text-xs text-gray-600 mb-3">
                    Baseado em {pick.games_analyzed} jogos analisados
                  </p>
                  
                  {/* Action buttons or status */}
                  {addedPicks.has(pick.fixture_id) ? (
                    <div className="flex items-center gap-2 text-green-400 text-sm">
                      <Check size={16} />
                      <span>Adicionada ao Dashboard ✅</span>
                    </div>
                  ) : skippedPicks.has(pick.fixture_id) ? (
                    <div className="flex items-center gap-2 text-gray-400 text-sm">
                      <X size={16} />
                      <span>Pulado 👍</span>
                    </div>
                  ) : (
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleEnterPick(pick, pick.picks[0]?.market || '', pick.picks[0]?.confidence || 0)}
                        className="flex-1 flex items-center justify-center gap-2 bg-green-600 hover:bg-green-700 text-white text-sm font-medium py-2 px-3 rounded-lg transition-colors"
                      >
                        <Check size={14} />
                        Entrar
                      </button>
                      <button
                        onClick={() => handleSkipPick(pick)}
                        disabled={skippingId === pick.fixture_id}
                        className="flex-1 flex items-center justify-center gap-2 bg-red-600/20 hover:bg-red-600/30 text-red-400 text-sm font-medium py-2 px-3 rounded-lg transition-colors disabled:opacity-50"
                      >
                        {skippingId === pick.fixture_id ? (
                          <Loader2 className="animate-spin" size={14} />
                        ) : (
                          <X size={14} />
                        )}
                        Pular
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Refreshing overlay */}
          {refreshing && (
            <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
              <div className="bg-dark-surface border border-dark-border rounded-xl p-6 text-center">
                <Loader2 className="w-8 h-8 text-blue-400 animate-spin mx-auto mb-3" />
                <p className="text-gray-300">Analisando jogos de hoje e amanhã…</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Add Bet Modal */}
      {selectedPick && (
        <AddBetModal
          isOpen={modalOpen}
          onClose={() => {
            setModalOpen(false)
            setSelectedPick(null)
          }}
          onSuccess={handleBetSuccess}
          prefill={{
            homeTeam: selectedPick.pick.home_team,
            awayTeam: selectedPick.pick.away_team,
            source: 'daily_picks',
            fixtureId: selectedPick.pick.fixture_id.toString(),
            league: selectedPick.pick.league,
            kickoffAt: selectedPick.pick.date_iso,
            suggestedMarket: selectedPick.market,
            valueFlag: selectedPick.valueFlag,
            botReco: {
              market: selectedPick.market,
              prob: selectedPick.confidence,
              confidence: selectedPick.confidence >= 70 ? 'ALTA' : selectedPick.confidence >= 50 ? 'MÉDIA' : 'BAIXA'
            }
          }}
        />
      )}
    </div>
  )
}

// Sidebar Component
function Sidebar({ 
  sidebarOpen, 
  setSidebarOpen, 
  user, 
  handleLogout,
  activePage 
}: { 
  sidebarOpen: boolean
  setSidebarOpen: (open: boolean) => void
  user: UserData | null
  handleLogout: () => void
  activePage: string
}) {
  return (
    <div className={`${sidebarOpen ? 'translate-x-0' : '-translate-x-full'} fixed inset-y-0 left-0 z-50 w-64 bg-dark-surface border-r border-dark-border transition-transform duration-300 lg:translate-x-0 lg:static lg:inset-0`}>
      <div className="flex items-center justify-between p-6 border-b border-dark-border">
        <h2 className="text-xl font-bold text-accent-blue">BetFaro</h2>
        <button onClick={() => setSidebarOpen(false)} className="lg:hidden text-gray-400 hover:text-white">
          <X size={24} />
        </button>
      </div>
      
      <nav className="p-4 space-y-2">
        <Link href="/" className={`flex items-center space-x-3 p-3 rounded-lg ${activePage === 'chat' ? 'bg-dark-border' : 'hover:bg-dark-border'} transition-colors`}>
          <MessageCircle size={20} />
          <span>Chat</span>
        </Link>
        <Link href="/picks" className={`flex items-center space-x-3 p-3 rounded-lg ${activePage === 'picks' ? 'bg-dark-border' : 'hover:bg-dark-border'} transition-colors`}>
          <Target size={20} className="text-yellow-400" />
          <span>Picks Diários</span>
          <span className="ml-auto text-[10px] bg-yellow-500/20 text-yellow-400 px-1.5 py-0.5 rounded font-medium">ELITE</span>
        </Link>
        <Link href="/dashboard" className={`flex items-center space-x-3 p-3 rounded-lg ${activePage === 'dashboard' ? 'bg-dark-border' : 'hover:bg-dark-border'} transition-colors`}>
          <BarChart3 size={20} />
          <span>Dashboard</span>
        </Link>
        <Link href="/plans" className={`flex items-center space-x-3 p-3 rounded-lg ${activePage === 'plans' ? 'bg-dark-border' : 'hover:bg-dark-border'} transition-colors`}>
          <CreditCard size={20} />
          <span>Planos</span>
        </Link>
        <Link href="/account" className={`flex items-center space-x-3 p-3 rounded-lg ${activePage === 'account' ? 'bg-dark-border' : 'hover:bg-dark-border'} transition-colors`}>
          <User size={20} />
          <span>Conta</span>
        </Link>
        <Link href="/ajuda" className={`flex items-center space-x-3 p-3 rounded-lg ${activePage === 'ajuda' ? 'bg-dark-border' : 'hover:bg-dark-border'} transition-colors`}>
          <HelpCircle size={20} />
          <span>Ajuda</span>
        </Link>
      </nav>
      
      <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-dark-border">
        <div className="mb-4">
          <p className="text-sm text-gray-400">{user?.email}</p>
          {user?.subscription && (
            <p className="text-xs text-accent-green">
              Plano {user.subscription.plan} - {user.subscription.status}
            </p>
          )}
        </div>
        <button
          onClick={handleLogout}
          className="flex items-center space-x-3 p-3 rounded-lg hover:bg-dark-border transition-colors w-full"
        >
          <LogOut size={20} />
          <span>Sair</span>
        </button>
      </div>
    </div>
  )
}
