import { NextRequest, NextResponse } from 'next/server'

// v2 - Direct API-Football integration with future games filter
export const dynamic = 'force-dynamic'
export const revalidate = 0

// Liga IDs da API-Football com prioridade por tier
const LEAGUE_PRIORITY: Record<number, { tier: number; name: string; shortName: string }> = {
  // Tier 1 - Brasil + Champions + Libertadores
  71: { tier: 1, name: "Brasileirão Série A", shortName: "Brasileirão" },
  73: { tier: 1, name: "Copa do Brasil", shortName: "Copa BR" },
  2: { tier: 1, name: "UEFA Champions League", shortName: "Champions" },
  13: { tier: 1, name: "Copa Libertadores", shortName: "Libertadores" },
  11: { tier: 1, name: "Copa Sul-Americana", shortName: "Sul-Americana" },
  
  // Tier 2 - Top 5 Europa
  39: { tier: 2, name: "Premier League", shortName: "Premier" },
  140: { tier: 2, name: "La Liga", shortName: "La Liga" },
  135: { tier: 2, name: "Serie A", shortName: "Serie A" },
  78: { tier: 2, name: "Bundesliga", shortName: "Bundesliga" },
  61: { tier: 2, name: "Ligue 1", shortName: "Ligue 1" },
  3: { tier: 2, name: "UEFA Europa League", shortName: "Europa League" },
  
  // Tier 3 - Série B + Outras ligas relevantes
  72: { tier: 3, name: "Brasileirão Série B", shortName: "Série B" },
  94: { tier: 3, name: "Primeira Liga", shortName: "Portugal" },
  88: { tier: 3, name: "Eredivisie", shortName: "Holanda" },
  128: { tier: 3, name: "Argentina Primera", shortName: "Argentina" },
  262: { tier: 3, name: "Liga MX", shortName: "México" },
  253: { tier: 3, name: "MLS", shortName: "MLS" },
  
  // Tier 4 - Estaduais BR
  475: { tier: 4, name: "Campeonato Paulista", shortName: "Paulistão" },
  476: { tier: 4, name: "Campeonato Carioca", shortName: "Carioca" },
  477: { tier: 4, name: "Campeonato Mineiro", shortName: "Mineiro" },
  478: { tier: 4, name: "Campeonato Gaúcho", shortName: "Gaúcho" },
}

const FALLBACK_SUGGESTIONS = [
  { label: "Flamengo x Palmeiras", query: "Flamengo x Palmeiras", league: "Brasileirão", tier: 1 },
  { label: "Real Madrid x Barcelona", query: "Real Madrid x Barcelona", league: "La Liga", tier: 2 },
  { label: "Arsenal x Chelsea", query: "Arsenal x Chelsea", league: "Premier", tier: 2 },
  { label: "Bayern x Dortmund", query: "Bayern x Dortmund", league: "Bundesliga", tier: 2 },
  { label: "Milan x Inter", query: "Milan x Inter", league: "Serie A", tier: 2 },
  { label: "PSG x Marseille", query: "PSG x Marseille", league: "Ligue 1", tier: 2 },
]

interface Fixture {
  fixture: {
    id: number
    date: string
    timestamp: number
    status: {
      short: string
    }
  }
  league: {
    id: number
    name: string
  }
  teams: {
    home: { name: string }
    away: { name: string }
  }
}

interface Suggestion {
  label: string
  query: string
  league: string
  kickoffAt: string
  kickoffDisplay: string
  tier: number
}

function formatKickoffDisplay(date: Date, now: Date): string {
  const isToday = date.toDateString() === now.toDateString()
  const tomorrow = new Date(now)
  tomorrow.setDate(tomorrow.getDate() + 1)
  const isTomorrow = date.toDateString() === tomorrow.toDateString()
  
  const hours = date.getHours().toString().padStart(2, '0')
  const minutes = date.getMinutes().toString().padStart(2, '0')
  const time = `${hours}:${minutes}`
  
  if (isToday) return `Hoje • ${time}`
  if (isTomorrow) return `Amanhã • ${time}`
  
  const dayNames = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb']
  return `${dayNames[date.getDay()]} • ${time}`
}

async function fetchFixturesFromAPI(dateStr: string): Promise<Fixture[]> {
  const apiKey = process.env.FOOTBALL_API_KEY
  if (!apiKey) {
    console.error('[suggestions] FOOTBALL_API_KEY not configured')
    return []
  }

  try {
    const leagueIds = Object.keys(LEAGUE_PRIORITY).join('-')
    const url = `https://v3.football.api-sports.io/fixtures?date=${dateStr}&league=${leagueIds}`
    
    const response = await fetch(url, {
      headers: { 'x-apisports-key': apiKey },
      cache: 'no-store'
    })

    if (!response.ok) {
      console.error(`[suggestions] API-Football error: ${response.status}`)
      return []
    }

    const data = await response.json()
    return data.response || []
  } catch (error) {
    console.error('[suggestions] Error fetching fixtures:', error)
    return []
  }
}

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const limit = parseInt(searchParams.get('limit') || '10')
  const days = parseInt(searchParams.get('days') || '2')
  
  const now = new Date()
  const generatedAt = now.toISOString()
  
  console.log(`[suggestions] Fetching suggestions at ${generatedAt}`)
  
  try {
    const allFixtures: Fixture[] = []
    let filteredPast = 0
    let filteredStatus = 0
    
    // Buscar fixtures para D0, D+1 (e D+2 se necessário)
    for (let d = 0; d < Math.min(days + 1, 3); d++) {
      const date = new Date(now)
      date.setDate(date.getDate() + d)
      const dateStr = date.toISOString().split('T')[0]
      
      const fixtures = await fetchFixturesFromAPI(dateStr)
      console.log(`[suggestions] Date ${dateStr}: ${fixtures.length} fixtures found`)
      allFixtures.push(...fixtures)
      
      // Se já temos jogos suficientes, parar
      if (allFixtures.length >= limit * 2) break
    }
    
    // Filtrar apenas jogos FUTUROS com status NS (Not Started)
    const futureFixtures = allFixtures.filter(f => {
      const kickoff = new Date(f.fixture.date)
      const status = f.fixture.status.short
      
      // Deve ser status NS (Not Started)
      if (status !== 'NS') {
        filteredStatus++
        return false
      }
      
      // Deve ser no futuro
      if (kickoff <= now) {
        filteredPast++
        return false
      }
      
      return true
    })
    
    console.log(`[suggestions] Filtered: ${filteredPast} past, ${filteredStatus} non-NS. Remaining: ${futureFixtures.length}`)
    
    // Mapear para formato de sugestão com tier
    const suggestions: Suggestion[] = futureFixtures.map(f => {
      const leagueInfo = LEAGUE_PRIORITY[f.league.id] || { tier: 5, name: f.league.name, shortName: f.league.name }
      const kickoffDate = new Date(f.fixture.date)
      
      return {
        label: `${f.teams.home.name} x ${f.teams.away.name}`,
        query: `${f.teams.home.name} x ${f.teams.away.name}`,
        league: leagueInfo.shortName,
        kickoffAt: f.fixture.date,
        kickoffDisplay: formatKickoffDisplay(kickoffDate, now),
        tier: leagueInfo.tier
      }
    })
    
    // Ordenar por: tier (menor primeiro), depois por kickoff (mais próximo primeiro)
    suggestions.sort((a, b) => {
      if (a.tier !== b.tier) return a.tier - b.tier
      return new Date(a.kickoffAt).getTime() - new Date(b.kickoffAt).getTime()
    })
    
    // Limitar resultado
    const result = suggestions.slice(0, limit)
    
    console.log(`[suggestions] Returning ${result.length} suggestions`)
    
    if (result.length === 0) {
      return NextResponse.json({
        generatedAt,
        items: FALLBACK_SUGGESTIONS,
        source: 'fallback',
        stats: { total: allFixtures.length, filteredPast, filteredStatus, future: 0 }
      }, {
        headers: { 'Cache-Control': 'no-store, max-age=0' }
      })
    }
    
    return NextResponse.json({
      generatedAt,
      items: result,
      source: 'api',
      stats: { total: allFixtures.length, filteredPast, filteredStatus, future: futureFixtures.length }
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
