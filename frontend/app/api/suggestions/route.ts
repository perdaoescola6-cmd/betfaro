import { NextRequest, NextResponse } from 'next/server';

// Liga IDs da API-Football com prioridade
const LEAGUE_PRIORITY: Record<number, { tier: number; name: string }> = {
  // Tier 1 - Brasil + Champions
  71: { tier: 1, name: "Brasileirão Série A" },
  72: { tier: 1, name: "Brasileirão Série B" },
  73: { tier: 1, name: "Copa do Brasil" },
  13: { tier: 1, name: "Libertadores" },
  11: { tier: 1, name: "Sul-Americana" },
  2: { tier: 1, name: "Champions League" },
  3: { tier: 1, name: "Europa League" },
  
  // Tier 2 - Top 5 Europa
  39: { tier: 2, name: "Premier League" },
  140: { tier: 2, name: "La Liga" },
  135: { tier: 2, name: "Serie A" },
  78: { tier: 2, name: "Bundesliga" },
  61: { tier: 2, name: "Ligue 1" },
  
  // Tier 3 - Outras ligas relevantes
  94: { tier: 3, name: "Primeira Liga" },
  88: { tier: 3, name: "Eredivisie" },
  307: { tier: 3, name: "Saudi Pro League" },
  262: { tier: 3, name: "Liga MX" },
  253: { tier: 3, name: "MLS" },
  128: { tier: 3, name: "Argentina Primera" },
  
  // Tier 4 - Estaduais BR
  475: { tier: 4, name: "Paulistão" },
  476: { tier: 4, name: "Carioca" },
  477: { tier: 4, name: "Mineiro" },
  478: { tier: 4, name: "Gaúcho" },
};

const FALLBACK_SUGGESTIONS = [
  { label: "Flamengo x Palmeiras", query: "Flamengo x Palmeiras" },
  { label: "Real Madrid x Barcelona", query: "Real Madrid x Barcelona" },
  { label: "Arsenal x Chelsea", query: "Arsenal x Chelsea" },
  { label: "Benfica x Porto", query: "Benfica x Porto" },
];

interface Suggestion {
  label: string;
  query: string;
  league?: string;
  kickoffTime?: string;
  tier?: number;
}

async function fetchFixturesForDate(dateStr: string): Promise<Suggestion[]> {
  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || process.env.BACKEND_URL || 'https://betfaro-production.up.railway.app';
  
  try {
    const response = await fetch(`${backendUrl}/api/suggestions?day=${dateStr}`, {
      headers: {
        'Content-Type': 'application/json',
      },
      cache: 'no-store',
    });
    
    if (!response.ok) {
      console.error(`Backend suggestions failed: ${response.status}`);
      return [];
    }
    
    const data = await response.json();
    return data.suggestions || [];
  } catch (error) {
    console.error('Error fetching suggestions from backend:', error);
    return [];
  }
}

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const day = searchParams.get('day') || 'today';
  
  try {
    // Buscar jogos de hoje
    let suggestions = await fetchFixturesForDate('today');
    
    // Se não tiver jogos suficientes, completar com amanhã
    if (suggestions.length < 8) {
      const tomorrowSuggestions = await fetchFixturesForDate('tomorrow');
      suggestions = [...suggestions, ...tomorrowSuggestions];
    }
    
    // Limitar a 12 sugestões
    suggestions = suggestions.slice(0, 12);
    
    // Se ainda não tiver sugestões, usar fallback
    if (suggestions.length === 0) {
      return NextResponse.json({
        suggestions: FALLBACK_SUGGESTIONS,
        source: 'fallback',
        date: new Date().toISOString().split('T')[0],
      });
    }
    
    return NextResponse.json({
      suggestions,
      source: 'api',
      date: new Date().toISOString().split('T')[0],
    });
    
  } catch (error) {
    console.error('Error in suggestions endpoint:', error);
    return NextResponse.json({
      suggestions: FALLBACK_SUGGESTIONS,
      source: 'fallback',
      error: 'Failed to fetch suggestions',
    });
  }
}
