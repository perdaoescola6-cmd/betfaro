import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'
import { settleBet, FixtureData } from '@/lib/settleBet'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY!

/**
 * POST /api/bets/resolve
 * Resolves pending bets by fetching fixture data and applying settlement logic
 * 
 * Can be called:
 * - Manually by admin
 * - By a cron job
 * - After a fixture ends
 */
export async function POST(request: NextRequest) {
  try {
    const supabase = createClient(supabaseUrl, supabaseServiceKey)
    
    const body = await request.json().catch(() => ({}))
    const { fixtureId, forceResolve } = body

    // Get pending bets (optionally filtered by fixture_id)
    let query = supabase
      .from('bets')
      .select('id, fixture_id, market, user_id, odds, stake')
      .eq('status', 'pending')

    if (fixtureId) {
      query = query.eq('fixture_id', fixtureId)
    }

    const { data: pendingBets, error: fetchError } = await query

    if (fetchError) {
      console.error('Error fetching pending bets:', fetchError)
      return NextResponse.json({ error: 'Failed to fetch pending bets' }, { status: 500 })
    }

    if (!pendingBets || pendingBets.length === 0) {
      return NextResponse.json({ message: 'No pending bets to resolve', resolved: 0 })
    }

    // Group bets by fixture_id
    const betsByFixture: Record<string, typeof pendingBets> = {}
    for (const bet of pendingBets) {
      if (bet.fixture_id) {
        if (!betsByFixture[bet.fixture_id]) {
          betsByFixture[bet.fixture_id] = []
        }
        betsByFixture[bet.fixture_id].push(bet)
      }
    }

    const results: Array<{ betId: string; oldStatus: string; newStatus: string; fixtureId: string }> = []
    const errors: Array<{ fixtureId: string; error: string }> = []

    // Process each fixture
    for (const [fId, bets] of Object.entries(betsByFixture)) {
      try {
        // Fetch fixture data from API-Football
        const fixtureData = await fetchFixtureData(fId)
        
        if (!fixtureData) {
          errors.push({ fixtureId: fId, error: 'Could not fetch fixture data' })
          continue
        }

        // Settle each bet for this fixture
        for (const bet of bets) {
          const newStatus = settleBet(bet.market, fixtureData)
          
          // Only update if status changed from pending
          if (newStatus !== 'pending' || forceResolve) {
            const updateData: Record<string, any> = {
              status: newStatus,
              result_updated_at: new Date().toISOString()
            }

            // Calculate profit/loss if resolved
            if (newStatus === 'won' && bet.stake) {
              updateData.profit_loss = bet.stake * (bet.odds - 1)
            } else if (newStatus === 'lost' && bet.stake) {
              updateData.profit_loss = -bet.stake
            } else if (newStatus === 'void' && bet.stake) {
              updateData.profit_loss = 0
            }

            const { error: updateError } = await supabase
              .from('bets')
              .update(updateData)
              .eq('id', bet.id)

            if (updateError) {
              console.error(`Error updating bet ${bet.id}:`, updateError)
            } else {
              results.push({
                betId: bet.id,
                oldStatus: 'pending',
                newStatus,
                fixtureId: fId
              })
            }
          }
        }
      } catch (err) {
        console.error(`Error processing fixture ${fId}:`, err)
        errors.push({ fixtureId: fId, error: String(err) })
      }
    }

    return NextResponse.json({
      message: `Resolved ${results.length} bets`,
      resolved: results.length,
      results,
      errors: errors.length > 0 ? errors : undefined
    })

  } catch (error) {
    console.error('Error in bet resolution:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}

/**
 * Fetch fixture data from API-Football
 */
async function fetchFixtureData(fixtureId: string): Promise<FixtureData | null> {
  const apiKey = process.env.FOOTBALL_API_KEY
  
  if (!apiKey) {
    console.error('FOOTBALL_API_KEY not configured')
    return null
  }

  try {
    // Fetch fixture details
    const fixtureResponse = await fetch(
      `https://v3.football.api-sports.io/fixtures?id=${fixtureId}`,
      {
        headers: {
          'x-apisports-key': apiKey
        }
      }
    )

    if (!fixtureResponse.ok) {
      console.error('Failed to fetch fixture:', fixtureResponse.status)
      return null
    }

    const fixtureJson = await fixtureResponse.json()
    const fixture = fixtureJson.response?.[0]

    if (!fixture) {
      console.error('Fixture not found:', fixtureId)
      return null
    }

    // Build fixture data object
    const fixtureData: FixtureData = {
      status: {
        short: fixture.fixture?.status?.short || 'NS'
      },
      goals: {
        home: fixture.goals?.home ?? null,
        away: fixture.goals?.away ?? null
      },
      score: {
        halftime: {
          home: fixture.score?.halftime?.home ?? null,
          away: fixture.score?.halftime?.away ?? null
        }
      }
    }

    // Try to get corners from statistics if needed
    // Check if any pending bets need corners data
    const needsCorners = true // Could optimize by checking bet markets

    if (needsCorners) {
      try {
        const statsResponse = await fetch(
          `https://v3.football.api-sports.io/fixtures/statistics?fixture=${fixtureId}`,
          {
            headers: {
              'x-apisports-key': apiKey
            }
          }
        )

        if (statsResponse.ok) {
          const statsJson = await statsResponse.json()
          const stats = statsJson.response

          if (stats && stats.length >= 2) {
            let homeCorners = 0
            let awayCorners = 0

            // Find corner kicks in home team stats
            const homeStats = stats[0]?.statistics || []
            const awayStats = stats[1]?.statistics || []

            for (const stat of homeStats) {
              if (stat.type === 'Corner Kicks') {
                homeCorners = parseInt(stat.value) || 0
                break
              }
            }

            for (const stat of awayStats) {
              if (stat.type === 'Corner Kicks') {
                awayCorners = parseInt(stat.value) || 0
                break
              }
            }

            fixtureData.corners = {
              home: homeCorners,
              away: awayCorners,
              total: homeCorners + awayCorners
            }
          }
        }
      } catch (statsError) {
        console.error('Error fetching statistics:', statsError)
        // Continue without corners data
      }
    }

    return fixtureData

  } catch (error) {
    console.error('Error fetching fixture data:', error)
    return null
  }
}

/**
 * GET /api/bets/resolve
 * Get resolution status / stats
 */
export async function GET() {
  try {
    const supabase = createClient(supabaseUrl, supabaseServiceKey)

    const { data: stats, error } = await supabase
      .from('bets')
      .select('status')

    if (error) {
      return NextResponse.json({ error: 'Failed to fetch stats' }, { status: 500 })
    }

    const counts = {
      total: stats?.length || 0,
      pending: stats?.filter(b => b.status === 'pending').length || 0,
      won: stats?.filter(b => b.status === 'won').length || 0,
      lost: stats?.filter(b => b.status === 'lost').length || 0,
      void: stats?.filter(b => b.status === 'void').length || 0
    }

    return NextResponse.json({ counts })

  } catch (error) {
    console.error('Error getting resolution stats:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
