/**
 * Date utilities for BetFaro
 * All dates are displayed in Brazil timezone (America/Sao_Paulo - GMT-3)
 */

const BRAZIL_TIMEZONE = 'America/Sao_Paulo'

/**
 * Format a date to Brazilian timezone
 * @param date - Date string, Date object, or timestamp
 * @param options - Intl.DateTimeFormat options
 * @returns Formatted date string in Brazil timezone
 */
export function formatDateBR(
  date: string | Date | number,
  options: Intl.DateTimeFormatOptions = {}
): string {
  if (!date) return ''
  
  const dateObj = typeof date === 'string' || typeof date === 'number' 
    ? new Date(date) 
    : date
  
  if (isNaN(dateObj.getTime())) return ''
  
  const defaultOptions: Intl.DateTimeFormatOptions = {
    timeZone: BRAZIL_TIMEZONE,
    ...options
  }
  
  return dateObj.toLocaleString('pt-BR', defaultOptions)
}

/**
 * Format date as dd/MM/yyyy
 */
export function formatDateOnlyBR(date: string | Date | number): string {
  return formatDateBR(date, {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric'
  })
}

/**
 * Format time as HH:mm
 */
export function formatTimeOnlyBR(date: string | Date | number): string {
  return formatDateBR(date, {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  })
}

/**
 * Format date and time as dd/MM/yyyy HH:mm
 */
export function formatDateTimeBR(date: string | Date | number): string {
  return formatDateBR(date, {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  })
}

/**
 * Format date as "Hoje", "Amanhã", or day of week + date
 */
export function formatRelativeDateBR(date: string | Date | number): string {
  if (!date) return ''
  
  const dateObj = typeof date === 'string' || typeof date === 'number' 
    ? new Date(date) 
    : date
  
  if (isNaN(dateObj.getTime())) return ''
  
  // Get today's date in Brazil timezone
  const now = new Date()
  const todayBR = new Date(now.toLocaleString('en-US', { timeZone: BRAZIL_TIMEZONE }))
  todayBR.setHours(0, 0, 0, 0)
  
  // Get the input date in Brazil timezone
  const dateBR = new Date(dateObj.toLocaleString('en-US', { timeZone: BRAZIL_TIMEZONE }))
  dateBR.setHours(0, 0, 0, 0)
  
  const diffDays = Math.floor((dateBR.getTime() - todayBR.getTime()) / (1000 * 60 * 60 * 24))
  
  if (diffDays === 0) {
    return `Hoje, ${formatTimeOnlyBR(date)}`
  } else if (diffDays === 1) {
    return `Amanhã, ${formatTimeOnlyBR(date)}`
  } else if (diffDays === -1) {
    return `Ontem, ${formatTimeOnlyBR(date)}`
  } else if (diffDays > 1 && diffDays <= 6) {
    const dayName = formatDateBR(date, { weekday: 'long' })
    return `${dayName}, ${formatTimeOnlyBR(date)}`
  } else {
    return formatDateTimeBR(date)
  }
}

/**
 * Format kickoff time for display (used in picks and chat)
 * Shows relative date + time
 */
export function formatKickoffBR(date: string | Date | number): string {
  return formatRelativeDateBR(date)
}

/**
 * Check if a date is in the past (in Brazil timezone)
 */
export function isPastBR(date: string | Date | number): boolean {
  if (!date) return false
  
  const dateObj = typeof date === 'string' || typeof date === 'number' 
    ? new Date(date) 
    : date
  
  if (isNaN(dateObj.getTime())) return false
  
  return dateObj.getTime() < Date.now()
}

/**
 * Check if a date is today (in Brazil timezone)
 */
export function isTodayBR(date: string | Date | number): boolean {
  if (!date) return false
  
  const dateObj = typeof date === 'string' || typeof date === 'number' 
    ? new Date(date) 
    : date
  
  if (isNaN(dateObj.getTime())) return false
  
  const now = new Date()
  const todayBR = formatDateOnlyBR(now)
  const dateBR = formatDateOnlyBR(dateObj)
  
  return todayBR === dateBR
}
