import { NextRequest, NextResponse } from 'next/server'

// v4 - Fetches from backend Python, filters future games, adds premium formatting
export const dynamic = 'force-dynamic'
export const revalidate = 0

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || process.env.BACKEND_URL || 'https://betfaro-production.up.railway.app'

// League short names for display
const LEAGUE_SHORT_NAMES: Record<string, string> = {
  'Serie A': 'Brasileirão',
  'Brasileirão Série A': 'Brasileirão',
  'Copa do Brasil': 'Copa BR',
  'UEFA Champions League': 'Champions',
  'Champions League': 'Champions',
  'CONCACAF Champions League': 'CONCACAF',
  'Copa Libertadores': 'Libertadores',
  'Premier League': 'Premier',
  'La Liga': 'La Liga',
  'Bundesliga': 'Bundesliga',
  'Ligue 1': 'Ligue 1',
  'Serie A Italy': 'Serie A',
  'Liga Profesional Argentina': 'Argentina',
  'Capixaba': 'Capixaba',
  'Amazonense': 'Amazonense',
  'Copa Costa Rica': 'Costa Rica',
}

// League tier priority (1 = highest priority)
const LEAGUE_TIERS: Record<string, number> = {
  'Serie A': 1,
  'Brasileirão Série A': 1,
  'Copa do Brasil': 1,
  'Champions League': 1,
  'UEFA Champions League': 1,
  'Copa Libertadores': 1,
  'Premier League': 2,
  'La Liga': 2,
  'Bundesliga': 2,
  'Ligue 1': 2,
  'Serie A Italy': 2,
  'CONCACAF Champions League': 2,
  'Liga Profesional Argentina': 3,
}

const FALLBACK_SUGGESTIONS = [
  { label: "Flamengo x Palmeiras", query: "Flamengo x Palmeiras", league: "Brasileirão", kickoffDisplay: "", tier: 1 },
  { label: "Real Madrid x Barcelona", query: "Real Madrid x Barcelona", league: "La Liga", kickoffDisplay: "", tier: 2 },
  { label: "Arsenal x Chelsea", query: "Arsenal x Chelsea", league: "Premier", kickoffDisplay: "", tier: 2 },
  { label: "Bayern x Dortmund", query: "Bayern x Dortmund", league: "Bundesliga", kickoffDisplay: "", tier: 2 },
  { label: "Milan x Inter", query: "Milan x Inter", league: "Serie A", kickoffDisplay: "", tier: 2 },
  { label: "PSG x Marseille", query: "PSG x Marseille", league: "Ligue 1", kickoffDisplay: "", tier: 2 },
]

interface BackendSuggestion {
  label: string
  query: string
  league?: string
  time?: string
}

interface Suggestion {
  label: string
  query: string
  league: string
  kickoffAt?: string
  kickoffDisplay: string
  tier: number
}

/**
 * Ensure kickoff time is in ISO UTC format
 * The frontend will convert to user's local timezone
 */
function ensureIsoUtc(dateStr: string | undefined): string | undefined {
  if (!dateStr) return undefined
  
  try {
    const date = new Date(dateStr)
    if (isNaN(date.getTime())) return undefined
    // Return ISO string (always UTC with Z suffix)
    return date.toISOString()
  } catch {
    return undefined
  }
}

function isFutureGame(dateStr: string | undefined): boolean {
  if (!dateStr) return true // If no date, include it
  
  try {
    const kickoff = new Date(dateStr)
    const now = new Date()
    return kickoff > now
  } catch {
    return true
  }
}

async function fetchFromBackend(day: string): Promise<BackendSuggestion[]> {
  try {
    const response = await fetch(`${BACKEND_URL}/api/suggestions?day=${day}`, {
      headers: { 'Content-Type': 'application/json' },
      cache: 'no-store',
    })
    
    if (!response.ok) {
      console.error(`[suggestions] Backend error for ${day}: ${response.status}`)
      return []
    }
    
    const data = await response.json()
    return data.suggestions || []
  } catch (error) {
    console.error(`[suggestions] Error fetching ${day} from backend:`, error)
    return []
  }
}

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const limit = parseInt(searchParams.get('limit') || '10')
  
  const now = new Date()
  const generatedAt = now.toISOString()
  
  console.log(`[suggestions] Fetching suggestions at ${generatedAt}`)
  
  try {
    // Fetch from backend for today and tomorrow
    const [todaySuggestions, tomorrowSuggestions] = await Promise.all([
      fetchFromBackend('today'),
      fetchFromBackend('tomorrow')
    ])
    
    const allBackendSuggestions = [...todaySuggestions, ...tomorrowSuggestions]
    console.log(`[suggestions] Backend returned ${allBackendSuggestions.length} suggestions`)
    
    // Filter only FUTURE games
    let filteredPast = 0
    const futureSuggestions = allBackendSuggestions.filter(s => {
      if (!isFutureGame(s.time)) {
        filteredPast++
        return false
      }
      return true
    })
    
    console.log(`[suggestions] Filtered ${filteredPast} past games, ${futureSuggestions.length} remaining`)
    
    // Map to our format with tier
    // NOTE: kickoffAt is returned as ISO UTC - frontend handles timezone conversion
    const suggestions: Suggestion[] = futureSuggestions.map(s => {
      const leagueName = s.league || 'Unknown'
      const shortName = LEAGUE_SHORT_NAMES[leagueName] || leagueName.split(' ')[0]
      const tier = LEAGUE_TIERS[leagueName] || 4
      
      return {
        label: s.label,
        query: s.query,
        league: shortName,
        kickoffAt: ensureIsoUtc(s.time), // Always return ISO UTC
        kickoffDisplay: '', // Frontend will format this based on user's timezone
        tier
      }
    })
    
    // Sort by tier (lower first), then by kickoff (sooner first)
    suggestions.sort((a, b) => {
      if (a.tier !== b.tier) return a.tier - b.tier
      if (a.kickoffAt && b.kickoffAt) {
        return new Date(a.kickoffAt).getTime() - new Date(b.kickoffAt).getTime()
      }
      return 0
    })
    
    // Remove duplicates by label
    const seen = new Set<string>()
    const uniqueSuggestions = suggestions.filter(s => {
      if (seen.has(s.label)) return false
      seen.add(s.label)
      return true
    })
    
    const result = uniqueSuggestions.slice(0, limit)
    
    console.log(`[suggestions] Returning ${result.length} suggestions`)
    
    if (result.length === 0) {
      return NextResponse.json({
        generatedAt,
        items: FALLBACK_SUGGESTIONS,
        source: 'fallback',
        stats: { total: allBackendSuggestions.length, filteredPast, future: 0 }
      }, {
        headers: { 'Cache-Control': 'no-store, max-age=0' }
      })
    }
    
    return NextResponse.json({
      generatedAt,
      items: result,
      source: 'api',
      stats: { total: allBackendSuggestions.length, filteredPast, future: futureSuggestions.length }
    }, {
      headers: { 'Cache-Control': 'no-store, max-age=0' }
    })
    
  } catch (error) {
    console.error('[suggestions] Error:', error)
    return NextResponse.json({
      generatedAt,
      items: FALLBACK_SUGGESTIONS,
      source: 'fallback',
      error: 'Failed to fetch suggestions'
    }, {
      headers: { 'Cache-Control': 'no-store, max-age=0' }
    })
  }
}
