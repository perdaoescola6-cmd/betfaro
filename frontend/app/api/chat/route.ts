import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000'
const INTERNAL_API_KEY = process.env.INTERNAL_API_KEY || 'betfaro_internal_2024'

export async function POST(request: NextRequest) {
  try {
    const supabase = await createClient()
    const { data: { user } } = await supabase.auth.getUser()

    if (!user) {
      return NextResponse.json(
        { detail: 'Not authenticated' },
        { status: 401 }
      )
    }

    const body = await request.json()

    // Forward request to backend
    const backendResponse = await fetch(
      `${BACKEND_URL}/api/chat`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Internal-Key': INTERNAL_API_KEY,
          'X-User-Id': user.id,
          'X-User-Email': user.email || '',
        },
        body: JSON.stringify(body),
      }
    )

    if (!backendResponse.ok) {
      const errorData = await backendResponse.json().catch(() => ({}))
      return NextResponse.json(
        { detail: errorData.detail || 'Erro ao processar mensagem' },
        { status: backendResponse.status }
      )
    }

    const data = await backendResponse.json()
    return NextResponse.json(data)

  } catch (error) {
    console.error('Error in chat API:', error)
    return NextResponse.json(
      { detail: 'Erro de conexão. Verifique sua internet e tente novamente.' },
      { status: 500 }
    )
  }
}
