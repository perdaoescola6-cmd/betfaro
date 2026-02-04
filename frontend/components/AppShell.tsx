'use client'

import { useState, useEffect, ReactNode } from 'react'
import { useRouter } from 'next/navigation'
import { Menu } from 'lucide-react'
import { createClient } from '@/lib/supabase/client'
import Sidebar from './Sidebar'

interface UserData {
  id: string
  email: string
  subscription?: {
    plan: string
    status: string
    current_period_end: string
  } | null
}

interface AppShellProps {
  children: ReactNode
  title?: string
  showHeader?: boolean
  headerContent?: ReactNode
}

export default function AppShell({ 
  children, 
  title, 
  showHeader = true,
  headerContent 
}: AppShellProps) {
  const router = useRouter()
  const supabase = createClient()
  const [user, setUser] = useState<UserData | null>(null)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isCheckingAuth, setIsCheckingAuth] = useState(true)

  useEffect(() => {
    checkAuth()

    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === 'SIGNED_IN' && session?.user) {
        loadUserData(session.user.id, session.user.email || '')
        setIsAuthenticated(true)
      } else if (event === 'SIGNED_OUT') {
        setUser(null)
        setIsAuthenticated(false)
        router.push('/')
      }
    })

    return () => subscription.unsubscribe()
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
        router.push('/auth/login')
      }
    } catch (error) {
      console.error('Auth check failed:', error)
      setIsAuthenticated(false)
      router.push('/auth/login')
    } finally {
      setIsCheckingAuth(false)
    }
  }

  const loadUserData = async (userId: string, email: string) => {
    try {
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

  // Loading state
  if (isCheckingAuth) {
    return (
      <div className="min-h-screen bg-dark-bg flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-caramelo to-caramelo-accent flex items-center justify-center animate-pulse">
            <span className="text-2xl">⚽</span>
          </div>
          <p className="text-gray-400">Carregando...</p>
        </div>
      </div>
    )
  }

  // Not authenticated - will redirect
  if (!isAuthenticated) {
    return null
  }

  return (
    <div className="h-screen bg-dark-bg flex overflow-hidden">
      {/* Sidebar */}
      <Sidebar 
        user={user} 
        isOpen={sidebarOpen} 
        onClose={() => setSidebarOpen(false)} 
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Header */}
        {showHeader && (
          <header className="flex-shrink-0 bg-dark-surface/80 backdrop-blur-sm border-b border-dark-border/50 px-4 py-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <button
                  onClick={() => setSidebarOpen(true)}
                  className="lg:hidden p-2 text-gray-400 hover:text-white hover:bg-dark-border/50 rounded-lg transition-colors"
                >
                  <Menu size={22} />
                </button>
                {title && (
                  <h1 className="text-lg font-semibold text-white truncate">{title}</h1>
                )}
              </div>
              {headerContent}
            </div>
          </header>
        )}

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  )
}
