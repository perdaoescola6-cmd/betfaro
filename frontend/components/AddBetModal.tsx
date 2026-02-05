'use client'

import { useState, useEffect } from 'react'
import { X, Check, Loader2 } from 'lucide-react'
import { MARKETS_BY_CATEGORY } from '@/lib/markets'

interface BotReco {
  market?: string
  prob?: number
  confidence?: string
  label?: string
}

interface AddBetModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess?: () => void
  prefill?: {
    homeTeam?: string
    awayTeam?: string
    source: 'chat' | 'daily_picks' | 'manual'
    fixtureId?: string
    league?: string
    kickoffAt?: string
    botReco?: BotReco
    suggestedMarket?: string
    suggestedOdds?: string  // Pre-fill odds when user provides them in chat
    valueFlag?: boolean
  }
}

export default function AddBetModal({ isOpen, onClose, onSuccess, prefill }: AddBetModalProps) {
  const [homeTeam, setHomeTeam] = useState('')
  const [awayTeam, setAwayTeam] = useState('')
  const [market, setMarket] = useState('')
  const [odds, setOdds] = useState('')
  const [stake, setStake] = useState('')
  const [note, setNote] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')

  // Update form when prefill changes or modal opens
  useEffect(() => {
    if (isOpen && prefill) {
      setHomeTeam(prefill.homeTeam || '')
      setAwayTeam(prefill.awayTeam || '')
      setMarket(prefill.suggestedMarket || '')
      // Pre-fill odds if provided by user in chat message
      if (prefill.suggestedOdds) {
        setOdds(prefill.suggestedOdds)
      }
    } else if (isOpen && !prefill) {
      // Reset form for manual entry
      setHomeTeam('')
      setAwayTeam('')
      setMarket('')
      setOdds('')
      setStake('')
      setNote('')
    }
  }, [isOpen, prefill])

  if (!isOpen) return null

  const hasTeams = homeTeam.trim() && awayTeam.trim()
  const isValid = hasTeams && market && odds && parseFloat(odds) >= 1.01

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!isValid) return

    setIsLoading(true)
    setError('')

    try {
      const response = await fetch('/api/bets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source: prefill?.source || 'manual',
          homeTeam: homeTeam.trim(),
          awayTeam: awayTeam.trim(),
          fixtureId: prefill?.fixtureId,
          league: prefill?.league,
          market,
          odds: parseFloat(odds),
          stake: stake ? parseFloat(stake) : null,
          note: note || null,
          botReco: prefill?.botReco,
          valueFlag: prefill?.valueFlag || false,
          kickoffAt: prefill?.kickoffAt
        })
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || 'Erro ao salvar')
      }

      // Success
      onSuccess?.()
      onClose()
      
      // Reset form
      setMarket('')
      setOdds('')
      setStake('')
      setNote('')

    } catch (err: any) {
      setError(err.message || 'Erro ao salvar aposta')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className="relative bg-dark-surface border border-dark-border rounded-xl w-full max-w-md mx-4 p-6 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold text-white">Adicionar Aposta</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {/* League & Value Flag Header */}
        {prefill?.league && (
          <div className="flex items-center justify-between mb-4">
            <span className="text-sm text-gray-400">{prefill.league}</span>
            {prefill.valueFlag && (
              <span className="px-2 py-0.5 bg-green-500/20 text-green-400 text-xs rounded">
                VALUE BET
              </span>
            )}
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Team Inputs */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Time Casa <span className="text-red-400">*</span>
              </label>
              <input
                type="text"
                value={homeTeam}
                onChange={(e) => setHomeTeam(e.target.value)}
                placeholder="Ex: Flamengo"
                className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2.5 text-white focus:outline-none focus:border-blue-500 text-sm"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Time Fora <span className="text-red-400">*</span>
              </label>
              <input
                type="text"
                value={awayTeam}
                onChange={(e) => setAwayTeam(e.target.value)}
                placeholder="Ex: Palmeiras"
                className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2.5 text-white focus:outline-none focus:border-blue-500 text-sm"
                required
              />
            </div>
          </div>

          {/* Market (Required) */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Mercado <span className="text-red-400">*</span>
            </label>
            <select
              value={market}
              onChange={(e) => setMarket(e.target.value)}
              className="w-full bg-dark-bg border border-dark-border rounded-lg px-4 py-3 text-white focus:outline-none focus:border-blue-500"
              required
            >
              <option value="">Selecione o mercado...</option>
              {Object.entries(MARKETS_BY_CATEGORY).map(([category, markets]) => (
                <optgroup key={category} label={category}>
                  {markets.map(m => (
                    <option key={m.key} value={m.key}>{m.label}</option>
                  ))}
                </optgroup>
              ))}
            </select>
          </div>

          {/* Odds (Required) */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Odd <span className="text-red-400">*</span>
            </label>
            <input
              type="number"
              step="0.01"
              min="1.01"
              value={odds}
              onChange={(e) => setOdds(e.target.value)}
              placeholder="Ex: 1.85"
              className="w-full bg-dark-bg border border-dark-border rounded-lg px-4 py-3 text-white focus:outline-none focus:border-blue-500"
              required
            />
          </div>

          {/* Stake (Optional) */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Stake (opcional)
            </label>
            <input
              type="number"
              step="0.01"
              min="0"
              value={stake}
              onChange={(e) => setStake(e.target.value)}
              placeholder="Ex: 50.00"
              className="w-full bg-dark-bg border border-dark-border rounded-lg px-4 py-3 text-white focus:outline-none focus:border-blue-500"
            />
          </div>

          {/* Note (Optional) */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Comentário (opcional)
            </label>
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Anotações sobre a aposta..."
              rows={2}
              className="w-full bg-dark-bg border border-dark-border rounded-lg px-4 py-3 text-white focus:outline-none focus:border-blue-500 resize-none"
            />
          </div>

          {/* Error */}
          {error && (
            <div className="text-red-400 text-sm bg-red-500/10 rounded-lg p-3">
              {error}
            </div>
          )}

          {/* Submit */}
          <button
            type="submit"
            disabled={!isValid || isLoading}
            className="w-full bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white font-medium py-3 rounded-lg transition-colors flex items-center justify-center gap-2"
          >
            {isLoading ? (
              <>
                <Loader2 className="animate-spin" size={18} />
                Salvando...
              </>
            ) : (
              <>
                <Check size={18} />
                Salvar Aposta
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  )
}
