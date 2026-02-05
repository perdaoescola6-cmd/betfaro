import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

// Market options for validation
const VALID_MARKETS = [
  'over_0_5', 'over_1_5', 'over_2_5', 'over_3_5',
  'under_0_5', 'under_1_5', 'under_2_5', 'under_3_5',
  'btts_yes', 'btts_no',
  '1x2_home', '1x2_draw', '1x2_away',
  'dc_1x', 'dc_x2', 'dc_12',
  'ht_over_0_5', 'ht_over_1_5',
  'corners_over_8_5', 'corners_over_9_5', 'corners_over_10_5',
  'cards_over_3_5', 'cards_over_4_5',
  'other'
]

export async function POST(request: NextRequest) {
  try {
    const supabase = await createClient()
    
    const { data: { user }, error: authError } = await supabase.auth.getUser()
    
    if (authError || !user) {
      return NextResponse.json(
        { error: 'Não autorizado' },
        { status: 401 }
      )
    }

    const body = await request.json()
    const {
      source,
      homeTeam,
      awayTeam,
      fixtureId,
      league,
      market,
      odds,
      stake,
      note,
      botReco,
      valueFlag,
      kickoffAt
    } = body

    // Validations
    if (!homeTeam || !awayTeam) {
      return NextResponse.json(
        { error: 'Times são obrigatórios' },
        { status: 400 }
      )
    }

    if (!market) {
      return NextResponse.json(
        { error: 'Mercado é obrigatório' },
        { status: 400 }
      )
    }

    if (!odds || odds < 1.01) {
      return NextResponse.json(
        { error: 'Odd deve ser >= 1.01' },
        { status: 400 }
      )
    }

    if (!['chat', 'daily_picks', 'manual'].includes(source)) {
      return NextResponse.json(
        { error: 'Source inválido' },
        { status: 400 }
      )
    }

    // Insert bet
    const { data: bet, error: insertError } = await supabase
      .from('bets')
      .insert({
        user_id: user.id,
        source,
        home_team: homeTeam,
        away_team: awayTeam,
        fixture_id: fixtureId || null,
        league: league || null,
        market,
        odds: parseFloat(odds),
        stake: stake ? parseFloat(stake) : null,
        note: note || null,
        bot_reco: botReco || null,
        value_flag: valueFlag || false,
        kickoff_at: kickoffAt || null,
        status: 'pending'
      })
      .select('id')
      .single()

    if (insertError) {
      console.error('Error inserting bet:', insertError)
      return NextResponse.json(
        { error: 'Erro ao salvar aposta' },
        { status: 500 }
      )
    }

    // Also record the action
    await supabase
      .from('bet_actions')
      .insert({
        user_id: user.id,
        action: 'entered',
        source,
        home_team: homeTeam,
        away_team: awayTeam,
        fixture_id: fixtureId || null,
        suggested_market: market,
        metadata: { odds, stake, botReco }
      })

    return NextResponse.json({
      ok: true,
      betId: bet.id
    })

  } catch (error) {
    console.error('Error in POST /api/bets:', error)
    return NextResponse.json(
      { error: 'Erro interno' },
      { status: 500 }
    )
  }
}

export async function GET(request: NextRequest) {
  try {
    const supabase = await createClient()
    
    const { data: { user }, error: authError } = await supabase.auth.getUser()
    
    if (authError || !user) {
      return NextResponse.json(
        { error: 'Não autorizado' },
        { status: 401 }
      )
    }

    const { searchParams } = new URL(request.url)
    const status = searchParams.get('status')
    const limit = parseInt(searchParams.get('limit') || '50')

    let query = supabase
      .from('bets')
      .select('*')
      .eq('user_id', user.id)
      .order('created_at', { ascending: false })
      .limit(limit)

    if (status) {
      query = query.eq('status', status)
    }

    const { data: bets, error } = await query

    if (error) {
      console.error('Error fetching bets:', error)
      return NextResponse.json(
        { error: 'Erro ao buscar apostas' },
        { status: 500 }
      )
    }

    // Calculate stats
    const total = bets?.length || 0
    const pending = bets?.filter(b => b.status === 'pending').length || 0
    const won = bets?.filter(b => b.status === 'won').length || 0
    const lost = bets?.filter(b => b.status === 'lost').length || 0
    const resolved = won + lost
    const winrate = resolved > 0 ? (won / resolved) * 100 : 0
    const valueBets = bets?.filter(b => b.value_flag).length || 0

    // Calculate ROI: (SUM(profit_loss) / SUM(stake)) * 100
    // Only consider bets with status 'won' or 'lost' and valid stake
    const betsWithStake = bets?.filter(b => 
      ['won', 'lost'].includes(b.status) && 
      b.stake && 
      b.stake > 0
    ) || []
    
    let totalStake = 0
    let totalProfitLoss = 0
    
    for (const bet of betsWithStake) {
      totalStake += bet.stake
      // If profit_loss is stored in DB, use it; otherwise calculate
      if (bet.profit_loss !== null && bet.profit_loss !== undefined) {
        totalProfitLoss += bet.profit_loss
      } else {
        // Calculate profit/loss based on status
        if (bet.status === 'won') {
          totalProfitLoss += bet.stake * (bet.odds - 1)
        } else if (bet.status === 'lost') {
          totalProfitLoss -= bet.stake
        }
      }
    }
    
    const roi = totalStake > 0 ? (totalProfitLoss / totalStake) * 100 : 0

    // Calculate streak
    let streak = 0
    const resolvedBets = bets?.filter(b => ['won', 'lost'].includes(b.status)) || []
    for (const bet of resolvedBets) {
      if (bet.status === 'won') {
        streak++
      } else {
        break
      }
    }

    return NextResponse.json({
      bets,
      stats: {
        total,
        pending,
        won,
        lost,
        winrate: Math.round(winrate * 10) / 10,
        streak,
        valueBets,
        roi: Math.round(roi * 10) / 10,
        totalStake: Math.round(totalStake * 100) / 100,
        totalProfitLoss: Math.round(totalProfitLoss * 100) / 100
      }
    })

  } catch (error) {
    console.error('Error in GET /api/bets:', error)
    return NextResponse.json(
      { error: 'Erro interno' },
      { status: 500 }
    )
  }
}
