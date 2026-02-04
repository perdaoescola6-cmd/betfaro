'use client'

import { useState } from 'react'
import { Check, X, Loader2 } from 'lucide-react'
import AddBetModal from './AddBetModal'

interface BotReco {
  market?: string
  prob?: number
  confidence?: string
  label?: string
}

interface BetCTAProps {
  homeTeam?: string
  awayTeam?: string
  source: 'chat' | 'daily_picks'
  fixtureId?: string
  league?: string
  kickoffAt?: string
  botReco?: BotReco
  suggestedMarket?: string
  valueFlag?: boolean
  onBetAdded?: () => void
}

export default function BetCTA({
  homeTeam = '',
  awayTeam = '',
  source,
  fixtureId,
  league,
  kickoffAt,
  botReco,
  suggestedMarket,
  valueFlag,
  onBetAdded
}: BetCTAProps) {
  const [showModal, setShowModal] = useState(false)
  const [isSkipping, setIsSkipping] = useState(false)
  const [actionTaken, setActionTaken] = useState<'entered' | 'skipped' | null>(null)

  const handleSkip = async () => {
    setIsSkipping(true)
    try {
      const response = await fetch('/api/bets/skip', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source,
          homeTeam,
          awayTeam,
          fixtureId,
          suggestedMarket,
          metadata: { botReco }
        })
      })

      if (response.ok) {
        setActionTaken('skipped')
      }
    } catch (error) {
      console.error('Error skipping bet:', error)
    } finally {
      setIsSkipping(false)
    }
  }

  const handleBetSuccess = () => {
    setActionTaken('entered')
    onBetAdded?.()
  }

  // Already took action
  if (actionTaken) {
    return (
      <div className="mt-4 p-3 bg-dark-surface/50 rounded-lg border border-dark-border">
        {actionTaken === 'entered' ? (
          <div className="flex items-center gap-2 text-green-400">
            <Check size={16} />
            <span className="text-sm">Aposta adicionada ao Dashboard ✅</span>
          </div>
        ) : (
          <div className="flex items-center gap-2 text-gray-400">
            <X size={16} />
            <span className="text-sm">Registrado como pulado 👍</span>
          </div>
        )}
      </div>
    )
  }

  // Show match info if available
  const hasMatchInfo = homeTeam || awayTeam

  return (
    <>
      <div className="mt-4 p-4 bg-gradient-to-r from-dark-surface/80 to-dark-surface/60 rounded-lg border border-dark-border/50 backdrop-blur-sm shadow-lg">
        {/* Match info header */}
        {hasMatchInfo && (
          <div className="text-center mb-3 pb-3 border-b border-dark-border/30">
            <span className="text-sm font-medium text-white truncate block">
              {homeTeam || '???'} vs {awayTeam || '???'}
            </span>
            {league && <span className="text-xs text-gray-400">{league}</span>}
          </div>
        )}
        
        <p className="text-sm text-gray-300 mb-3">📌 Você entrou nessa aposta?</p>
        <div className="flex gap-3">
          <button
            onClick={() => setShowModal(true)}
            className="flex-1 flex items-center justify-center gap-2 bg-green-600 hover:bg-green-700 text-white text-sm font-medium py-2.5 px-4 rounded-lg transition-all hover:scale-[1.02] active:scale-[0.98]"
          >
            <Check size={16} />
            <span className="truncate">Fiz a bet</span>
          </button>
          <button
            onClick={handleSkip}
            disabled={isSkipping}
            className="flex-1 flex items-center justify-center gap-2 bg-red-600/20 hover:bg-red-600/30 text-red-400 text-sm font-medium py-2.5 px-4 rounded-lg transition-all hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50"
          >
            {isSkipping ? (
              <Loader2 className="animate-spin" size={16} />
            ) : (
              <X size={16} />
            )}
            <span className="truncate">Não entrei</span>
          </button>
        </div>
      </div>

      <AddBetModal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        onSuccess={handleBetSuccess}
        prefill={{
          homeTeam,
          awayTeam,
          source,
          fixtureId,
          league,
          kickoffAt,
          botReco,
          suggestedMarket,
          valueFlag
        }}
      />
    </>
  )
}
