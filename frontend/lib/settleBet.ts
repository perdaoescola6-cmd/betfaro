/**
 * Bet Settlement Logic for BetFaro
 * Central function to determine bet outcome based on fixture data
 */

export type BetStatus = 'won' | 'lost' | 'void' | 'pending'

export interface FixtureData {
  status: {
    short: string // FT, AET, PEN, NS, PST, CANC, ABD, SUSP, 1H, HT, 2H, ET, etc
  }
  goals: {
    home: number | null
    away: number | null
  }
  score?: {
    halftime?: {
      home: number | null
      away: number | null
    }
  }
  corners?: {
    home: number | null
    away: number | null
    total?: number | null
  }
}

// Status codes that indicate game is still in progress
const PENDING_STATUSES = ['NS', 'TBD', '1H', 'HT', '2H', 'ET', 'BT', 'P', 'INT', 'LIVE']

// Status codes that indicate game was cancelled/abandoned
const VOID_STATUSES = ['CANC', 'PST', 'ABD', 'SUSP', 'AWD', 'WO']

// Status codes that indicate game is finished
const FINAL_STATUSES = ['FT', 'AET', 'PEN']

/**
 * Main settlement function
 * @param marketKey - The market key (e.g., 'over_2_5' or 'over_2_5_ft')
 * @param fixtureData - Fixture data from API
 * @returns BetStatus - 'won' | 'lost' | 'void' | 'pending'
 */
export function settleBet(marketKey: string, fixtureData: FixtureData): BetStatus {
  const status = fixtureData.status?.short?.toUpperCase()

  // Check if game is still pending
  if (!status || PENDING_STATUSES.includes(status)) {
    return 'pending'
  }

  // Check if game was cancelled/abandoned
  if (VOID_STATUSES.includes(status)) {
    return 'void'
  }

  // Check if game is finished
  if (!FINAL_STATUSES.includes(status)) {
    // Unknown status - treat as pending
    return 'pending'
  }

  // Game is finished - proceed with settlement
  const goalsHome = fixtureData.goals?.home
  const goalsAway = fixtureData.goals?.away

  // Validate goals data exists
  if (goalsHome === null || goalsHome === undefined || goalsAway === null || goalsAway === undefined) {
    return 'void' // Can't settle without goals data
  }

  const ftTotal = goalsHome + goalsAway

  // Normalize market key - add _ft suffix if not present for FT markets
  // This handles both 'over_2_5' and 'over_2_5_ft' formats
  const normalizedMarket = normalizeMarketKey(marketKey)

  // Route to appropriate settlement logic based on market category
  if (normalizedMarket.startsWith('over_') && normalizedMarket.endsWith('_ft')) {
    return settleOverFT(normalizedMarket, ftTotal)
  }

  if (normalizedMarket.startsWith('under_') && normalizedMarket.endsWith('_ft')) {
    return settleUnderFT(normalizedMarket, ftTotal)
  }

  if (normalizedMarket.startsWith('btts_')) {
    return settleBTTS(normalizedMarket, goalsHome, goalsAway)
  }

  if (normalizedMarket === 'home_win_ft' || normalizedMarket === 'draw_ft' || normalizedMarket === 'away_win_ft' ||
      normalizedMarket === 'home_win' || normalizedMarket === 'draw' || normalizedMarket === 'away_win') {
    return settleResultFT(normalizedMarket, goalsHome, goalsAway)
  }

  if (normalizedMarket.startsWith('dc_')) {
    return settleDoubleChance(normalizedMarket, goalsHome, goalsAway)
  }

  if (normalizedMarket.endsWith('_ht')) {
    return settleHT(normalizedMarket, fixtureData)
  }

  if (normalizedMarket.startsWith('corners_')) {
    return settleCorners(normalizedMarket, fixtureData)
  }

  // Unknown market - can't settle
  console.warn(`[settleBet] Unknown market: ${marketKey} (normalized: ${normalizedMarket})`)
  return 'void'
}

/**
 * Normalize market key to standard format
 * Handles variations like 'over_2_5' -> 'over_2_5_ft'
 */
function normalizeMarketKey(marketKey: string): string {
  const key = marketKey.toLowerCase().trim()
  
  // Over/Under markets without suffix -> assume FT
  if (/^(over|under)_\d+_\d+$/.test(key)) {
    return `${key}_ft`
  }
  
  // BTTS markets without suffix -> assume FT
  if (key === 'btts_yes' || key === 'btts_no' || key === 'btts_sim' || key === 'btts_nao') {
    const normalized = key.replace('_sim', '_yes').replace('_nao', '_no')
    return `${normalized}_ft`
  }
  
  // Result markets without suffix
  if (key === 'home_win' || key === 'draw' || key === 'away_win') {
    return `${key}_ft`
  }
  
  // Double chance without suffix
  if (/^dc_(1x|x2|12)$/.test(key)) {
    return `${key}_ft`
  }
  
  return key
}

/**
 * Settle Over X.5 FT markets
 */
function settleOverFT(marketKey: string, ftTotal: number): BetStatus {
  switch (marketKey) {
    case 'over_0_5_ft':
      return ftTotal >= 1 ? 'won' : 'lost'
    case 'over_1_5_ft':
      return ftTotal >= 2 ? 'won' : 'lost'
    case 'over_2_5_ft':
      return ftTotal >= 3 ? 'won' : 'lost'
    case 'over_3_5_ft':
      return ftTotal >= 4 ? 'won' : 'lost'
    default:
      return 'void'
  }
}

/**
 * Settle Under X.5 FT markets
 */
function settleUnderFT(marketKey: string, ftTotal: number): BetStatus {
  switch (marketKey) {
    case 'under_0_5_ft':
      return ftTotal === 0 ? 'won' : 'lost'
    case 'under_1_5_ft':
      return ftTotal <= 1 ? 'won' : 'lost'
    case 'under_2_5_ft':
      return ftTotal <= 2 ? 'won' : 'lost'
    case 'under_3_5_ft':
      return ftTotal <= 3 ? 'won' : 'lost'
    default:
      return 'void'
  }
}

/**
 * Settle BTTS markets
 */
function settleBTTS(marketKey: string, goalsHome: number, goalsAway: number): BetStatus {
  const bothScored = goalsHome >= 1 && goalsAway >= 1

  switch (marketKey) {
    case 'btts_yes_ft':
      return bothScored ? 'won' : 'lost'
    case 'btts_no_ft':
      return !bothScored ? 'won' : 'lost'
    default:
      return 'void'
  }
}

/**
 * Settle 1X2 Result FT markets
 */
function settleResultFT(marketKey: string, goalsHome: number, goalsAway: number): BetStatus {
  switch (marketKey) {
    case 'home_win_ft':
      return goalsHome > goalsAway ? 'won' : 'lost'
    case 'draw_ft':
      return goalsHome === goalsAway ? 'won' : 'lost'
    case 'away_win_ft':
      return goalsHome < goalsAway ? 'won' : 'lost'
    default:
      return 'void'
  }
}

/**
 * Settle Double Chance FT markets
 */
function settleDoubleChance(marketKey: string, goalsHome: number, goalsAway: number): BetStatus {
  switch (marketKey) {
    case 'dc_1x_ft':
      // Home win OR Draw
      return goalsHome >= goalsAway ? 'won' : 'lost'
    case 'dc_x2_ft':
      // Draw OR Away win
      return goalsAway >= goalsHome ? 'won' : 'lost'
    case 'dc_12_ft':
      // Home win OR Away win (no draw)
      return goalsHome !== goalsAway ? 'won' : 'lost'
    default:
      return 'void'
  }
}

/**
 * Settle Half Time markets
 */
function settleHT(marketKey: string, fixtureData: FixtureData): BetStatus {
  const htHome = fixtureData.score?.halftime?.home
  const htAway = fixtureData.score?.halftime?.away

  // If halftime data not available, void the bet
  if (htHome === null || htHome === undefined || htAway === null || htAway === undefined) {
    return 'void'
  }

  const htTotal = htHome + htAway

  switch (marketKey) {
    case 'over_0_5_ht':
      return htTotal >= 1 ? 'won' : 'lost'
    case 'over_1_5_ht':
      return htTotal >= 2 ? 'won' : 'lost'
    default:
      return 'void'
  }
}

/**
 * Settle Corners FT markets
 */
function settleCorners(marketKey: string, fixtureData: FixtureData): BetStatus {
  let cornersTotal: number | null = null

  // Try to get corners total
  if (fixtureData.corners?.total !== null && fixtureData.corners?.total !== undefined) {
    cornersTotal = fixtureData.corners.total
  } else if (
    fixtureData.corners?.home !== null && 
    fixtureData.corners?.home !== undefined &&
    fixtureData.corners?.away !== null && 
    fixtureData.corners?.away !== undefined
  ) {
    cornersTotal = fixtureData.corners.home + fixtureData.corners.away
  }

  // If corners data not available, void the bet
  if (cornersTotal === null) {
    return 'void'
  }

  switch (marketKey) {
    case 'corners_over_8_5_ft':
      return cornersTotal >= 9 ? 'won' : 'lost'
    case 'corners_over_9_5_ft':
      return cornersTotal >= 10 ? 'won' : 'lost'
    default:
      return 'void'
  }
}

/**
 * Batch settle multiple bets
 */
export function settleBets(
  bets: Array<{ id: string; market: string }>,
  fixtureData: FixtureData
): Array<{ id: string; status: BetStatus }> {
  return bets.map(bet => ({
    id: bet.id,
    status: settleBet(bet.market, fixtureData)
  }))
}
