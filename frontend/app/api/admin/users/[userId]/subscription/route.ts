import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import { createAdminClient } from '@/lib/supabase/admin'

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ userId: string }> }
) {
  try {
    const { userId } = await params
    const supabase = await createClient()
    
    // Get authenticated user
    const { data: { user }, error: authError } = await supabase.auth.getUser()
    
    if (authError || !user) {
      return NextResponse.json(
        { error: 'Não autorizado' },
        { status: 401 }
      )
    }

    // Check if user is admin
    const { data: profile } = await supabase
      .from('profiles')
      .select('role')
      .eq('id', user.id)
      .single()

    if (profile?.role !== 'admin') {
      return NextResponse.json(
        { error: 'Acesso negado. Apenas administradores.' },
        { status: 403 }
      )
    }

    const { plan, status } = await request.json()

    // Validate plan
    const validPlans = ['free', 'pro', 'elite']
    if (plan && !validPlans.includes(plan)) {
      return NextResponse.json(
        { error: `Plano inválido. Use: ${validPlans.join(', ')}` },
        { status: 400 }
      )
    }

    // Validate status
    const validStatuses = ['active', 'trialing', 'past_due', 'canceled', 'incomplete']
    if (status && !validStatuses.includes(status)) {
      return NextResponse.json(
        { error: `Status inválido. Use: ${validStatuses.join(', ')}` },
        { status: 400 }
      )
    }

    // Use admin client to update subscription
    const adminSupabase = createAdminClient()

    // Build update object
    const updateData: any = {
      provider: 'manual',
      updated_at: new Date().toISOString(),
    }

    if (plan) updateData.plan = plan
    if (status) updateData.status = status

    // If setting to free, also set status to active
    if (plan === 'free') {
      updateData.status = 'active'
      updateData.current_period_end = null
    }

    // If activating a paid plan manually, set period end to 30 days
    if (plan && plan !== 'free' && (!status || status === 'active')) {
      updateData.status = 'active'
      updateData.current_period_end = new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString()
    }

    const { data, error } = await adminSupabase
      .from('subscriptions')
      .upsert({
        user_id: userId,
        ...updateData,
      })
      .select()
      .single()

    if (error) {
      console.error('Error updating subscription:', error)
      return NextResponse.json(
        { error: 'Erro ao atualizar assinatura' },
        { status: 500 }
      )
    }

    return NextResponse.json({
      message: 'Assinatura atualizada com sucesso',
      subscription: data,
    })
  } catch (error) {
    console.error('Admin subscription update error:', error)
    return NextResponse.json(
      { error: 'Erro interno do servidor' },
      { status: 500 }
    )
  }
}
