'use client'

import { useEffect, useState, useCallback } from 'react'
import Link from 'next/link'
import { 
  BarChart3, 
  TrendingUp, 
  Target, 
  Flame,
  Plus,
  X,
  Check,
  AlertCircle,
  Diamond,
  Edit3,
  Loader2,
  MessageCircle,
  Zap,
  DollarSign
} from 'lucide-react'
import { createClient } from '@/lib/supabase/client'
import AddBetModal from '@/components/AddBetModal'
import AppShell from '@/components/AppShell'
import { getMarketLabel } from '@/lib/markets'

interface Bet {
  id: string
  home_team: string
  away_team: string
  market: string
  odds: number
  stake?: number
  note?: string
  status: 'pending' | 'won' | 'lost' | 'void' | 'cashout'
  value_flag: boolean
  source: 'chat' | 'daily_picks' | 'manual'
  league?: string
  created_at: string
  bot_reco?: any
}

interface Stats {
  total: number
  pending: number
  won: number
  lost: number
  winrate: number
  streak: number
  valueBets: number
  roi: number
  totalStake: number
  totalProfitLoss: number
}


export default function DashboardPage() {
  const supabase = createClient()
  const [userId, setUserId] = useState<string | null>(null)
  const [bets, setBets] = useState<Bet[]>([])
  const [stats, setStats] = useState<Stats>({ total: 0, pending: 0, won: 0, lost: 0, winrate: 0, streak: 0, valueBets: 0, roi: 0, totalStake: 0, totalProfitLoss: 0 })
  const [loading, setLoading] = useState(true)
  const [showAddModal, setShowAddModal] = useState(false)
  const [showResultModal, setShowResultModal] = useState<string | null>(null)

  const fetchBets = useCallback(async () => {
    try {
      const response = await fetch('/api/bets', { cache: 'no-store' })
      if (response.ok) {
        const data = await response.json()
        setBets(data.bets || [])
        setStats(data.stats || { total: 0, pending: 0, won: 0, lost: 0, winrate: 0, streak: 0, valueBets: 0 })
      }
    } catch (error) {
      console.error('Error fetching bets:', error)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    const init = async () => {
      const { data: { user: authUser } } = await supabase.auth.getUser()
      if (authUser) {
        setUserId(authUser.id)
        fetchBets()
      }
    }
    init()
  }, [supabase, fetchBets])

  // Supabase Realtime subscription for bets
  useEffect(() => {
    if (!userId) return

    const channel = supabase
      .channel('bets-changes')
      .on('postgres_changes', {
        event: '*',
        schema: 'public',
        table: 'bets',
        filter: `user_id=eq.${userId}`
      }, () => {
        fetchBets()
      })
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [userId, supabase, fetchBets])

  const handleUpdateResult = async (betId: string, result: 'won' | 'lost' | 'void') => {
    try {
      const { error } = await supabase
        .from('bets')
        .update({ status: result, updated_at: new Date().toISOString() })
        .eq('id', betId)

      if (!error) {
        fetchBets()
      }
    } catch (error) {
      console.error('Error updating bet:', error)
    } finally {
      setShowResultModal(null)
    }
  }

  const handleBetAdded = () => {
    setShowAddModal(false)
    fetchBets()
  }

  const getStatusBadge = (status: Bet['status']) => {
    switch (status) {
      case 'won': return <span className="px-2 py-1 text-xs rounded-full bg-green-500/20 text-green-400">Ganhou</span>
      case 'lost': return <span className="px-2 py-1 text-xs rounded-full bg-red-500/20 text-red-400">Perdeu</span>
      case 'void': return <span className="px-2 py-1 text-xs rounded-full bg-gray-500/20 text-gray-400">Anulada</span>
      case 'cashout': return <span className="px-2 py-1 text-xs rounded-full bg-blue-500/20 text-blue-400">Cashout</span>
      default: return <span className="px-2 py-1 text-xs rounded-full bg-yellow-500/20 text-yellow-400">Pendente</span>
    }
  }

  const getSourceBadge = (source: Bet['source']) => {
    switch (source) {
      case 'chat': return <span className="flex items-center gap-1 px-2 py-0.5 text-xs rounded-full bg-blue-500/20 text-blue-400"><MessageCircle size={10} />Chat</span>
      case 'daily_picks': return <span className="flex items-center gap-1 px-2 py-0.5 text-xs rounded-full bg-yellow-500/20 text-yellow-400"><Zap size={10} />Picks</span>
      default: return <span className="px-2 py-0.5 text-xs rounded-full bg-gray-500/20 text-gray-400">Manual</span>
    }
  }

  const headerContent = (
    <button
      onClick={() => setShowAddModal(true)}
      className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg font-medium transition-colors text-sm"
    >
      <Plus size={16} />
      <span className="hidden sm:inline">Adicionar Aposta</span>
    </button>
  )
  
  if (loading) {
    return (
      <AppShell title="Dashboard">
        <div className="flex items-center justify-center h-full">
          <Loader2 className="animate-spin text-caramelo" size={32} />
        </div>
      </AppShell>
    )
  }

  return (
    <AppShell title="Dashboard" headerContent={headerContent}>
      <div className="max-w-7xl mx-auto p-4 sm:p-6">
        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-8">
          <div className="bg-dark-surface border border-dark-border rounded-xl p-5">
            <div className="flex items-center justify-between mb-3">
              <BarChart3 className="text-blue-400" size={22} />
              <span className="text-xs text-gray-500">Total</span>
            </div>
            <p className="text-2xl font-bold">{stats.total}</p>
            <p className="text-sm text-gray-400">Apostas registradas</p>
          </div>

          <div className="bg-dark-surface border border-dark-border rounded-xl p-5">
            <div className="flex items-center justify-between mb-3">
              <TrendingUp className="text-green-400" size={22} />
              <span className="text-xs text-gray-500">{stats.won}W / {stats.lost}L</span>
            </div>
            <p className="text-2xl font-bold">{stats.winrate}%</p>
            <p className="text-sm text-gray-400">Taxa de acerto</p>
          </div>

          {/* ROI Card */}
          <div className="bg-dark-surface border border-dark-border rounded-xl p-5">
            <div className="flex items-center justify-between mb-3">
              <DollarSign className={stats.roi >= 0 ? "text-green-400" : "text-red-400"} size={22} />
              <span className="text-xs text-gray-500">ROI</span>
            </div>
            <p className={`text-2xl font-bold ${stats.roi >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {stats.roi >= 0 ? '+' : ''}{stats.roi}%
            </p>
            <p className="text-sm text-gray-400">
              {stats.totalProfitLoss >= 0 ? '+' : ''}R${stats.totalProfitLoss.toFixed(2)}
            </p>
          </div>

          <div className="bg-dark-surface border border-dark-border rounded-xl p-5">
            <div className="flex items-center justify-between mb-3">
              <Diamond className="text-yellow-400" size={22} />
              <span className="text-xs text-gray-500">Value</span>
            </div>
            <p className="text-2xl font-bold">{stats.valueBets}</p>
            <p className="text-sm text-gray-400">Apostas com valor</p>
          </div>

          <div className="bg-dark-surface border border-dark-border rounded-xl p-5">
            <div className="flex items-center justify-between mb-3">
              <Flame className="text-orange-400" size={22} />
              <span className="text-xs text-gray-500">Streak</span>
            </div>
            <p className="text-2xl font-bold">{stats.streak}</p>
            <p className="text-sm text-gray-400">Vitórias seguidas</p>
          </div>
        </div>

        {/* Bets List */}
        <div className="bg-dark-surface border border-dark-border rounded-xl overflow-hidden">
          <div className="p-4 border-b border-dark-border flex items-center justify-between">
            <h2 className="font-semibold">Suas Apostas</h2>
            <span className="text-sm text-gray-400">{stats.pending} pendentes</span>
          </div>
          
          {bets.length === 0 ? (
            <div className="p-12 text-center">
              <Target className="mx-auto text-gray-500 mb-4" size={48} />
              <h3 className="text-lg font-semibold mb-2">Nenhuma aposta registrada</h3>
              <p className="text-gray-400 mb-6">
                Use o Chat ou Picks Diários para adicionar apostas ao seu dashboard.
              </p>
              <div className="flex gap-3 justify-center">
                <Link href="/" className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg font-medium transition-colors">
                  Ir para o Chat
                </Link>
                <Link href="/picks" className="px-4 py-2 bg-yellow-600 hover:bg-yellow-700 rounded-lg font-medium transition-colors">
                  Ver Picks
                </Link>
              </div>
            </div>
          ) : (
            <div className="divide-y divide-dark-border">
              {bets.map(bet => (
                <div key={bet.id} className="p-4 hover:bg-dark-border/30 transition-colors">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-3 mb-1">
                        <span className="font-medium">{bet.home_team} vs {bet.away_team}</span>
                        {bet.value_flag && (
                          <span className="flex items-center space-x-1 px-2 py-0.5 text-xs rounded-full bg-yellow-500/20 text-yellow-400">
                            <Diamond size={12} />
                            <span>Value</span>
                          </span>
                        )}
                        {getSourceBadge(bet.source)}
                      </div>
                      <div className="flex items-center space-x-4 text-sm text-gray-400">
                        <span>{getMarketLabel(bet.market)}</span>
                        <span>@{bet.odds.toFixed(2)}</span>
                        {bet.stake && <span>R${bet.stake}</span>}
                        <span>{new Date(bet.created_at).toLocaleDateString('pt-BR')}</span>
                      </div>
                    </div>
                    <div className="flex items-center space-x-3">
                      {getStatusBadge(bet.status)}
                      {bet.status === 'pending' && (
                        <button
                          onClick={() => setShowResultModal(bet.id)}
                          className="p-2 text-gray-400 hover:text-white hover:bg-dark-border rounded-lg transition-colors"
                          title="Marcar resultado"
                        >
                          <Edit3 size={16} />
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Add Bet Modal */}
      <AddBetModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        onSuccess={handleBetAdded}
        prefill={{
          homeTeam: '',
          awayTeam: '',
          source: 'manual'
        }}
      />

      {/* Result Modal */}
      {showResultModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-dark-surface border border-dark-border rounded-2xl p-6 max-w-sm w-full shadow-2xl">
            <div className="text-center mb-6">
              <AlertCircle className="mx-auto text-yellow-400 mb-4" size={32} />
              <h3 className="text-lg font-semibold mb-2">Marcar resultado manualmente</h3>
              <p className="text-gray-400 text-sm">
                Não encontramos esse jogo na base de dados. Você pode marcar o resultado manualmente.
              </p>
            </div>
            
            <div className="space-y-2">
              <button
                onClick={() => handleUpdateResult(showResultModal, 'won')}
                className="w-full py-3 px-4 rounded-lg bg-green-600 hover:bg-green-700 text-white font-medium transition-colors flex items-center justify-center space-x-2"
              >
                <Check size={18} />
                <span>Ganhou</span>
              </button>
              <button
                onClick={() => handleUpdateResult(showResultModal, 'lost')}
                className="w-full py-3 px-4 rounded-lg bg-red-600 hover:bg-red-700 text-white font-medium transition-colors flex items-center justify-center space-x-2"
              >
                <X size={18} />
                <span>Perdeu</span>
              </button>
              <button
                onClick={() => handleUpdateResult(showResultModal, 'void')}
                className="w-full py-3 px-4 rounded-lg bg-gray-600 hover:bg-gray-700 text-white font-medium transition-colors"
              >
                Anulada
              </button>
            </div>
            
            <button
              onClick={() => setShowResultModal(null)}
              className="w-full mt-4 py-2 text-gray-400 hover:text-white transition-colors"
            >
              Cancelar
            </button>
          </div>
        </div>
      )}
    </AppShell>
  )
}
