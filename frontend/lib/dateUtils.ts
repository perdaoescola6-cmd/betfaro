/**
 * Date utilities for BetFaro
 * 
 * IMPORTANT: All dates are displayed in the USER'S LOCAL TIMEZONE
 * detected via Intl.DateTimeFormat().resolvedOptions().timeZone
 * 
 * The database stores all dates as UTC (timestamptz).
 * The frontend converts to user's local timezone for display.
 * 
 * Fallback timezone: America/Sao_Paulo (Brazil)
 */

const FALLBACK_TIMEZONE = 'America/Sao_Paulo'

/**
 * Get the user's timezone from the browser
 * Falls back to America/Sao_Paulo if detection fails
 */
export function getUserTimeZone(): string {
  try {
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone
    return tz || FALLBACK_TIMEZONE
  } catch {
    return FALLBACK_TIMEZONE
  }
}

/**
 * Format kickoff time in the user's local timezone
 * @param isoUtc - ISO UTC date string or Date object
 * @param opts - Options for formatting
 * @returns Formatted time string (e.g., "22:00" or "04/02 22:00")
 */
export function formatKickoffLocal(
  isoUtc: string | Date | null | undefined,
  opts?: { withDate?: boolean }
): string {
  if (!isoUtc) return 'Horário indisponível'
  
  const tz = getUserTimeZone()
  const d = typeof isoUtc === 'string' ? new Date(isoUtc) : isoUtc
  
  if (isNaN(d.getTime())) return 'Horário indisponível'
  
  const formatOptions: Intl.DateTimeFormatOptions = {
    timeZone: tz,
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
    ...(opts?.withDate ? { day: '2-digit', month: '2-digit' } : {})
  }
  
  return new Intl.DateTimeFormat('pt-BR', formatOptions).format(d)
}

/**
 * Get day label (Hoje/Amanhã) based on user's timezone
 * @param isoUtc - ISO UTC date string or Date object
 * @returns "Hoje", "Amanhã", or empty string
 */
export function dayLabelLocal(isoUtc: string | Date | null | undefined): string {
  if (!isoUtc) return ''
  
  const tz = getUserTimeZone()
  const d = typeof isoUtc === 'string' ? new Date(isoUtc) : isoUtc
  
  if (isNaN(d.getTime())) return ''
  
  const now = new Date()
  
  // Convert both dates to YYYY-MM-DD in user's timezone for comparison
  const toYMD = (x: Date) =>
    new Intl.DateTimeFormat('en-CA', {
      timeZone: tz,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit'
    }).format(x)
  
  const dateYMD = toYMD(d)
  const todayYMD = toYMD(now)
  
  // Calculate tomorrow in user's timezone
  const tomorrow = new Date(now.getTime() + 24 * 60 * 60 * 1000)
  const tomorrowYMD = toYMD(tomorrow)
  
  // Calculate yesterday
  const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000)
  const yesterdayYMD = toYMD(yesterday)
  
  if (dateYMD === todayYMD) return 'Hoje'
  if (dateYMD === tomorrowYMD) return 'Amanhã'
  if (dateYMD === yesterdayYMD) return 'Ontem'
  
  return ''
}

/**
 * Format kickoff with day label (e.g., "Hoje • 22:00" or "Amanhã • 15:30")
 * @param isoUtc - ISO UTC date string or Date object
 * @returns Formatted string with day label and time
 */
export function formatKickoffWithLabel(isoUtc: string | Date | null | undefined): string {
  if (!isoUtc) return 'Horário indisponível'
  
  const d = typeof isoUtc === 'string' ? new Date(isoUtc) : isoUtc
  if (isNaN(d.getTime())) return 'Horário indisponível'
  
  const label = dayLabelLocal(d)
  const time = formatKickoffLocal(d)
  
  if (label) {
    return `${label} • ${time}`
  }
  
  // If not today/tomorrow/yesterday, show weekday or full date
  const tz = getUserTimeZone()
  const now = new Date()
  const diffMs = d.getTime() - now.getTime()
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))
  
  if (diffDays > 0 && diffDays <= 6) {
    // Within a week - show weekday
    const weekday = new Intl.DateTimeFormat('pt-BR', {
      timeZone: tz,
      weekday: 'short'
    }).format(d).replace('.', '')
    return `${weekday} • ${time}`
  }
  
  // More than a week - show date
  return formatKickoffLocal(d, { withDate: true })
}

/**
 * Format date only in user's timezone (dd/MM/yyyy)
 */
export function formatDateLocal(isoUtc: string | Date | null | undefined): string {
  if (!isoUtc) return ''
  
  const tz = getUserTimeZone()
  const d = typeof isoUtc === 'string' ? new Date(isoUtc) : isoUtc
  
  if (isNaN(d.getTime())) return ''
  
  return new Intl.DateTimeFormat('pt-BR', {
    timeZone: tz,
    day: '2-digit',
    month: '2-digit',
    year: 'numeric'
  }).format(d)
}

/**
 * Format date and time in user's timezone (dd/MM/yyyy HH:mm)
 */
export function formatDateTimeLocal(isoUtc: string | Date | null | undefined): string {
  if (!isoUtc) return ''
  
  const tz = getUserTimeZone()
  const d = typeof isoUtc === 'string' ? new Date(isoUtc) : isoUtc
  
  if (isNaN(d.getTime())) return ''
  
  return new Intl.DateTimeFormat('pt-BR', {
    timeZone: tz,
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  }).format(d)
}

/**
 * Check if a date is in the past (in user's timezone)
 */
export function isPast(isoUtc: string | Date | null | undefined): boolean {
  if (!isoUtc) return false
  
  const d = typeof isoUtc === 'string' ? new Date(isoUtc) : isoUtc
  if (isNaN(d.getTime())) return false
  
  return d.getTime() < Date.now()
}

/**
 * Check if a date is today (in user's timezone)
 */
export function isToday(isoUtc: string | Date | null | undefined): boolean {
  return dayLabelLocal(isoUtc) === 'Hoje'
}

/**
 * Check if a date is a future game (kickoff > now)
 */
export function isFutureGame(isoUtc: string | Date | null | undefined): boolean {
  if (!isoUtc) return true // Assume future if no date
  
  const d = typeof isoUtc === 'string' ? new Date(isoUtc) : isoUtc
  if (isNaN(d.getTime())) return true
  
  return d.getTime() > Date.now()
}
