import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'
import { settleBet, FixtureData } from '@/lib/settleBet'

// Force dynamic, no caching
export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY!
const CRON_SECRET = process.env.CRON_SECRET
const FOOTBALL_API_KEY = process.env.FOOTBALL_API_KEY

const BATCH_LIMIT = 50
const LOCK_TTL_MINUTES = 9
const FETCH_TIMEOUT_MS = 10000
const MAX_CONCURRENT_FIXTURES = 5

interface RunStats {
  runId: string
  found: number
  processed: number
  resolved: number
  skipped: number
  errors: number
  durationMs: number
  details: Array<{ betId: string; fixtureId: string; market: string; newStatus: string }>
  errorDetails: Array<{ fixtureId: string; error: string }>
  notes: Record<string, any>
}

/**
 * POST /api/bets/resolve
 * Vercel Cron job to resolve pending bets
 * Protected by CRON_SECRET
 * 
 * IMPORTANT: This endpoint ALWAYS logs to resolve_runs table,
 * even on errors or when no bets are found.
 */
export async function POST(request: NextRequest) {
  const startTime = Date.now()
  const runId = crypto.randomUUID()
  
  // Initialize Supabase with service role key (REQUIRED for admin operations)
  const supabase = createClient(supabaseUrl, supabaseServiceKey)
  
  const stats: RunStats = {
    runId,
    found: 0,
    processed: 0,
    resolved: 0,
    skipped: 0,
    errors: 0,
    durationMs: 0,
    details: [],
    errorDetails: [],
    notes: {
      source: 'github_actions',
      env: process.env.NODE_ENV || 'unknown'
    }
  }

  console.log(`[${runId}] 🚀 Bet resolver started`)

  try {
    // 1. Validate authorization
    const authHeader = request.headers.get('authorization')
    const authToken = authHeader?.replace('Bearer ', '')
    
    // Also check for Vercel Cron header (automatically added by Vercel)
    const isVercelCron = request.headers.get('x-vercel-cron') === '1'
    
    if (!isVercelCron && authToken !== CRON_SECRET) {
      console.log(`[${runId}] ❌ Unauthorized request`)
      stats.notes.error = 'Unauthorized'
      // Still log the attempt
      stats.durationMs = Date.now() - startTime
      await logRunGuaranteed(supabase, stats)
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    // 2. Acquire lock to prevent concurrent executions
    const lockAcquired = await acquireLock(supabase, runId)
    if (!lockAcquired) {
      console.log(`[${runId}] ⏭️ Skipped - another instance is running`)
      stats.notes.skipped = 'locked'
      stats.durationMs = Date.now() - startTime
      await logRunGuaranteed(supabase, stats)
      return NextResponse.json({ 
        ok: true, 
        skipped: 'locked',
        runId,
        message: 'Another resolver instance is currently running'
      })
    }

    try {
      // 3. Fetch pending bets with optimized query
      const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000).toISOString()
      
      const { data: pendingBets, error: fetchError } = await supabase
        .from('bets')
        .select('id, fixture_id, market, user_id, odds, stake, status, kickoff_at, created_at')
        .eq('status', 'pending')
        .not('fixture_id', 'is', null)
        .or(`kickoff_at.lte.${fiveMinutesAgo},kickoff_at.is.null`)
        .order('kickoff_at', { ascending: true, nullsFirst: false })
        .limit(BATCH_LIMIT)

      if (fetchError) {
        console.error(`[${runId}] ❌ Error fetching bets:`, fetchError)
        stats.notes.fetchError = fetchError.message
        throw new Error('Failed to fetch pending bets')
      }

      stats.found = pendingBets?.length || 0
      console.log(`[${runId}] 📊 Found ${stats.found} pending bets`)

      if (!pendingBets || pendingBets.length === 0) {
        stats.notes.message = 'No pending bets to resolve'
        // Don't return early - let finally block handle logging
      }

      // 4. Group bets by fixture_id
      const betsByFixture: Record<string, typeof pendingBets> = {}
      for (const bet of pendingBets) {
        if (bet.fixture_id) {
          if (!betsByFixture[bet.fixture_id]) {
            betsByFixture[bet.fixture_id] = []
          }
          betsByFixture[bet.fixture_id].push(bet)
        }
      }

      const fixtureIds = Object.keys(betsByFixture)
      console.log(`[${runId}] 🎯 Processing ${fixtureIds.length} unique fixtures`)

      // 5. Fetch fixture data with caching and concurrency limit
      const fixtureCache = new Map<string, FixtureData | null>()
      
      // Process fixtures in batches to limit concurrency
      for (let i = 0; i < fixtureIds.length; i += MAX_CONCURRENT_FIXTURES) {
        const batch = fixtureIds.slice(i, i + MAX_CONCURRENT_FIXTURES)
        const promises = batch.map(async (fId) => {
          try {
            const data = await fetchFixtureDataWithTimeout(fId)
            fixtureCache.set(fId, data)
          } catch (err) {
            console.error(`[${runId}] ⚠️ Failed to fetch fixture ${fId}:`, err)
            fixtureCache.set(fId, null)
            stats.errorDetails.push({ fixtureId: fId, error: String(err) })
          }
        })
        await Promise.all(promises)
      }

      // 6. Process each bet
      for (const [fixtureId, bets] of Object.entries(betsByFixture)) {
        const fixtureData = fixtureCache.get(fixtureId)
        
        if (!fixtureData) {
          stats.errors += bets.length
          continue
        }

        for (const bet of bets) {
          stats.processed++
          
          try {
            // Re-check status to ensure idempotency
            const { data: currentBet } = await supabase
              .from('bets')
              .select('status')
              .eq('id', bet.id)
              .single()

            if (currentBet?.status !== 'pending') {
              stats.skipped++
              console.log(`[${runId}] ⏭️ Bet ${bet.id} already resolved (${currentBet?.status})`)
              continue
            }

            // Apply settlement logic
            const newStatus = settleBet(bet.market, fixtureData)

            if (newStatus === 'pending') {
              stats.skipped++
              continue
            }

            // Calculate profit/loss
            const updateData: Record<string, any> = {
              status: newStatus,
              result_updated_at: new Date().toISOString()
            }

            if (bet.stake) {
              if (newStatus === 'won') {
                updateData.profit_loss = bet.stake * (bet.odds - 1)
              } else if (newStatus === 'lost') {
                updateData.profit_loss = -bet.stake
              } else if (newStatus === 'void') {
                updateData.profit_loss = 0
              }
            }

            // Update bet
            const { error: updateError } = await supabase
              .from('bets')
              .update(updateData)
              .eq('id', bet.id)
              .eq('status', 'pending') // Extra safety check

            if (updateError) {
              console.error(`[${runId}] ❌ Error updating bet ${bet.id}:`, updateError)
              stats.errors++
            } else {
              stats.resolved++
              stats.details.push({
                betId: bet.id,
                fixtureId,
                market: bet.market,
                newStatus
              })
              console.log(`[${runId}] ✅ Bet ${bet.id} resolved: ${newStatus}`)
            }
          } catch (err) {
            console.error(`[${runId}] ❌ Error processing bet ${bet.id}:`, err)
            stats.errors++
          }
        }
      }

      stats.durationMs = Date.now() - startTime
      await logRunGuaranteed(supabase, stats)
      
      console.log(`[${runId}] 🏁 Completed in ${stats.durationMs}ms - Resolved: ${stats.resolved}, Skipped: ${stats.skipped}, Errors: ${stats.errors}`)

      return NextResponse.json({
        ok: true,
        runId,
        found: stats.found,
        processed: stats.processed,
        resolved: stats.resolved,
        skipped: stats.skipped,
        errors: stats.errors,
        durationMs: stats.durationMs,
        details: stats.details.slice(0, 10), // Limit response size
        errorDetails: stats.errorDetails.slice(0, 5)
      })

    } finally {
      await releaseLock(supabase)
    }

  } catch (error) {
    stats.durationMs = Date.now() - startTime
    stats.notes.fatalError = error instanceof Error ? error.message : String(error)
    console.error(`[${runId}] 💥 Fatal error:`, error)
    
    // ALWAYS log to resolve_runs, even on fatal errors
    await logRunGuaranteed(supabase, stats)
    
    return NextResponse.json({ 
      ok: false,
      runId,
      error: 'Internal server error',
      durationMs: stats.durationMs
    }, { status: 500 })
  }
}

/**
 * Acquire distributed lock
 */
async function acquireLock(supabase: any, runId: string): Promise<boolean> {
  const lockKey = 'bets_resolve'
  const now = new Date()
  const expiresAt = new Date(now.getTime() + LOCK_TTL_MINUTES * 60 * 1000)

  try {
    // Try to get existing lock
    const { data: existingLock } = await supabase
      .from('locks')
      .select('*')
      .eq('key', lockKey)
      .single()

    if (existingLock) {
      // Check if lock is expired
      if (new Date(existingLock.expires_at) > now) {
        return false // Lock is still valid
      }
      
      // Lock expired, update it
      const { error } = await supabase
        .from('locks')
        .update({ 
          run_id: runId, 
          acquired_at: now.toISOString(),
          expires_at: expiresAt.toISOString()
        })
        .eq('key', lockKey)
        .lt('expires_at', now.toISOString())

      return !error
    }

    // No lock exists, create one
    const { error } = await supabase
      .from('locks')
      .insert({
        key: lockKey,
        run_id: runId,
        acquired_at: now.toISOString(),
        expires_at: expiresAt.toISOString()
      })

    return !error
  } catch (err) {
    console.error('Lock acquisition error:', err)
    return true // On error, proceed anyway (fail open)
  }
}

/**
 * Release lock
 */
async function releaseLock(supabase: any): Promise<void> {
  try {
    await supabase
      .from('locks')
      .delete()
      .eq('key', 'bets_resolve')
  } catch (err) {
    console.error('Lock release error:', err)
  }
}

/**
 * Log run to database - GUARANTEED to complete
 * This function will retry and never throw, ensuring every run is logged
 */
async function logRunGuaranteed(supabase: any, stats: RunStats): Promise<void> {
  const maxRetries = 3
  
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      const { error } = await supabase
        .from('resolve_runs')
        .insert({
          id: stats.runId,
          found: stats.found,
          processed: stats.processed,
          resolved: stats.resolved,
          skipped: stats.skipped,
          errors: stats.errors,
          duration_ms: stats.durationMs,
          notes: {
            ...stats.notes,
            details: stats.details.slice(0, 20),
            errorDetails: stats.errorDetails
          }
        })
      
      if (error) {
        console.error(`[${stats.runId}] ⚠️ Failed to log run (attempt ${attempt}/${maxRetries}):`, error)
        if (attempt === maxRetries) {
          console.error(`[${stats.runId}] ❌ CRITICAL: Could not log run after ${maxRetries} attempts`)
        }
        continue
      }
      
      console.log(`[${stats.runId}] 📝 Run logged to resolve_runs`)
      return
    } catch (err) {
      console.error(`[${stats.runId}] ⚠️ Exception logging run (attempt ${attempt}/${maxRetries}):`, err)
      if (attempt < maxRetries) {
        await new Promise(r => setTimeout(r, 500 * attempt)) // Exponential backoff
      }
    }
  }
}

/**
 * Fetch fixture data with timeout
 */
async function fetchFixtureDataWithTimeout(fixtureId: string): Promise<FixtureData | null> {
  if (!FOOTBALL_API_KEY) {
    console.error('FOOTBALL_API_KEY not configured')
    return null
  }

  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS)

  try {
    const fixtureResponse = await fetch(
      `https://v3.football.api-sports.io/fixtures?id=${fixtureId}`,
      {
        headers: { 'x-apisports-key': FOOTBALL_API_KEY },
        signal: controller.signal
      }
    )

    if (!fixtureResponse.ok) {
      return null
    }

    const fixtureJson = await fixtureResponse.json()
    const fixture = fixtureJson.response?.[0]

    if (!fixture) {
      return null
    }

    const fixtureData: FixtureData = {
      status: { short: fixture.fixture?.status?.short || 'NS' },
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

    // Fetch corners if needed (separate request with timeout)
    try {
      const statsController = new AbortController()
      const statsTimeout = setTimeout(() => statsController.abort(), FETCH_TIMEOUT_MS)

      const statsResponse = await fetch(
        `https://v3.football.api-sports.io/fixtures/statistics?fixture=${fixtureId}`,
        {
          headers: { 'x-apisports-key': FOOTBALL_API_KEY },
          signal: statsController.signal
        }
      )

      clearTimeout(statsTimeout)

      if (statsResponse.ok) {
        const statsJson = await statsResponse.json()
        const stats = statsJson.response

        if (stats?.length >= 2) {
          let homeCorners = 0
          let awayCorners = 0

          for (const stat of stats[0]?.statistics || []) {
            if (stat.type === 'Corner Kicks') {
              homeCorners = parseInt(stat.value) || 0
              break
            }
          }

          for (const stat of stats[1]?.statistics || []) {
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
    } catch {
      // Continue without corners
    }

    return fixtureData
  } catch (err) {
    if ((err as Error).name === 'AbortError') {
      console.error(`Timeout fetching fixture ${fixtureId}`)
    }
    return null
  } finally {
    clearTimeout(timeout)
  }
}

/**
 * GET /api/bets/resolve
 * Get resolution stats (protected)
 */
export async function GET(request: NextRequest) {
  const authHeader = request.headers.get('authorization')
  const authToken = authHeader?.replace('Bearer ', '')
  
  if (authToken !== CRON_SECRET) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  try {
    const supabase = createClient(supabaseUrl, supabaseServiceKey)

    const { data: bets } = await supabase
      .from('bets')
      .select('status')

    const { data: recentRuns } = await supabase
      .from('resolve_runs')
      .select('*')
      .order('created_at', { ascending: false })
      .limit(5)

    const counts = {
      total: bets?.length || 0,
      pending: bets?.filter(b => b.status === 'pending').length || 0,
      won: bets?.filter(b => b.status === 'won').length || 0,
      lost: bets?.filter(b => b.status === 'lost').length || 0,
      void: bets?.filter(b => b.status === 'void').length || 0
    }

    return NextResponse.json({ counts, recentRuns })
  } catch (error) {
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
