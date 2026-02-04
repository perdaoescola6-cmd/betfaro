import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import { v4 as uuidv4 } from 'uuid'

export const runtime = 'nodejs'

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000'
const INTERNAL_API_KEY = process.env.INTERNAL_API_KEY || 'betfaro_internal_2024'
const TIMEOUT_MS = 30000 // 30 seconds

interface ChatResponse {
  ok: boolean
  reply?: string
  error?: {
    code: 'UPSTREAM_DOWN' | 'BAD_REQUEST' | 'UNAUTHORIZED' | 'RATE_LIMIT' | 'NO_SUBSCRIPTION' | 'UNKNOWN'
    message: string
  }
  debugId: string
}

export async function POST(request: NextRequest): Promise<NextResponse<ChatResponse>> {
  const debugId = uuidv4()
  const startTime = Date.now()
  
  console.log(`[${debugId}] Chat request started`)
  
  try {
    // 1. Authenticate user
    const supabase = await createClient()
    const { data: { user }, error: authError } = await supabase.auth.getUser()

    if (authError || !user) {
      console.log(`[${debugId}] Auth failed: ${authError?.message || 'No user'}`)
      return NextResponse.json(
        { ok: false, error: { code: 'UNAUTHORIZED', message: 'Faça login para usar o chat' }, debugId },
        { status: 401 }
      )
    }

    // 2. Check subscription in Supabase
    const { data: subscription } = await supabase
      .from('subscriptions')
      .select('plan, status')
      .eq('user_id', user.id)
      .maybeSingle()

    const hasActiveSubscription = subscription && subscription.status === 'active'
    const userPlan = subscription?.plan || 'free'
    
    console.log(`[${debugId}] User ${user.email} plan=${userPlan} hasSubscription=${hasActiveSubscription}`)

    if (!hasActiveSubscription) {
      return NextResponse.json(
        { ok: false, error: { code: 'NO_SUBSCRIPTION', message: 'Assinatura ativa necessária. Acesse a página de Planos.' }, debugId },
        { status: 403 }
      )
    }

    // 3. Parse request body
    let body: { content?: string; message?: string }
    try {
      body = await request.json()
    } catch {
      return NextResponse.json(
        { ok: false, error: { code: 'BAD_REQUEST', message: 'JSON inválido' }, debugId },
        { status: 400 }
      )
    }

    const message = body.content || body.message
    if (!message || typeof message !== 'string' || message.trim().length === 0) {
      return NextResponse.json(
        { ok: false, error: { code: 'BAD_REQUEST', message: 'Mensagem não pode estar vazia' }, debugId },
        { status: 400 }
      )
    }

    // 4. Forward to backend with timeout
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_MS)

    try {
      console.log(`[${debugId}] Calling backend: ${BACKEND_URL}/api/internal/chat`)
      
      const backendResponse = await fetch(
        `${BACKEND_URL}/api/internal/chat`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Internal-Key': INTERNAL_API_KEY,
            'X-User-Id': user.id,
            'X-User-Email': user.email || '',
            'X-User-Plan': userPlan,
            'X-Has-Subscription': 'true',
            'X-Debug-Id': debugId,
          },
          body: JSON.stringify({ content: message.trim() }),
          signal: controller.signal,
        }
      )

      clearTimeout(timeoutId)
      
      const elapsed = Date.now() - startTime
      console.log(`[${debugId}] Backend responded: status=${backendResponse.status} elapsed=${elapsed}ms`)

      if (!backendResponse.ok) {
        const errorData = await backendResponse.json().catch(() => ({ detail: 'Erro desconhecido' }))
        const errorMessage = errorData.detail || 'Erro ao processar mensagem'
        
        // Map status codes to error codes
        let errorCode: ChatResponse['error']['code'] = 'UNKNOWN'
        if (backendResponse.status === 401) errorCode = 'UNAUTHORIZED'
        else if (backendResponse.status === 403) errorCode = 'NO_SUBSCRIPTION'
        else if (backendResponse.status === 429) errorCode = 'RATE_LIMIT'
        else if (backendResponse.status >= 500) errorCode = 'UPSTREAM_DOWN'
        
        return NextResponse.json(
          { ok: false, error: { code: errorCode, message: errorMessage }, debugId },
          { status: backendResponse.status }
        )
      }

      const data = await backendResponse.json()
      
      return NextResponse.json({
        ok: true,
        reply: data.response || data.reply || 'Resposta recebida',
        debugId
      })

    } catch (fetchError) {
      clearTimeout(timeoutId)
      
      if (fetchError instanceof Error && fetchError.name === 'AbortError') {
        console.error(`[${debugId}] Backend timeout after ${TIMEOUT_MS}ms`)
        return NextResponse.json(
          { ok: false, error: { code: 'UPSTREAM_DOWN', message: 'Servidor demorou muito para responder. Tente novamente.' }, debugId },
          { status: 504 }
        )
      }
      
      console.error(`[${debugId}] Backend fetch error:`, fetchError)
      return NextResponse.json(
        { ok: false, error: { code: 'UPSTREAM_DOWN', message: 'Servidor do BetFaro indisponível. Tente novamente em instantes.' }, debugId },
        { status: 502 }
      )
    }

  } catch (error) {
    console.error(`[${debugId}] Unexpected error:`, error)
    return NextResponse.json(
      { ok: false, error: { code: 'UNKNOWN', message: 'Erro interno. Tente novamente.' }, debugId },
      { status: 500 }
    )
  }
}
