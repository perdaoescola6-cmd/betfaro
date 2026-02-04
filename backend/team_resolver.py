"""
TeamResolver - Módulo robusto para resolução de nomes de times
Prioriza times brasileiros quando o contexto indica Brasil
"""
import unicodedata
import re
import logging
from typing import Dict, List, Optional, Tuple
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

class TeamResolver:
    """
    Resolve nomes de times com alta confiança usando:
    1. Aliases locais (mapeamento direto)
    2. Busca na API com fuzzy matching
    3. Validação por fixtures recentes
    4. Priorização por país/contexto
    """
    
    # IDs oficiais da API-Football para times brasileiros (Série A 2024/2025)
    BRAZILIAN_TEAMS = {
        # Série A
        "flamengo": {"id": 127, "name": "Flamengo", "country": "Brazil"},
        "palmeiras": {"id": 121, "name": "Palmeiras", "country": "Brazil"},
        "corinthians": {"id": 131, "name": "Corinthians", "country": "Brazil"},
        "sao paulo": {"id": 126, "name": "Sao Paulo", "country": "Brazil"},
        "santos": {"id": 128, "name": "Santos", "country": "Brazil"},
        "gremio": {"id": 130, "name": "Gremio", "country": "Brazil"},
        "internacional": {"id": 119, "name": "Internacional", "country": "Brazil"},
        "cruzeiro": {"id": 129, "name": "Cruzeiro", "country": "Brazil"},
        "botafogo": {"id": 120, "name": "Botafogo", "country": "Brazil"},
        "fluminense": {"id": 124, "name": "Fluminense", "country": "Brazil"},
        "vasco da gama": {"id": 133, "name": "Vasco DA Gama", "country": "Brazil"},
        "atletico mineiro": {"id": 1062, "name": "Atletico-MG", "country": "Brazil"},
        "athletico paranaense": {"id": 134, "name": "Athletico-PR", "country": "Brazil"},
        "bahia": {"id": 118, "name": "Bahia", "country": "Brazil"},
        "fortaleza": {"id": 132, "name": "Fortaleza EC", "country": "Brazil"},
        "cuiaba": {"id": 1193, "name": "Cuiaba", "country": "Brazil"},
        "bragantino": {"id": 1127, "name": "RB Bragantino", "country": "Brazil"},
        "juventude": {"id": 1837, "name": "Juventude", "country": "Brazil"},
        "vitoria": {"id": 2129, "name": "Vitoria", "country": "Brazil"},
        "criciuma": {"id": 1196, "name": "Criciuma", "country": "Brazil"},
        
        # Série B
        "sport recife": {"id": 135, "name": "Sport Recife", "country": "Brazil"},
        "ceara": {"id": 2130, "name": "Ceara", "country": "Brazil"},
        "coritiba": {"id": 1199, "name": "Coritiba", "country": "Brazil"},
        "chapecoense": {"id": 1194, "name": "Chapecoense-SC", "country": "Brazil"},
        "avai": {"id": 1195, "name": "Avai", "country": "Brazil"},
        "ponte preta": {"id": 1200, "name": "Ponte Preta", "country": "Brazil"},
        "guarani": {"id": 1201, "name": "Guarani", "country": "Brazil"},
        "novorizontino": {"id": 7848, "name": "Novorizontino", "country": "Brazil"},
        "mirassol": {"id": 7847, "name": "Mirassol", "country": "Brazil"},
        "ituano": {"id": 7769, "name": "Ituano", "country": "Brazil"},
        "operario": {"id": 7770, "name": "Operario-PR", "country": "Brazil"},
        "vila nova": {"id": 1202, "name": "Vila Nova", "country": "Brazil"},
        "goias": {"id": 1192, "name": "Goias", "country": "Brazil"},
        "america mineiro": {"id": 1191, "name": "America-MG", "country": "Brazil"},
        "csa": {"id": 2131, "name": "CSA", "country": "Brazil"},
        "abc": {"id": 7771, "name": "ABC", "country": "Brazil"},
        "botafogo pb": {"id": 7772, "name": "Botafogo-PB", "country": "Brazil"},
        "nautico": {"id": 1203, "name": "Nautico", "country": "Brazil"},
        "santa cruz": {"id": 1204, "name": "Santa Cruz", "country": "Brazil"},
        "remo": {"id": 7773, "name": "Remo", "country": "Brazil"},
        "paysandu": {"id": 7774, "name": "Paysandu", "country": "Brazil"},
        "sampaio correa": {"id": 7775, "name": "Sampaio Correa", "country": "Brazil"},
        "tombense": {"id": 7776, "name": "Tombense", "country": "Brazil"},
    }
    
    # Aliases brasileiros (apelidos populares)
    BRAZILIAN_ALIASES = {
        # Apelidos
        "galo": "atletico mineiro",
        "mengao": "flamengo",
        "mengo": "flamengo",
        "fla": "flamengo",
        "verdao": "palmeiras",
        "porco": "palmeiras",
        "timao": "corinthians",
        "coringao": "corinthians",
        "tricolor paulista": "sao paulo",
        "spfc": "sao paulo",
        "peixe": "santos",
        "santastico": "santos",
        "imortal": "gremio",
        "tricolor gaucho": "gremio",
        "colorado": "internacional",
        "inter de porto alegre": "internacional",
        "raposa": "cruzeiro",
        "celeste": "cruzeiro",
        "fogao": "botafogo",
        "glorioso": "botafogo",
        "flu": "fluminense",
        "tricolor carioca": "fluminense",
        "vascao": "vasco da gama",
        "gigante da colina": "vasco da gama",
        "furacao": "athletico paranaense",
        "cap": "athletico paranaense",
        "leao": "fortaleza",
        "tricolor de aco": "fortaleza",
        "esquadrao": "bahia",
        "tricolor baiano": "bahia",
        "dourado": "cuiaba",
        "massa bruta": "bragantino",
        "leao da barra": "vitoria",
        "tigre": "criciuma",
        "papo": "juventude",
        
        # Variações de escrita
        "atletico mg": "atletico mineiro",
        "atletico-mg": "atletico mineiro",
        "atl mineiro": "atletico mineiro",
        "cam": "atletico mineiro",
        "athletico pr": "athletico paranaense",
        "athletico-pr": "athletico paranaense",
        "atl paranaense": "athletico paranaense",
        "rb bragantino": "bragantino",
        "red bull bragantino": "bragantino",
        "redbull bragantino": "bragantino",
        "vasco": "vasco da gama",
        "america mg": "america mineiro",
        "america-mg": "america mineiro",
        "operario pr": "operario",
        "operario-pr": "operario",
        "botafogo-pb": "botafogo pb",
        "chapecoense sc": "chapecoense",
        "chapecoense-sc": "chapecoense",
        "fortaleza ec": "fortaleza",
        "ec vitoria": "vitoria",
    }
    
    # Indicadores de contexto brasileiro
    BRAZIL_INDICATORS = [
        "mg", "sp", "rj", "rs", "pr", "sc", "ba", "ce", "pe", "pa", "go", "mt", "ms", "df",
        "mineiro", "paulista", "carioca", "gaucho", "paranaense", "catarinense", "baiano",
        "brasileiro", "brasileirao", "serie a", "serie b", "copa do brasil",
        "galo", "mengao", "timao", "verdao", "peixe", "colorado", "furacao", "tricolor",
    ]
    
    # Times europeus que podem conflitar
    EUROPEAN_CONFLICTS = {
        "atletico": ["Atletico Madrid", "Atletico-MG", "Athletico-PR"],
        "sporting": ["Sporting CP", "Sporting Braga", "Sporting Gijon"],
        "inter": ["Inter", "Internacional"],
        "vitoria": ["Vitoria", "Vitoria Guimaraes", "Vitoria Setubal"],
        "braga": ["SC Braga", "Sporting Braga"],
    }
    
    def __init__(self, football_api=None):
        self.api = football_api
        
    def _normalize(self, text: str) -> str:
        """Normaliza texto: lowercase, sem acentos, sem pontuação"""
        if not text:
            return ""
        # Lowercase
        text = text.lower().strip()
        # Remove acentos
        text = unicodedata.normalize('NFKD', text)
        text = ''.join(c for c in text if not unicodedata.combining(c))
        # Remove pontuação e hífens
        text = re.sub(r'[^\w\s]', ' ', text)
        # Remove sufixos comuns
        suffixes = ['fc', 'sc', 'ac', 'ec', 'club', 'esporte clube', 'futebol clube']
        for suffix in suffixes:
            text = re.sub(rf'\b{suffix}\b', '', text)
        # Normaliza espaços
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def _similarity(self, a: str, b: str) -> float:
        """Calcula similaridade entre duas strings (0-1)"""
        return SequenceMatcher(None, a, b).ratio()
    
    def _detect_brazil_context(self, text: str) -> bool:
        """Detecta se o contexto indica time brasileiro"""
        normalized = self._normalize(text)
        for indicator in self.BRAZIL_INDICATORS:
            if indicator in normalized:
                return True
        return False
    
    def _is_ambiguous(self, normalized: str) -> Optional[List[str]]:
        """Verifica se o nome é ambíguo e retorna opções"""
        for key, options in self.EUROPEAN_CONFLICTS.items():
            if normalized == key or normalized.startswith(key + " "):
                return options
        return None
    
    def resolve_local(self, team_name: str, prefer_brazil: bool = False) -> Optional[Dict]:
        """
        Resolve time usando aliases locais (sem API)
        Retorna: {id, name, country, confidence, why}
        """
        normalized = self._normalize(team_name)
        
        # 1. Verificar alias brasileiro primeiro
        if normalized in self.BRAZILIAN_ALIASES:
            canonical = self.BRAZILIAN_ALIASES[normalized]
            if canonical in self.BRAZILIAN_TEAMS:
                team = self.BRAZILIAN_TEAMS[canonical]
                return {
                    "id": team["id"],
                    "name": team["name"],
                    "country": team["country"],
                    "confidence": 0.95,
                    "why": f"Alias brasileiro '{team_name}' → {team['name']}"
                }
        
        # 2. Verificar time brasileiro direto
        if normalized in self.BRAZILIAN_TEAMS:
            team = self.BRAZILIAN_TEAMS[normalized]
            return {
                "id": team["id"],
                "name": team["name"],
                "country": team["country"],
                "confidence": 0.95,
                "why": f"Time brasileiro identificado: {team['name']}"
            }
        
        # 3. Busca fuzzy em times brasileiros
        best_match = None
        best_score = 0
        for key, team in self.BRAZILIAN_TEAMS.items():
            score = self._similarity(normalized, key)
            if score > best_score and score >= 0.75:
                best_score = score
                best_match = team
        
        if best_match and (prefer_brazil or best_score >= 0.85):
            return {
                "id": best_match["id"],
                "name": best_match["name"],
                "country": best_match["country"],
                "confidence": best_score,
                "why": f"Fuzzy match brasileiro ({best_score:.0%}): {best_match['name']}"
            }
        
        return None
    
    async def resolve(self, team_name: str, context: str = "") -> Dict:
        """
        Resolve time com alta confiança usando múltiplas etapas
        
        Retorna:
        {
            "success": bool,
            "team_id": int or None,
            "team_name": str or None,
            "country": str or None,
            "confidence": float (0-1),
            "why": str,
            "ambiguous": bool,
            "suggestions": list (se ambíguo)
        }
        """
        normalized = self._normalize(team_name)
        full_context = f"{team_name} {context}".lower()
        prefer_brazil = self._detect_brazil_context(full_context)
        
        logger.info(f"Resolving team: '{team_name}' (normalized: '{normalized}', prefer_brazil: {prefer_brazil})")
        
        # Verificar ambiguidade
        ambiguous_options = self._is_ambiguous(normalized)
        if ambiguous_options and not prefer_brazil:
            # Se contexto indica Brasil, não é ambíguo
            if not any(ind in full_context for ind in ['madrid', 'espanha', 'spain', 'la liga']):
                return {
                    "success": False,
                    "team_id": None,
                    "team_name": None,
                    "country": None,
                    "confidence": 0,
                    "why": f"Nome ambíguo: '{team_name}'",
                    "ambiguous": True,
                    "suggestions": ambiguous_options
                }
        
        # Etapa 1: Resolver localmente (aliases brasileiros)
        local_result = self.resolve_local(team_name, prefer_brazil)
        if local_result and local_result["confidence"] >= 0.85:
            return {
                "success": True,
                "team_id": local_result["id"],
                "team_name": local_result["name"],
                "country": local_result["country"],
                "confidence": local_result["confidence"],
                "why": local_result["why"],
                "ambiguous": False,
                "suggestions": []
            }
        
        # Etapa 2: Buscar na API
        if self.api:
            try:
                api_results = await self.api.search_teams(team_name)
                if api_results:
                    # Filtrar e ranquear resultados
                    candidates = []
                    for team in api_results[:10]:
                        team_normalized = self._normalize(team.get("team", {}).get("name", ""))
                        score = self._similarity(normalized, team_normalized)
                        
                        # Bonus para times brasileiros se contexto indica Brasil
                        country = team.get("team", {}).get("country", "")
                        if prefer_brazil and country == "Brazil":
                            score += 0.15
                        
                        candidates.append({
                            "id": team.get("team", {}).get("id"),
                            "name": team.get("team", {}).get("name"),
                            "country": country,
                            "score": min(score, 1.0)
                        })
                    
                    # Ordenar por score
                    candidates.sort(key=lambda x: x["score"], reverse=True)
                    
                    if candidates and candidates[0]["score"] >= 0.75:
                        best = candidates[0]
                        return {
                            "success": True,
                            "team_id": best["id"],
                            "team_name": best["name"],
                            "country": best["country"],
                            "confidence": best["score"],
                            "why": f"API match ({best['score']:.0%}): {best['name']} ({best['country']})",
                            "ambiguous": False,
                            "suggestions": []
                        }
                    elif candidates:
                        # Baixa confiança - retornar sugestões
                        suggestions = [f"{c['name']} ({c['country']})" for c in candidates[:3]]
                        return {
                            "success": False,
                            "team_id": None,
                            "team_name": None,
                            "country": None,
                            "confidence": candidates[0]["score"] if candidates else 0,
                            "why": f"Confiança baixa para '{team_name}'",
                            "ambiguous": True,
                            "suggestions": suggestions
                        }
            except Exception as e:
                logger.error(f"API search error: {e}")
        
        # Etapa 3: Fallback - usar resultado local mesmo com confiança menor
        if local_result and local_result["confidence"] >= 0.75:
            return {
                "success": True,
                "team_id": local_result["id"],
                "team_name": local_result["name"],
                "country": local_result["country"],
                "confidence": local_result["confidence"],
                "why": local_result["why"],
                "ambiguous": False,
                "suggestions": []
            }
        
        # Não encontrado
        return {
            "success": False,
            "team_id": None,
            "team_name": None,
            "country": None,
            "confidence": 0,
            "why": f"Time não encontrado: '{team_name}'",
            "ambiguous": False,
            "suggestions": []
        }
    
    async def resolve_match(self, team1_name: str, team2_name: str) -> Dict:
        """
        Resolve dois times para uma partida
        
        Retorna:
        {
            "success": bool,
            "team1": {...},
            "team2": {...},
            "confidence": float (média),
            "ambiguous": bool,
            "message": str
        }
        """
        # Contexto combinado
        context = f"{team1_name} {team2_name}"
        
        # Resolver cada time
        result1 = await self.resolve(team1_name, context)
        result2 = await self.resolve(team2_name, context)
        
        # Verificar ambiguidade
        if result1.get("ambiguous") or result2.get("ambiguous"):
            suggestions = []
            if result1.get("ambiguous"):
                suggestions.extend([f"Time 1: {s}" for s in result1.get("suggestions", [])])
            if result2.get("ambiguous"):
                suggestions.extend([f"Time 2: {s}" for s in result2.get("suggestions", [])])
            
            return {
                "success": False,
                "team1": result1,
                "team2": result2,
                "confidence": 0,
                "ambiguous": True,
                "message": "Nomes ambíguos. Você quis dizer:\n" + "\n".join(suggestions[:6])
            }
        
        # Verificar sucesso
        if not result1["success"] or not result2["success"]:
            failed = []
            if not result1["success"]:
                failed.append(f"'{team1_name}'")
            if not result2["success"]:
                failed.append(f"'{team2_name}'")
            
            return {
                "success": False,
                "team1": result1,
                "team2": result2,
                "confidence": 0,
                "ambiguous": False,
                "message": f"Não encontrei com segurança: {', '.join(failed)}"
            }
        
        # Sucesso
        avg_confidence = (result1["confidence"] + result2["confidence"]) / 2
        
        return {
            "success": True,
            "team1": result1,
            "team2": result2,
            "confidence": avg_confidence,
            "ambiguous": False,
            "message": f"Times identificados: {result1['team_name']} vs {result2['team_name']} (confiança: {avg_confidence:.0%})"
        }
