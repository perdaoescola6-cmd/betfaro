'use client'

import { useState, useEffect, useRef } from 'react'
import { MessageCircle, BarChart3, CreditCard, User, LogOut, Send, Menu, X, Trash2, HelpCircle, Target } from 'lucide-react'
import Link from 'next/link'
import { createClient } from '@/lib/supabase/client'
import BetCTA from '@/components/BetCTA'

interface MatchData {
  homeTeam: string
  awayTeam: string
  league?: string
  fixtureId?: string
  kickoffAt?: string
  suggestedMarket?: string
  botReco?: {
    market?: string
    prob?: number
    confidence?: string
  }
}

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  matchData?: MatchData
  isAnalysis?: boolean
}

interface UserData {
  id: string
  email: string
  subscription?: {
    plan: string
    status: string
    current_period_end: string
  } | null
}

interface Suggestion {
  label: string
  query: string
  league?: string
  kickoffAt?: string
  kickoffDisplay?: string
  tier?: number
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [user, setUser] = useState<UserData | null>(null)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isCheckingAuth, setIsCheckingAuth] = useState(true)
  const [showClearModal, setShowClearModal] = useState(false)
  const [showHelpTooltip, setShowHelpTooltip] = useState(false)
  const [suggestions, setSuggestions] = useState<Suggestion[]>([])
  const [suggestionsLoading, setSuggestionsLoading] = useState(true)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const supabase = createClient()

  const fallbackSuggestions: Suggestion[] = [
    { label: "Flamengo x Palmeiras", query: "Flamengo x Palmeiras" },
    { label: "Real Madrid x Barcelona", query: "Real Madrid x Barcelona" },
    { label: "Arsenal x Chelsea", query: "Arsenal x Chelsea" },
    { label: "Benfica x Porto", query: "Benfica x Porto" },
  ]

  useEffect(() => {
    checkAuth()

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === 'SIGNED_IN' && session?.user) {
        loadUserData(session.user.id, session.user.email || '')
        setIsAuthenticated(true)
      } else if (event === 'SIGNED_OUT') {
        setUser(null)
        setIsAuthenticated(false)
      }
    })

    return () => subscription.unsubscribe()
  }, [])

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  // Load dynamic suggestions on mount and auto-refresh every 10 minutes
  useEffect(() => {
    const loadSuggestions = async () => {
      setSuggestionsLoading(true)
      try {
        const response = await fetch('/api/suggestions?limit=8&days=2', { cache: 'no-store' })
        if (response.ok) {
          const data = await response.json()
          if (data.items && data.items.length > 0) {
            setSuggestions(data.items)
          } else {
            setSuggestions(fallbackSuggestions)
          }
        } else {
          setSuggestions(fallbackSuggestions)
        }
      } catch (error) {
        console.error('Failed to load suggestions:', error)
        setSuggestions(fallbackSuggestions)
      } finally {
        setSuggestionsLoading(false)
      }
    }
    
    loadSuggestions()
    
    // Auto-refresh every 10 minutes
    const interval = setInterval(loadSuggestions, 10 * 60 * 1000)
    
    // Also refresh at midnight
    const checkMidnight = setInterval(() => {
      const now = new Date()
      if (now.getHours() === 0 && now.getMinutes() === 0) {
        loadSuggestions()
      }
    }, 60 * 1000)
    
    return () => {
      clearInterval(interval)
      clearInterval(checkMidnight)
    }
  }, [])

  const checkAuth = async () => {
    setIsCheckingAuth(true)
    try {
      const { data: { user: authUser } } = await supabase.auth.getUser()

      if (authUser) {
        await loadUserData(authUser.id, authUser.email || '')
        setIsAuthenticated(true)
      } else {
        setIsAuthenticated(false)
      }
    } catch (error) {
      console.error('Auth check failed:', error)
      setIsAuthenticated(false)
    } finally {
      setIsCheckingAuth(false)
    }
  }

  const loadUserData = async (userId: string, email: string) => {
    try {
      // Get subscription data
      const { data: subscription } = await supabase
        .from('subscriptions')
        .select('plan, status, current_period_end')
        .eq('user_id', userId)
        .maybeSingle()

      setUser({
        id: userId,
        email: email,
        subscription: subscription
      })
    } catch (error) {
      console.error('Failed to load user data:', error)
      setUser({
        id: userId,
        email: email,
        subscription: null
      })
    }
  }

  const loadChatHistory = async () => {
    const token = localStorage.getItem('token')
    try {
      const response = await fetch('/api/chat/history', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      if (response.ok) {
        const history = await response.json()
        setMessages(history.map((msg: any) => ({
          id: msg.timestamp,
          role: msg.role,
          content: msg.content,
          timestamp: new Date(msg.timestamp)
        })))
      }
    } catch (error) {
      console.error('Failed to load chat history:', error)
    }
  }

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return
    await sendMessageWithQuery(input)
  }

  const sendMessageWithQuery = async (query: string) => {
    if (!query.trim() || isLoading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: query,
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    const token = localStorage.getItem('token')
    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ content: query })
      })

      if (response.ok) {
        const data = await response.json()
        const content = data.reply || data.response || 'Resposta recebida'
        
        // Check if this is a match analysis (contains team names and stats)
        const isAnalysis = content.includes('⚽') && content.includes('vs') && 
                          (content.includes('Over') || content.includes('BTTS') || content.includes('Forma Recente'))
        
        // Try to extract match data from the response
        let matchData: MatchData | undefined
        if (isAnalysis) {
          // Extract team names from "⚽ Team A vs Team B" pattern
          const matchPattern = /⚽\s*([^v]+)\s*vs\s*([^\n]+)/i
          const matchMatch = content.match(matchPattern)
          if (matchMatch) {
            matchData = {
              homeTeam: matchMatch[1].trim(),
              awayTeam: matchMatch[2].trim(),
              league: data.league,
              fixtureId: data.fixtureId,
            }
          }
        }
        
        const assistantMessage: Message = {
          id: data.debugId || Date.now().toString(),
          role: 'assistant',
          content,
          timestamp: new Date(),
          matchData,
          isAnalysis
        }
        setMessages(prev => [...prev, assistantMessage])
      } else {
        const error = await response.json()
        const errorMessage = error.error?.message || error.detail || 'Ocorreu um erro ao processar sua mensagem.'
        setMessages(prev => [...prev, {
          id: Date.now().toString(),
          role: 'assistant',
          content: `❌ ${errorMessage}`,
          timestamp: new Date()
        }])
      }
    } catch (error) {
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        role: 'assistant',
        content: '❌ Erro de conexão. Verifique sua internet e tente novamente.',
        timestamp: new Date()
      }])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const handleLogout = async () => {
    await supabase.auth.signOut()
    setUser(null)
    setIsAuthenticated(false)
    setMessages([])
  }

  const handleClearChat = () => {
    setMessages([])
    localStorage.removeItem('chatHistory')
    setShowClearModal(false)
  }

  // Show loading while checking auth
  if (isCheckingAuth) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-dark-bg">
        <div className="flex flex-col items-center gap-4">
          <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
          <p className="text-gray-400">Carregando...</p>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden">
        {/* Animated Background */}
        <div className="football-bg"></div>
        <div className="grid-pattern"></div>
        
        {/* Floating Football Icons */}
        <div className="football-icon">⚽</div>
        <div className="football-icon">⚽</div>
        <div className="football-icon">⚽</div>
        <div className="football-icon">⚽</div>
        <div className="football-icon">⚽</div>
        
        {/* Animated Gradient Orbs */}
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-caramelo/10 rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-green-500/10 rounded-full blur-3xl animate-pulse" style={{animationDelay: '1s'}}></div>
        
        {/* Main Card */}
        <div className="glass-card max-w-md w-full p-8 relative z-10">
          {/* Logo/Header */}
          <div className="text-center mb-10">
            <div className="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-gradient-to-br from-caramelo to-caramelo-accent mb-6 shadow-lg shadow-caramelo/30">
              <span className="text-4xl">⚽</span>
            </div>
            <h1 className="text-4xl font-bold text-gradient mb-3">BetFaro</h1>
            <p className="text-gray-400 text-lg">Aposte como um insider 🐕</p>
          </div>
          
          {/* Buttons */}
          <div className="space-y-4 mb-10">
            <Link 
              href="/auth/login" 
              className="group relative w-full block text-center py-4 px-6 rounded-xl font-semibold text-white overflow-hidden transition-all duration-300 hover:scale-[1.02] active:scale-[0.98]"
            >
              <div className="absolute inset-0 bg-gradient-to-r from-caramelo to-caramelo-accent transition-all duration-300 group-hover:from-caramelo-hover group-hover:to-caramelo"></div>
              <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300 bg-[radial-gradient(circle_at_50%_-20%,rgba(255,255,255,0.3),transparent_70%)]"></div>
              <span className="relative flex items-center justify-center gap-2">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1" />
                </svg>
                Entrar
              </span>
            </Link>
            
            <Link 
              href="/auth/register" 
              className="group relative w-full block text-center py-4 px-6 rounded-xl font-semibold text-white overflow-hidden transition-all duration-300 hover:scale-[1.02] active:scale-[0.98] border border-gray-600/50 hover:border-green-500/50"
            >
              <div className="absolute inset-0 bg-gradient-to-r from-gray-800/80 to-gray-700/80 transition-all duration-300 group-hover:from-green-600/20 group-hover:to-green-500/20"></div>
              <span className="relative flex items-center justify-center gap-2">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
                </svg>
                Criar Conta Grátis
              </span>
            </Link>
          </div>
          
          {/* Plans Section */}
          <div className="pt-8 border-t border-white/10">
            <h3 className="text-lg font-semibold mb-6 text-center text-gray-300">
              <span className="inline-flex items-center gap-2">
                <svg className="w-5 h-5 text-caramelo" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                </svg>
                Planos Disponíveis
              </span>
            </h3>
            <div className="space-y-3">
              <div className="flex justify-between items-center p-3 rounded-lg bg-white/5 hover:bg-white/10 transition-colors">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-gray-500/20 flex items-center justify-center">
                    <span className="text-gray-400 text-sm font-bold">⚡</span>
                  </div>
                  <span className="font-medium">Free</span>
                </div>
                <span className="text-gray-400 font-bold">Grátis</span>
              </div>
              <div className="flex justify-between items-center p-3 rounded-lg bg-white/5 hover:bg-white/10 transition-colors border border-caramelo/30">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-caramelo/20 flex items-center justify-center">
                    <span className="text-caramelo text-sm font-bold">⭐</span>
                  </div>
                  <div>
                    <span className="font-medium">Pro</span>
                    <span className="ml-2 text-xs bg-caramelo/20 text-caramelo px-2 py-0.5 rounded-full">Popular</span>
                  </div>
                </div>
                <span className="text-green-400 font-bold">R$49<span className="text-xs text-gray-500">/mês</span></span>
              </div>
              <div className="flex justify-between items-center p-3 rounded-lg bg-white/5 hover:bg-white/10 transition-colors">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-purple-500/20 flex items-center justify-center">
                    <span className="text-purple-400 text-sm font-bold">👑</span>
                  </div>
                  <span className="font-medium">Elite</span>
                </div>
                <span className="text-green-400 font-bold">R$99<span className="text-xs text-gray-500">/mês</span></span>
              </div>
            </div>
          </div>
          
          {/* Footer */}
          <div className="mt-8 text-center">
            <p className="text-xs text-gray-500">
              🔒 Pagamento seguro via Stripe
            </p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="h-screen bg-dark-bg flex overflow-hidden">
      {/* Sidebar */}
      <div className={`${sidebarOpen ? 'translate-x-0' : '-translate-x-full'} fixed inset-y-0 left-0 z-50 w-64 bg-dark-surface border-r border-dark-border transition-transform duration-300 lg:translate-x-0 lg:static lg:inset-0`}>
        <div className="flex items-center justify-between p-6 border-b border-dark-border">
          <h2 className="text-xl font-bold text-accent-blue">BetFaro</h2>
          <button
            onClick={() => setSidebarOpen(false)}
            className="lg:hidden text-gray-400 hover:text-white"
          >
            <X size={24} />
          </button>
        </div>
        
        <nav className="p-4 space-y-2">
          <Link href="/" className="flex items-center space-x-3 p-3 rounded-lg bg-dark-border transition-colors">
            <MessageCircle size={20} />
            <span>Chat</span>
          </Link>
          <Link href="/picks" className="flex items-center space-x-3 p-3 rounded-lg hover:bg-dark-border transition-colors">
            <Target size={20} className="text-yellow-400" />
            <span>Picks Diários</span>
            <span className="ml-auto text-[10px] bg-yellow-500/20 text-yellow-400 px-1.5 py-0.5 rounded font-medium">ELITE</span>
          </Link>
          <Link href="/dashboard" className="flex items-center space-x-3 p-3 rounded-lg hover:bg-dark-border transition-colors">
            <BarChart3 size={20} />
            <span>Dashboard</span>
          </Link>
          <Link href="/plans" className="flex items-center space-x-3 p-3 rounded-lg hover:bg-dark-border transition-colors">
            <CreditCard size={20} />
            <span>Planos</span>
          </Link>
          <Link href="/account" className="flex items-center space-x-3 p-3 rounded-lg hover:bg-dark-border transition-colors">
            <User size={20} />
            <span>Conta</span>
          </Link>
          <Link href="/ajuda" className="flex items-center space-x-3 p-3 rounded-lg hover:bg-dark-border transition-colors">
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

      {/* Main Content - Fixed height, no page scroll */}
      <div className="flex-1 flex flex-col h-screen overflow-hidden">
        {/* Header */}
        <header className="bg-dark-surface border-b border-dark-border p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => setSidebarOpen(true)}
                className="lg:hidden text-gray-400 hover:text-white"
              >
                <Menu size={24} />
              </button>
              <h1 className="text-xl font-semibold">Chat de Análises</h1>
            </div>
            <div className="flex items-center space-x-3">
              {/* Help Button with Tooltip */}
              <div className="relative">
                <button
                  onMouseEnter={() => setShowHelpTooltip(true)}
                  onMouseLeave={() => setShowHelpTooltip(false)}
                  className="flex items-center justify-center w-7 h-7 text-gray-400 hover:text-caramelo hover:bg-caramelo/10 rounded-lg transition-colors"
                >
                  <HelpCircle size={16} />
                </button>
                
                {/* Tooltip */}
                {showHelpTooltip && (
                  <div className="absolute right-0 top-full mt-2 w-72 p-4 bg-dark-surface border border-dark-border rounded-xl shadow-2xl z-50">
                    <div className="absolute -top-2 right-4 w-4 h-4 bg-dark-surface border-l border-t border-dark-border transform rotate-45"></div>
                    <h4 className="font-semibold text-caramelo mb-2 text-sm">📖 Como pesquisar</h4>
                    <ul className="text-xs text-gray-300 space-y-1.5">
                      <li className="flex items-start gap-2">
                        <span className="text-green-400">•</span>
                        <span>Use: <code className="bg-dark-border px-1 rounded">TimeA x TimeB</code> ou <code className="bg-dark-border px-1 rounded">vs</code></span>
                      </li>
                      <li className="flex items-start gap-2">
                        <span className="text-green-400">•</span>
                        <span>Ex.: <code className="bg-dark-border px-1 rounded">Arsenal x Chelsea</code></span>
                      </li>
                      <li className="flex items-start gap-2">
                        <span className="text-caramelo">•</span>
                        <span>Opcional: mercados (<code className="bg-dark-border px-1 rounded">over 2.5</code>, <code className="bg-dark-border px-1 rounded">btts sim</code>)</span>
                      </li>
                      <li className="flex items-start gap-2">
                        <span className="text-caramelo">•</span>
                        <span>Opcional: odds (<code className="bg-dark-border px-1 rounded">@2.10</code>)</span>
                      </li>
                      <li className="flex items-start gap-2">
                        <span className="text-yellow-400">⚠️</span>
                        <span>Se houver nomes parecidos, o bot pedirá confirmação</span>
                      </li>
                    </ul>
                    <Link href="/ajuda" className="block mt-3 text-xs text-caramelo hover:text-caramelo-hover font-medium">
                      Ver ajuda completa →
                    </Link>
                  </div>
                )}
              </div>
              
              {messages.length > 0 && (
                <button
                  onClick={() => setShowClearModal(true)}
                  className="flex items-center space-x-1 px-3 py-1.5 text-xs font-medium text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded-lg transition-colors"
                >
                  <Trash2 size={14} />
                  <span>Limpar</span>
                </button>
              )}
              {user?.subscription && (
                <span className="badge badge-success">
                  {user.subscription.plan}
                </span>
              )}
            </div>
          </div>
        </header>

        {/* Chat Area - Fixed height with internal scroll */}
        <div className="flex-1 flex flex-col p-4 overflow-hidden" style={{ height: 'calc(100vh - 73px)' }}>
          <div className="flex-1 overflow-y-auto space-y-4 pr-2" style={{ scrollbarWidth: 'thin' }}>
            {messages.length === 0 ? (
              <div className="text-center py-12">
                <MessageCircle size={48} className="mx-auto text-gray-500 mb-4" />
                <h3 className="text-xl font-semibold mb-2">Sem mensagens ainda</h3>
                <p className="text-gray-400 mb-6">
                  Digite um jogo para começar sua análise
                </p>
                {/* Premium Suggestion Cards */}
                <div className="w-full max-w-3xl mx-auto">
                  {suggestionsLoading ? (
                    <div className="flex items-center justify-center space-x-2 text-gray-400 py-4">
                      <div className="animate-spin h-5 w-5 border-2 border-amber-500 border-t-transparent rounded-full"></div>
                      <span className="text-sm">Carregando jogos de hoje...</span>
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      {suggestions.slice(0, 8).map((suggestion, index) => (
                        <button
                          key={index}
                          onClick={() => sendMessageWithQuery(suggestion.query)}
                          className="group relative bg-dark-surface/80 hover:bg-dark-surface border border-dark-border hover:border-amber-500/50 rounded-xl p-4 text-left transition-all duration-200 hover:shadow-lg hover:shadow-amber-500/10"
                        >
                          {/* League Tag */}
                          {suggestion.league && (
                            <span className="absolute top-3 right-3 text-[10px] font-medium px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-400 uppercase tracking-wide">
                              {suggestion.league}
                            </span>
                          )}
                          
                          {/* Teams */}
                          <div className="font-semibold text-white group-hover:text-amber-50 pr-16 leading-tight">
                            {suggestion.label}
                          </div>
                          
                          {/* Kickoff Time */}
                          {suggestion.kickoffDisplay && (
                            <div className="mt-2 text-xs text-gray-400 group-hover:text-gray-300 flex items-center gap-1.5">
                              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                              </svg>
                              {suggestion.kickoffDisplay}
                            </div>
                          )}
                          
                          {/* Hover indicator */}
                          <div className="absolute bottom-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity">
                            <svg className="w-4 h-4 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                            </svg>
                          </div>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ) : (
              messages.map((message) => (
                <div
                  key={message.id}
                  className={message.role === 'user' 
                    ? 'ml-auto max-w-[80%] bg-blue-600 text-white rounded-2xl rounded-br-md px-4 py-3' 
                    : 'chat-terminal max-w-[90%]'
                  }
                >
                  <div className="whitespace-pre-wrap font-mono text-sm">{message.content}</div>
                  <div className={`text-xs mt-2 ${message.role === 'user' ? 'text-blue-200' : 'text-gray-500'}`}>
                    {message.timestamp.toLocaleTimeString()}
                  </div>
                  
                  {/* BetCTA for analysis messages */}
                  {message.role === 'assistant' && message.isAnalysis && message.matchData && (
                    <BetCTA
                      homeTeam={message.matchData.homeTeam}
                      awayTeam={message.matchData.awayTeam}
                      source="chat"
                      fixtureId={message.matchData.fixtureId}
                      league={message.matchData.league}
                      kickoffAt={message.matchData.kickoffAt}
                      suggestedMarket={message.matchData.suggestedMarket}
                      botReco={message.matchData.botReco}
                    />
                  )}
                </div>
              ))
            )}
            
            {isLoading && (
              <div className="chat-terminal max-w-[90%]">
                <div className="flex items-center space-x-3">
                  <div className="flex space-x-1">
                    <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse"></div>
                    <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse" style={{animationDelay: '0.2s'}}></div>
                    <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse" style={{animationDelay: '0.4s'}}></div>
                  </div>
                  <span className="text-gray-400 font-mono text-sm">Analisando...</span>
                </div>
              </div>
            )}
            
            {/* Scroll anchor */}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Area - Always visible at bottom */}
          <div className="flex space-x-2 pt-4 mt-auto flex-shrink-0">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Digite: TimeA x TimeB ou 'time over 2.5 last 10'..."
              className="input flex-1"
              disabled={isLoading}
            />
            <button
              onClick={sendMessage}
              disabled={isLoading || !input.trim()}
              className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Send size={20} />
            </button>
          </div>
        </div>
      </div>

      {/* Clear Chat Modal */}
      {showClearModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-dark-surface border border-dark-border rounded-2xl p-6 max-w-sm w-full shadow-2xl">
            <div className="text-center mb-6">
              <div className="w-12 h-12 bg-red-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
                <Trash2 className="text-red-400" size={24} />
              </div>
              <h3 className="text-lg font-semibold mb-2">Limpar histórico do chat?</h3>
              <p className="text-gray-400 text-sm">
                Isso apagará todas as mensagens deste dispositivo.
              </p>
            </div>
            <div className="flex space-x-3">
              <button
                onClick={() => setShowClearModal(false)}
                className="flex-1 py-2.5 px-4 rounded-lg bg-dark-border hover:bg-gray-700 text-white font-medium transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={handleClearChat}
                className="flex-1 py-2.5 px-4 rounded-lg bg-red-600 hover:bg-red-700 text-white font-medium transition-colors"
              >
                Limpar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
