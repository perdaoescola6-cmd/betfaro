import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

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
      suggestedMarket,
      metadata
    } = body

    // Validations
    if (!homeTeam || !awayTeam) {
      return NextResponse.json(
        { error: 'Times são obrigatórios' },
        { status: 400 }
      )
    }

    if (!['chat', 'daily_picks'].includes(source)) {
      return NextResponse.json(
        { error: 'Source inválido' },
        { status: 400 }
      )
    }

    // Insert skip action
    const { error: insertError } = await supabase
      .from('bet_actions')
      .insert({
        user_id: user.id,
        action: 'skipped',
        source,
        home_team: homeTeam,
        away_team: awayTeam,
        fixture_id: fixtureId || null,
        suggested_market: suggestedMarket || null,
        metadata: metadata || null
      })

    if (insertError) {
      console.error('Error inserting skip action:', insertError)
      return NextResponse.json(
        { error: 'Erro ao registrar ação' },
        { status: 500 }
      )
    }

    return NextResponse.json({
      ok: true,
      message: 'Registrado como pulado'
    })

  } catch (error) {
    console.error('Error in POST /api/bets/skip:', error)
    return NextResponse.json(
      { error: 'Erro interno' },
      { status: 500 }
    )
  }
}
