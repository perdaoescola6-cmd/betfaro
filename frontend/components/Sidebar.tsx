'use client'

import { usePathname } from 'next/navigation'
import Link from 'next/link'
import { 
  MessageCircle, 
  BarChart3, 
  CreditCard, 
  User, 
  LogOut, 
  X, 
  HelpCircle, 
  Target 
} from 'lucide-react'
import { createClient } from '@/lib/supabase/client'

interface UserData {
  email?: string
  subscription?: {
    plan: string
    status: string
  } | null
}

interface SidebarProps {
  user: UserData | null
  isOpen: boolean
  onClose: () => void
}

const navItems = [
  { href: '/', label: 'Chat', icon: MessageCircle, activeExact: true },
  { href: '/picks', label: 'Picks Diários', icon: Target, badge: 'ELITE', badgeColor: 'yellow' },
  { href: '/dashboard', label: 'Dashboard', icon: BarChart3 },
  { href: '/plans', label: 'Planos', icon: CreditCard },
  { href: '/account', label: 'Conta', icon: User },
  { href: '/ajuda', label: 'Ajuda', icon: HelpCircle },
]

export default function Sidebar({ user, isOpen, onClose }: SidebarProps) {
  const pathname = usePathname()
  const supabase = createClient()

  const handleLogout = async () => {
    await supabase.auth.signOut()
    window.location.href = '/'
  }

  const isActive = (href: string, activeExact?: boolean) => {
    if (activeExact) {
      return pathname === href
    }
    return pathname === href || pathname.startsWith(href + '/')
  }

  const getPlanBadge = (plan: string | undefined) => {
    switch (plan?.toLowerCase()) {
      case 'elite':
        return { text: 'Elite', color: 'bg-yellow-500/20 text-yellow-400' }
      case 'pro':
        return { text: 'Pro', color: 'bg-caramelo/20 text-caramelo' }
      default:
        return { text: 'Free', color: 'bg-gray-500/20 text-gray-400' }
    }
  }

  const planBadge = getPlanBadge(user?.subscription?.plan)

  return (
    <>
      {/* Mobile Overlay */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <aside 
        className={`
          fixed inset-y-0 left-0 z-50 w-64 
          bg-dark-surface/95 backdrop-blur-md
          border-r border-dark-border/50
          transform transition-transform duration-300 ease-in-out
          lg:translate-x-0 lg:static lg:z-auto
          ${isOpen ? 'translate-x-0' : '-translate-x-full'}
          flex flex-col
        `}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-dark-border/50">
          <Link href="/" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-caramelo to-caramelo-accent flex items-center justify-center">
              <span className="text-lg">⚽</span>
            </div>
            <span className="text-xl font-bold text-gradient">BetFaro</span>
          </Link>
          <button
            onClick={onClose}
            className="lg:hidden p-1.5 text-gray-400 hover:text-white hover:bg-dark-border/50 rounded-lg transition-colors"
          >
            <X size={20} />
          </button>
        </div>
        
        {/* Navigation */}
        <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon
            const active = isActive(item.href, item.activeExact)
            
            return (
              <Link 
                key={item.href}
                href={item.href} 
                onClick={onClose}
                className={`
                  flex items-center gap-3 px-3 py-2.5 rounded-lg
                  transition-all duration-200
                  ${active 
                    ? 'bg-caramelo/20 text-caramelo border-l-2 border-caramelo' 
                    : 'text-gray-300 hover:bg-dark-border/50 hover:text-white border-l-2 border-transparent'
                  }
                `}
              >
                <Icon size={20} className={active ? 'text-caramelo' : ''} />
                <span className="font-medium">{item.label}</span>
                {item.badge && (
                  <span className={`ml-auto text-[10px] px-1.5 py-0.5 rounded font-semibold
                    ${item.badgeColor === 'yellow' ? 'bg-yellow-500/20 text-yellow-400' : 'bg-gray-500/20 text-gray-400'}
                  `}>
                    {item.badge}
                  </span>
                )}
              </Link>
            )
          })}
        </nav>
        
        {/* Footer */}
        <div className="p-4 border-t border-dark-border/50 bg-dark-bg/30">
          {/* User Info */}
          <div className="mb-3 px-2">
            <p className="text-sm text-gray-400 truncate">{user?.email || 'Carregando...'}</p>
            <div className="flex items-center gap-2 mt-1">
              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${planBadge.color}`}>
                {planBadge.text}
              </span>
              {user?.subscription?.status === 'active' && (
                <span className="text-xs text-green-400">Ativo</span>
              )}
            </div>
          </div>
          
          {/* Logout Button */}
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-gray-400 hover:text-red-400 hover:bg-red-500/10 transition-colors"
          >
            <LogOut size={18} />
            <span className="font-medium">Sair</span>
          </button>
        </div>
      </aside>
    </>
  )
}
