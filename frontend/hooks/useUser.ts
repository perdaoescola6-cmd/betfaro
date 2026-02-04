'use client'

import { useState, useEffect, useCallback } from 'react'
import { createClient } from '@/lib/supabase/client'

interface UserData {
  userId: string
  email: string
  plan: string
  status: string
  limits: {
    dailyAnalyses: number
    features: string[]
  }
  subscription: {
    plan: string
    status: string
    current_period_end: string
  } | null
}

interface UseUserReturn {
  user: UserData | null
  loading: boolean
  error: string | null
  refresh: () => Promise<void>
  startPolling: () => void
  stopPolling: () => void
}

export function useUser(): UseUserReturn {
  const [user, setUser] = useState<UserData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [pollingInterval, setPollingInterval] = useState<NodeJS.Timeout | null>(null)
  const supabase = createClient()

  const fetchUser = useCallback(async () => {
    try {
      const { data: { user: authUser } } = await supabase.auth.getUser()
      
      if (!authUser) {
        setUser(null)
        setLoading(false)
        return
      }

      const response = await fetch('/api/me', {
        cache: 'no-store',
        headers: {
          'Cache-Control': 'no-cache',
        },
      })

      if (response.ok) {
        const data = await response.json()
        setUser(data)
        setError(null)
      } else {
        setError('Failed to fetch user data')
      }
    } catch (err) {
      console.error('Error fetching user:', err)
      setError('Network error')
    } finally {
      setLoading(false)
    }
  }, [supabase])

  const refresh = useCallback(async () => {
    setLoading(true)
    
    // First, try to sync with Stripe
    try {
      await fetch('/api/billing/refresh', {
        method: 'POST',
        cache: 'no-store',
      })
    } catch (err) {
      console.error('Error refreshing billing:', err)
    }
    
    // Then fetch updated user data
    await fetchUser()
  }, [fetchUser])

  const startPolling = useCallback(() => {
    // Poll every 2 seconds for up to 30 seconds
    let attempts = 0
    const maxAttempts = 15
    const initialPlan = user?.plan

    const interval = setInterval(async () => {
      attempts++
      
      await refresh()
      
      // Stop if plan changed or max attempts reached
      if (user?.plan !== initialPlan || attempts >= maxAttempts) {
        clearInterval(interval)
        setPollingInterval(null)
      }
    }, 2000)

    setPollingInterval(interval)
  }, [user?.plan, refresh])

  const stopPolling = useCallback(() => {
    if (pollingInterval) {
      clearInterval(pollingInterval)
      setPollingInterval(null)
    }
  }, [pollingInterval])

  // Initial fetch
  useEffect(() => {
    fetchUser()
  }, [fetchUser])

  // Listen for auth changes
  useEffect(() => {
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === 'SIGNED_IN') {
        fetchUser()
      } else if (event === 'SIGNED_OUT') {
        setUser(null)
      }
    })

    return () => subscription.unsubscribe()
  }, [supabase, fetchUser])

  // Check for checkout success in URL
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search)
    const checkoutSuccess = urlParams.get('checkout') === 'success' || 
                           urlParams.get('session_id') !== null

    if (checkoutSuccess) {
      // Start polling to detect plan change
      startPolling()
      
      // Clean up URL
      const newUrl = window.location.pathname
      window.history.replaceState({}, '', newUrl)
    }
  }, [startPolling])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (pollingInterval) {
        clearInterval(pollingInterval)
      }
    }
  }, [pollingInterval])

  return {
    user,
    loading,
    error,
    refresh,
    startPolling,
    stopPolling,
  }
}
