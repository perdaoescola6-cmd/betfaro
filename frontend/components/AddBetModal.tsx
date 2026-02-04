'use client'

import { useState } from 'react'
import { X, Check, Loader2 } from 'lucide-react'

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
    homeTeam: string
    awayTeam: string
    source: 'chat' | 'daily_picks' | 'manual'
    fixtureId?: string
    league?: string
    kickoffAt?: string
    botReco?: BotReco
    suggestedMarket?: string
    valueFlag?: boolean
  }
}

const MARKET_OPTIONS = [
  { value: '', label: 'Selecione o mercado...' },
  { value: 'over_0_5', label: 'Over 0.5 Gols' },
  { value: 'over_1_5', label: 'Over 1.5 Gols' },
  { value: 'over_2_5', label: 'Over 2.5 Gols' },
  { value: 'over_3_5', label: 'Over 3.5 Gols' },
  { value: 'under_0_5', label: 'Under 0.5 Gols' },
  { value: 'under_1_5', label: 'Under 1.5 Gols' },
  { value: 'under_2_5', label: 'Under 2.5 Gols' },
  { value: 'under_3_5', label: 'Under 3.5 Gols' },
  { value: 'btts_yes', label: 'BTTS Sim' },
  { value: 'btts_no', label: 'BTTS Não' },
  { value: '1x2_home', label: 'Vitória Casa (1)' },
  { value: '1x2_draw', label: 'Empate (X)' },
  { value: '1x2_away', label: 'Vitória Fora (2)' },
  { value: 'dc_1x', label: 'Dupla Chance 1X' },
  { value: 'dc_x2', label: 'Dupla Chance X2' },
  { value: 'dc_12', label: 'Dupla Chance 12' },
  { value: 'ht_over_0_5', label: 'HT Over 0.5' },
  { value: 'ht_over_1_5', label: 'HT Over 1.5' },
  { value: 'corners_over_8_5', label: 'Escanteios Over 8.5' },
  { value: 'corners_over_9_5', label: 'Escanteios Over 9.5' },
  { value: 'corners_over_10_5', label: 'Escanteios Over 10.5' },
  { value: 'other', label: 'Outro mercado' },
]

export default function AddBetModal({ isOpen, onClose, onSuccess, prefill }: AddBetModalProps) {
  const [market, setMarket] = useState(prefill?.suggestedMarket || '')
  const [odds, setOdds] = useState('')
  const [stake, setStake] = useState('')
  const [note, setNote] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')

  if (!isOpen) return null

  const isValid = market && odds && parseFloat(odds) >= 1.01

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!isValid || !prefill) return

    setIsLoading(true)
    setError('')

    try {
      const response = await fetch('/api/bets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source: prefill.source,
          homeTeam: prefill.homeTeam,
          awayTeam: prefill.awayTeam,
          fixtureId: prefill.fixtureId,
          league: prefill.league,
          market,
          odds: parseFloat(odds),
          stake: stake ? parseFloat(stake) : null,
          note: note || null,
          botReco: prefill.botReco,
          valueFlag: prefill.valueFlag || false,
          kickoffAt: prefill.kickoffAt
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

        {/* Match Info */}
        {prefill && (
          <div className="bg-dark-bg rounded-lg p-4 mb-6">
            <div className="text-center">
              <span className="text-lg font-medium text-white">
                {prefill.homeTeam} vs {prefill.awayTeam}
              </span>
              {prefill.league && (
                <p className="text-sm text-gray-400 mt-1">{prefill.league}</p>
              )}
              {prefill.valueFlag && (
                <span className="inline-block mt-2 px-2 py-0.5 bg-green-500/20 text-green-400 text-xs rounded">
                  VALUE BET
                </span>
              )}
            </div>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
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
              {MARKET_OPTIONS.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
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
