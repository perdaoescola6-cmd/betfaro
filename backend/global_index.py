"""
Global Index - Índice dinâmico de ligas e times da API-Football
Não depende de ligas hardcoded - busca tudo da API
"""
import asyncio
import logging
import unicodedata
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

class GlobalIndex:
    """
    Índice global de ligas e times
    - Busca todas as ligas da API dinamicamente
    - Cria índice de times com aliases normalizados
    - Cache com TTL de 24h
    """
    
    # Países prioritários (ordem de prioridade para desambiguação)
    PRIORITY_COUNTRIES = [
        "Brazil", "England", "Spain", "Italy", "Germany", "France",
        "Portugal", "Netherlands", "Argentina", "Saudi Arabia",
        "Mexico", "USA", "Japan", "South Korea", "Turkey",
        "Belgium", "Scotland", "Chile", "Colombia", "UAE", "Qatar"
    ]
    
    # Ligas brasileiras (IDs conhecidos da API-Football)
    BRAZIL_LEAGUES = {
        71: {"name": "Série A", "tier": 1},
        72: {"name": "Série B", "tier": 2},
        75: {"name": "Série C", "tier": 3},
        73: {"name": "Copa do Brasil", "tier": 1, "type": "cup"},
        # Estaduais
        475: {"name": "Paulistão", "tier": 2, "type": "state"},
        476: {"name": "Carioca", "tier": 2, "type": "state"},
        477: {"name": "Mineiro", "tier": 2, "type": "state"},
        478: {"name": "Gaúcho", "tier": 2, "type": "state"},
        479: {"name": "Paranaense", "tier": 2, "type": "state"},
        480: {"name": "Catarinense", "tier": 2, "type": "state"},
        481: {"name": "Baiano", "tier": 2, "type": "state"},
        482: {"name": "Pernambucano", "tier": 2, "type": "state"},
        483: {"name": "Cearense", "tier": 2, "type": "state"},
        484: {"name": "Goiano", "tier": 2, "type": "state"},
    }
    
    # Ligas internacionais importantes
    IMPORTANT_LEAGUES = {
        # Europa
        39: {"name": "Premier League", "country": "England", "tier": 1},
        40: {"name": "Championship", "country": "England", "tier": 2},
        140: {"name": "La Liga", "country": "Spain", "tier": 1},
        141: {"name": "Segunda División", "country": "Spain", "tier": 2},
        135: {"name": "Serie A", "country": "Italy", "tier": 1},
        136: {"name": "Serie B", "country": "Italy", "tier": 2},
        78: {"name": "Bundesliga", "country": "Germany", "tier": 1},
        79: {"name": "2. Bundesliga", "country": "Germany", "tier": 2},
        61: {"name": "Ligue 1", "country": "France", "tier": 1},
        62: {"name": "Ligue 2", "country": "France", "tier": 2},
        94: {"name": "Primeira Liga", "country": "Portugal", "tier": 1},
        88: {"name": "Eredivisie", "country": "Netherlands", "tier": 1},
        203: {"name": "Süper Lig", "country": "Turkey", "tier": 1},
        144: {"name": "Pro League", "country": "Belgium", "tier": 1},
        179: {"name": "Superliga", "country": "Denmark", "tier": 1},
        106: {"name": "Ekstraklasa", "country": "Poland", "tier": 1},
        345: {"name": "Czech Liga", "country": "Czech-Republic", "tier": 1},
        # Champions/Europa
        2: {"name": "Champions League", "country": "World", "tier": 1, "type": "cup"},
        3: {"name": "Europa League", "country": "World", "tier": 1, "type": "cup"},
        848: {"name": "Conference League", "country": "World", "tier": 2, "type": "cup"},
        # Américas
        128: {"name": "Primera División", "country": "Argentina", "tier": 1},
        129: {"name": "Copa Argentina", "country": "Argentina", "tier": 1, "type": "cup"},
        262: {"name": "Liga MX", "country": "Mexico", "tier": 1},
        265: {"name": "Liga Expansión MX", "country": "Mexico", "tier": 2},
        253: {"name": "MLS", "country": "USA", "tier": 1},
        239: {"name": "Primera División", "country": "Chile", "tier": 1},
        239: {"name": "Primera A", "country": "Colombia", "tier": 1},
        # Ásia
        307: {"name": "Saudi Pro League", "country": "Saudi-Arabia", "tier": 1},
        308: {"name": "Saudi First Division", "country": "Saudi-Arabia", "tier": 2},
        98: {"name": "J-League", "country": "Japan", "tier": 1},
        99: {"name": "J2 League", "country": "Japan", "tier": 2},
        292: {"name": "K-League 1", "country": "South-Korea", "tier": 1},
        169: {"name": "Chinese Super League", "country": "China", "tier": 1},
        # Oriente Médio
        305: {"name": "UAE League", "country": "UAE", "tier": 1},
        301: {"name": "Qatar Stars League", "country": "Qatar", "tier": 1},
        290: {"name": "Iran Pro League", "country": "Iran", "tier": 1},
    }
    
    def __init__(self, api=None):
        self.api = api
        self._leagues_cache = {}
        self._teams_cache = {}
        self._teams_by_name = {}  # Normalized name -> team data
        self._cache_timestamp = None
        self.CACHE_TTL = 86400  # 24 hours
        
    def _normalize(self, text: str) -> str:
        """Normaliza texto para comparação"""
        if not text:
            return ""
        text = text.lower().strip()
        text = unicodedata.normalize('NFKD', text)
        text = ''.join(c for c in text if not unicodedata.combining(c))
        text = re.sub(r'[^\w\s]', ' ', text)
        # Remove sufixos comuns
        suffixes = ['fc', 'sc', 'ac', 'ec', 'club', 'cf']
        for suffix in suffixes:
            text = re.sub(rf'\b{suffix}\b', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def _similarity(self, a: str, b: str) -> float:
        """Calcula similaridade entre strings"""
        return SequenceMatcher(None, a, b).ratio()
    
    async def initialize(self):
        """Inicializa o índice global (chamado no startup)"""
        if self._is_cache_valid():
            logger.info("Global index cache is valid, skipping initialization")
            return
        
        logger.info("Initializing global index...")
        
        try:
            # Buscar ligas
            await self._load_leagues()
            
            # Buscar times das ligas importantes
            await self._load_teams()
            
            self._cache_timestamp = datetime.utcnow()
            logger.info(f"Global index initialized: {len(self._leagues_cache)} leagues, {len(self._teams_cache)} teams")
            
        except Exception as e:
            logger.error(f"Failed to initialize global index: {e}")
    
    def _is_cache_valid(self) -> bool:
        """Verifica se o cache ainda é válido"""
        if not self._cache_timestamp:
            return False
        elapsed = (datetime.utcnow() - self._cache_timestamp).total_seconds()
        return elapsed < self.CACHE_TTL
    
    async def _load_leagues(self):
        """Carrega todas as ligas da API"""
        if not self.api:
            # Usar ligas conhecidas como fallback
            self._leagues_cache = {**self.BRAZIL_LEAGUES, **self.IMPORTANT_LEAGUES}
            return
        
        try:
            # Buscar ligas ativas
            leagues = await self.api._make_request("leagues", {"current": "true"})
            
            for league_data in leagues:
                league = league_data.get("league", {})
                country = league_data.get("country", {})
                
                league_id = league.get("id")
                if league_id:
                    self._leagues_cache[league_id] = {
                        "name": league.get("name"),
                        "country": country.get("name"),
                        "type": league.get("type"),
                        "logo": league.get("logo")
                    }
            
            logger.info(f"Loaded {len(self._leagues_cache)} leagues from API")
            
        except Exception as e:
            logger.warning(f"Failed to load leagues from API: {e}, using fallback")
            self._leagues_cache = {**self.BRAZIL_LEAGUES, **self.IMPORTANT_LEAGUES}
    
    async def _load_teams(self):
        """Carrega times das ligas importantes"""
        if not self.api:
            return
        
        # Ligas prioritárias para carregar times
        priority_league_ids = list(self.BRAZIL_LEAGUES.keys()) + list(self.IMPORTANT_LEAGUES.keys())
        
        for league_id in priority_league_ids[:30]:  # Limitar para não exceder rate limit
            try:
                teams = await self.api._make_request("teams", {"league": league_id, "season": 2024})
                
                for team_data in teams:
                    team = team_data.get("team", {})
                    team_id = team.get("id")
                    
                    if team_id:
                        team_info = {
                            "id": team_id,
                            "name": team.get("name"),
                            "country": team.get("country"),
                            "logo": team.get("logo"),
                            "league_id": league_id
                        }
                        self._teams_cache[team_id] = team_info
                        
                        # Indexar por nome normalizado
                        normalized = self._normalize(team.get("name", ""))
                        if normalized:
                            self._teams_by_name[normalized] = team_info
                
                await asyncio.sleep(0.1)  # Rate limiting
                
            except Exception as e:
                logger.warning(f"Failed to load teams for league {league_id}: {e}")
                continue
        
        logger.info(f"Loaded {len(self._teams_cache)} teams from API")
    
    async def search_team(self, query: str, prefer_country: str = None) -> Optional[Dict]:
        """
        Busca time no índice global
        
        Args:
            query: Nome do time (pode ser apelido, nome parcial, etc)
            prefer_country: País preferido para desambiguação
        
        Returns:
            Dict com dados do time ou None
        """
        normalized = self._normalize(query)
        
        # 1. Busca exata no índice
        if normalized in self._teams_by_name:
            return self._teams_by_name[normalized]
        
        # 2. Busca fuzzy no índice local
        best_match = None
        best_score = 0
        
        for name, team in self._teams_by_name.items():
            score = self._similarity(normalized, name)
            
            # Bonus para país preferido
            if prefer_country and team.get("country") == prefer_country:
                score += 0.1
            
            if score > best_score:
                best_score = score
                best_match = team
        
        if best_match and best_score >= 0.75:
            return best_match
        
        # 3. Busca na API (fallback)
        if self.api:
            try:
                results = await self.api.search_teams(query)
                if results:
                    # Filtrar por país preferido se especificado
                    if prefer_country:
                        country_matches = [r for r in results if r.get("team", {}).get("country") == prefer_country]
                        if country_matches:
                            results = country_matches
                    
                    if results:
                        team = results[0].get("team", {})
                        return {
                            "id": team.get("id"),
                            "name": team.get("name"),
                            "country": team.get("country"),
                            "logo": team.get("logo")
                        }
            except Exception as e:
                logger.warning(f"API search failed for '{query}': {e}")
        
        return None
    
    async def search_teams_multi(self, queries: List[str], context: str = "") -> List[Optional[Dict]]:
        """Busca múltiplos times em paralelo"""
        # Detectar país preferido pelo contexto
        prefer_country = None
        context_lower = context.lower()
        
        if any(ind in context_lower for ind in ["mg", "sp", "rj", "rs", "brasileiro", "galo", "mengao"]):
            prefer_country = "Brazil"
        elif any(ind in context_lower for ind in ["al-", "saudi", "riyadh"]):
            prefer_country = "Saudi-Arabia"
        
        tasks = [self.search_team(q, prefer_country) for q in queries]
        return await asyncio.gather(*tasks)
    
    def get_league_info(self, league_id: int) -> Optional[Dict]:
        """Retorna informações de uma liga"""
        return self._leagues_cache.get(league_id)
    
    def get_leagues_by_country(self, country: str) -> List[Dict]:
        """Retorna todas as ligas de um país"""
        return [
            {"id": lid, **info}
            for lid, info in self._leagues_cache.items()
            if info.get("country", "").lower() == country.lower()
        ]
    
    def get_brazil_leagues(self) -> List[Dict]:
        """Retorna todas as ligas brasileiras"""
        return self.get_leagues_by_country("Brazil")


# Singleton instance
_global_index = None

def get_global_index() -> GlobalIndex:
    """Retorna instância singleton do índice global"""
    global _global_index
    if _global_index is None:
        _global_index = GlobalIndex()
    return _global_index

async def initialize_global_index(api):
    """Inicializa o índice global com a API"""
    index = get_global_index()
    index.api = api
    await index.initialize()
    return index
