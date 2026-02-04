/**
 * Official Markets Configuration for BetFaro
 * All market_keys are in snake_case format
 */

export interface Market {
  key: string
  label: string
  category: 'goals_ft' | 'btts_ft' | 'result_ft' | 'double_chance_ft' | 'goals_ht' | 'corners_ft'
  params?: {
    threshold?: number
    period?: 'ft' | 'ht'
  }
}

// Full Time - Goals
export const GOALS_FT_MARKETS: Market[] = [
  { key: 'over_0_5_ft', label: 'Over 0.5 Gols', category: 'goals_ft', params: { threshold: 0.5, period: 'ft' } },
  { key: 'over_1_5_ft', label: 'Over 1.5 Gols', category: 'goals_ft', params: { threshold: 1.5, period: 'ft' } },
  { key: 'over_2_5_ft', label: 'Over 2.5 Gols', category: 'goals_ft', params: { threshold: 2.5, period: 'ft' } },
  { key: 'over_3_5_ft', label: 'Over 3.5 Gols', category: 'goals_ft', params: { threshold: 3.5, period: 'ft' } },
  { key: 'under_0_5_ft', label: 'Under 0.5 Gols', category: 'goals_ft', params: { threshold: 0.5, period: 'ft' } },
  { key: 'under_1_5_ft', label: 'Under 1.5 Gols', category: 'goals_ft', params: { threshold: 1.5, period: 'ft' } },
  { key: 'under_2_5_ft', label: 'Under 2.5 Gols', category: 'goals_ft', params: { threshold: 2.5, period: 'ft' } },
  { key: 'under_3_5_ft', label: 'Under 3.5 Gols', category: 'goals_ft', params: { threshold: 3.5, period: 'ft' } },
]

// Both Teams To Score (FT)
export const BTTS_FT_MARKETS: Market[] = [
  { key: 'btts_yes_ft', label: 'Ambos Marcam - Sim', category: 'btts_ft' },
  { key: 'btts_no_ft', label: 'Ambos Marcam - Não', category: 'btts_ft' },
]

// Result FT (1X2)
export const RESULT_FT_MARKETS: Market[] = [
  { key: 'home_win_ft', label: 'Vitória Casa', category: 'result_ft' },
  { key: 'draw_ft', label: 'Empate', category: 'result_ft' },
  { key: 'away_win_ft', label: 'Vitória Fora', category: 'result_ft' },
]

// Double Chance FT
export const DOUBLE_CHANCE_FT_MARKETS: Market[] = [
  { key: 'dc_1x_ft', label: 'Dupla Chance 1X', category: 'double_chance_ft' },
  { key: 'dc_x2_ft', label: 'Dupla Chance X2', category: 'double_chance_ft' },
  { key: 'dc_12_ft', label: 'Dupla Chance 12', category: 'double_chance_ft' },
]

// Half Time - Goals
export const GOALS_HT_MARKETS: Market[] = [
  { key: 'over_0_5_ht', label: 'Over 0.5 Gols (HT)', category: 'goals_ht', params: { threshold: 0.5, period: 'ht' } },
  { key: 'over_1_5_ht', label: 'Over 1.5 Gols (HT)', category: 'goals_ht', params: { threshold: 1.5, period: 'ht' } },
]

// Corners FT
export const CORNERS_FT_MARKETS: Market[] = [
  { key: 'corners_over_8_5_ft', label: 'Corners Over 8.5', category: 'corners_ft', params: { threshold: 8.5, period: 'ft' } },
  { key: 'corners_over_9_5_ft', label: 'Corners Over 9.5', category: 'corners_ft', params: { threshold: 9.5, period: 'ft' } },
]

// All markets combined
export const ALL_MARKETS: Market[] = [
  ...GOALS_FT_MARKETS,
  ...BTTS_FT_MARKETS,
  ...RESULT_FT_MARKETS,
  ...DOUBLE_CHANCE_FT_MARKETS,
  ...GOALS_HT_MARKETS,
  ...CORNERS_FT_MARKETS,
]

// Grouped markets for dropdown display
export const MARKETS_BY_CATEGORY = {
  'Gols (FT)': GOALS_FT_MARKETS,
  'Ambos Marcam': BTTS_FT_MARKETS,
  'Resultado (1X2)': RESULT_FT_MARKETS,
  'Dupla Chance': DOUBLE_CHANCE_FT_MARKETS,
  'Gols (HT)': GOALS_HT_MARKETS,
  'Corners': CORNERS_FT_MARKETS,
}

// Helper to get market by key
export function getMarketByKey(key: string): Market | undefined {
  return ALL_MARKETS.find(m => m.key === key)
}

// Helper to get label by key
export function getMarketLabel(key: string): string {
  return getMarketByKey(key)?.label || key
}

// Map of key to label for quick lookup
export const MARKET_KEY_TO_LABEL: Record<string, string> = Object.fromEntries(
  ALL_MARKETS.map(m => [m.key, m.label])
)
