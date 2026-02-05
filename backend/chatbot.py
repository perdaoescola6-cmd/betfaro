from typing import Dict, List, Optional, Tuple
import asyncio
import re
import logging
from datetime import datetime
from football_api import FootballAPI
from models import User, Subscription
from team_resolver import TeamResolver

logger = logging.getLogger(__name__)

class ChatBot:
    def __init__(self):
        self.api = FootballAPI()
        self.team_resolver = TeamResolver(self.api)
        
        # Market patterns for intelligent parsing
        self.market_patterns = {
            # Over patterns
            r'(?:over|o|mais de|acima de|mais|acima)\s*(\d+[.,]?\d*)(?:\s*(?:gols?|goals?))?': lambda m: f"Over {m.group(1).replace(',', '.')} Gols",
            r'\+(\d+[.,]?\d*)(?:\s*(?:gols?|goals?))?': lambda m: f"Over {m.group(1).replace(',', '.')} Gols",
            # Under patterns
            r'(?:under|u|menos de|abaixo de|menos|abaixo)\s*(\d+[.,]?\d*)(?:\s*(?:gols?|goals?))?': lambda m: f"Under {m.group(1).replace(',', '.')} Gols",
            r'-(\d+[.,]?\d*)(?:\s*(?:gols?|goals?))?': lambda m: f"Under {m.group(1).replace(',', '.')} Gols",
            # BTTS patterns
            r'(?:btts|ambas?\s*(?:marcam?|marcarem?)|ambos?\s*(?:marcam?|marcarem?)|both\s*(?:teams?\s*)?(?:to\s*)?score)(?:\s*(?:sim|yes|s))?': lambda m: "Ambos Marcam (Sim)",
            r'(?:btts|ambas?\s*(?:marcam?|marcarem?)|ambos?\s*(?:marcam?|marcarem?))(?:\s*(?:não|no|n))': lambda m: "Ambos Marcam (Não)",
        }
        
        # Odd patterns
        self.odd_patterns = [
            r'@\s*(\d+[.,]\d+)',  # @2.10
            r'odd[s]?\s*[:=]?\s*(\d+[.,]\d+)',  # odd: 2.10
            r'(?:^|\s)(\d+[.,]\d{2})(?:\s|$)',  # 2.10 standalone
        ]
    
    # Plan limits for feature-gating
    PLAN_LIMITS = {
        'free': 5,
        'pro': 25,
        'elite': 100
    }
    
    async def process_message(self, user_input: str, user: User) -> str:
        """Process user message with intelligent interpretation"""
        try:
            original_input = user_input.strip()
            
            # ═════════════════════════════════════════════════════════════════
            # 0. CHECK PLAN LIMITS (Feature-gating) - Only check, don't consume yet
            # ═════════════════════════════════════════════════════════════════
            if not self._has_remaining_quota(user):
                return self._format_limit_reached(user)
            
            # ═══════════════════════════════════════════════════════════════
            # 1. HANDLE COMMANDS
            # ═══════════════════════════════════════════════════════════════
            if original_input.lower() in ['/help', 'help', 'ajuda', '/ajuda', '?']:
                return self._format_help()
            
            # ═══════════════════════════════════════════════════════════════
            # 2. PARSE INPUT - Extract teams, markets, and odds
            # ═══════════════════════════════════════════════════════════════
            parsed = self._intelligent_parse(original_input)
            
            teams_text = parsed.get("teams_text", "")
            markets = parsed.get("markets", [])
            odds = parsed.get("odds", [])
            
            # ═══════════════════════════════════════════════════════════════
            # 3. IDENTIFY TEAMS - Try multiple methods
            # ═══════════════════════════════════════════════════════════════
            teams = []
            ambiguous = False
            
            # Method 1: Direct regex extraction from cleaned text
            if teams_text:
                extracted = self._extract_teams_from_text(teams_text)
                if extracted:
                    teams = extracted
            
            # Method 2: Try LLM if direct extraction failed
            if not teams:
                try:
                    text_for_llm = teams_text if teams_text else original_input
                    llm_result = await self.api.translate_team_name_with_llm(text_for_llm)
                    teams = llm_result.get("teams", [])
                    ambiguous = llm_result.get("ambiguous", False)
                    
                    if ambiguous:
                        options = llm_result.get("options", [])
                        question = llm_result.get("question", "Qual time você quer dizer?")
                        return self._format_disambiguation_question(question, options)
                except Exception as e:
                    pass  # Continue to fallback
            
            # Method 3: Fallback - extract from original input
            if not teams:
                extracted = self._extract_teams_from_text(original_input)
                if extracted:
                    teams = extracted
            
            # ═══════════════════════════════════════════════════════════════
            # 4. HANDLE DIFFERENT SCENARIOS
            # ═══════════════════════════════════════════════════════════════
            
            # Standard match analysis (with or without markets/odds)
            if len(teams) >= 2:
                parsed = {
                    "intent": "match",
                    "team_a": teams[0],
                    "team_b": teams[1],
                    "n": 10,
                    "split_mode": "A_HOME_B_AWAY",
                    "markets": markets,
                    "odds": odds
                }
                return await self._analyze_match(parsed, user)
            
            # Single team analysis
            elif len(teams) >= 1:
                parsed = {
                    "intent": "team",
                    "team": teams[0],
                    "n": 10,
                    "home_away": "all",
                    "metrics": ["over_2_5", "btts", "win_rate", "over_1_5", "clean_sheet_rate"]
                }
                return await self._analyze_team(parsed, user)
            
            # ═══════════════════════════════════════════════════════════════
            # 5. FRIENDLY FALLBACK - Never show cold error
            # ═══════════════════════════════════════════════════════════════
            return self._format_friendly_fallback(original_input)
                
        except Exception as e:
            return self._format_friendly_fallback(str(e))
    
    def _extract_teams_from_text(self, text: str) -> List[str]:
        """Extract RAW team names from text - DO NOT resolve here, let TeamResolver handle it"""
        teams = []
        text_lower = text.lower().strip()
        
        logger.info(f"[PARSE] Input: '{text}'")
        
        # ROBUST SEPARATORS: x, vs, versus, × (NOT hyphen - it's used in team names like Al-Khaleej)
        separators = r'\s+(?:x|vs\.?|versus|v\.?|×)\s+'
        
        # Try to split by separator first (most reliable)
        parts = re.split(separators, text_lower, maxsplit=1, flags=re.IGNORECASE)
        
        if len(parts) >= 2:
            team_a_raw = parts[0].strip()
            team_b_raw = parts[1].strip()
            
            # Clean team B from trailing market/odds info
            team_b_raw = re.sub(r'\s+(?:over|under|o|u)\s*\d.*$', '', team_b_raw, flags=re.IGNORECASE)
            team_b_raw = re.sub(r'\s+btts.*$', '', team_b_raw, flags=re.IGNORECASE)
            team_b_raw = re.sub(r'\s+ambas?.*$', '', team_b_raw, flags=re.IGNORECASE)
            team_b_raw = re.sub(r'\s*@.*$', '', team_b_raw)
            team_b_raw = re.sub(r'\s+\d+[.,]\d+.*$', '', team_b_raw)
            team_b_raw = team_b_raw.strip()
            
            # Return RAW names - TeamResolver will handle resolution with Brazil priority
            if team_a_raw and team_b_raw:
                teams = [team_a_raw, team_b_raw]
                logger.info(f"[PARSE] Extracted RAW teams: {teams}")
        
        return teams
    
    def _resolve_team_alias(self, raw_name: str, known_teams: dict) -> str:
        """Resolve a raw team name to its official name using aliases"""
        raw_lower = raw_name.lower().strip()
        
        # Direct match
        if raw_lower in known_teams:
            return known_teams[raw_lower]
        
        # Partial match (alias contains raw or raw contains alias)
        for alias, official in known_teams.items():
            if alias == raw_lower or raw_lower == alias:
                return official
            # Check if raw is a substring of alias or vice versa
            if len(raw_lower) >= 3:
                if raw_lower in alias or alias in raw_lower:
                    return official
        
        # No match found - return title case of raw name
        return raw_name.title()
    
    def _intelligent_parse(self, user_input: str) -> Dict:
        """Intelligently parse user input to extract teams, markets, and odds"""
        result = {
            "teams_text": "",
            "markets": [],
            "odds": []
        }
        
        text = user_input.lower().strip()
        
        # Extract odds first (they're easy to identify)
        for pattern in self.odd_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                odd_value = match.replace(',', '.')
                try:
                    if 1.01 <= float(odd_value) <= 100:  # Valid odd range
                        result["odds"].append(odd_value)
                except:
                    pass
        
        # Extract markets
        for pattern, formatter in self.market_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                market = formatter(match)
                if market not in result["markets"]:
                    result["markets"].append(market)
        
        # Clean text to extract teams - be aggressive
        teams_text = text
        
        # Remove odds patterns
        teams_text = re.sub(r'@\s*\d+[.,]\d+', ' ', teams_text)
        teams_text = re.sub(r'odd[s]?\s*[:=]?\s*\d+[.,]\d+', ' ', teams_text)
        teams_text = re.sub(r'(?:^|\s)\d+[.,]\d{2}(?:\s|$)', ' ', teams_text)
        
        # Remove market keywords - comprehensive list
        market_keywords = [
            r'\bover\s*\d+[.,]?\d*', r'\bo\d+[.,]?\d*', r'\+\d+[.,]?\d*',
            r'\bunder\s*\d+[.,]?\d*', r'\bu\d+[.,]?\d*', r'-\d+[.,]?\d*',
            r'\bbtts\b', r'\bambas?\s*marcam?\b', r'\bambos?\s*marcam?\b',
            r'\bboth\s*teams?\s*(?:to\s*)?score\b',
            r'\bgols?\b', r'\bgoals?\b',
            r'\bsim\b', r'\byes\b', r'\bnão\b', r'\bno\b',
            r'\bmais\s*de\b', r'\bmenos\s*de\b', r'\bacima\s*de\b', r'\babaixo\s*de\b',
        ]
        for kw in market_keywords:
            teams_text = re.sub(kw, ' ', teams_text, flags=re.IGNORECASE)
        
        # Remove connectors and noise
        teams_text = re.sub(r'\s+e\s+', ' ', teams_text)
        teams_text = re.sub(r'\s+\+\s+', ' ', teams_text)
        teams_text = re.sub(r'\s+com\s+', ' ', teams_text)
        teams_text = re.sub(r'\s+and\s+', ' ', teams_text)
        
        # Clean up multiple spaces and trim
        teams_text = re.sub(r'\s+', ' ', teams_text).strip()
        
        # Keep the original text - the separator pattern will be handled by _extract_teams_from_text
        result["teams_text"] = teams_text
        
        return result
    
    def _format_help(self) -> str:
        """Format help message"""
        lines = []
        lines.append("📌 Como usar o BetFaro")
        lines.append("─────────────────────────────────────────────────────────")
        lines.append("")
        lines.append("📊 Análise de jogo:")
        lines.append("  Chelsea vs Arsenal")
        lines.append("  Benfica x Porto")
        lines.append("  Flamengo - Palmeiras")
        lines.append("")
        lines.append("🎯 Com mercados específicos:")
        lines.append("  Chelsea x Arsenal over 2.5")
        lines.append("  Benfica vs Porto btts sim")
        lines.append("  Real Madrid x Barcelona o2.5 + btts")
        lines.append("")
        lines.append("💰 Com odds:")
        lines.append("  Chelsea x Arsenal o2.5 @2.10")
        lines.append("  Benfica vs Porto btts sim @1.85")
        lines.append("")
        lines.append("📈 Estatísticas de time:")
        lines.append("  Chelsea stats")
        lines.append("  Estatísticas do Benfica")
        lines.append("")
        lines.append("─────────────────────────────────────────────────────────")
        lines.append("💡 Dica: Pode escrever de forma informal, eu entendo!")
        return "\n".join(lines)
    
    def _format_bet_confirmation(self, teams: List[str], markets: List[str], odds: List[str]) -> str:
        """Format bet confirmation when user provides markets/odds"""
        lines = []
        lines.append(f"⚽ {teams[0]} vs {teams[1]}")
        lines.append("")
        
        if markets:
            lines.append(f"🎯 Mercados: {' + '.join(markets)}")
        
        if odds:
            lines.append(f"💰 Odd informada: {', '.join(odds)}")
        
        lines.append("")
        lines.append("─────────────────────────────────────────────────────────")
        lines.append("")
        lines.append("O que você quer fazer?")
        lines.append("  1. Digite 'analisar' para ver a análise completa")
        lines.append("  2. Digite 'validar' para verificar se a odd tem valor")
        lines.append("")
        lines.append("Ou simplesmente digite o jogo sem mercados para análise:")
        lines.append(f"  {teams[0]} vs {teams[1]}")
        
        return "\n".join(lines)
    
    def _format_friendly_fallback(self, original_input: str) -> str:
        """Format friendly fallback when we can't understand the input"""
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"[FALLBACK] Could not process: '{original_input}'")
        
        lines = []
        text_lower = original_input.lower().strip()
        
        # Check if it looks like a match query
        has_separator = any(sep in text_lower for sep in [' x ', ' vs ', ' v ', ' - ', '×'])
        
        if has_separator:
            # User tried to input a match but we couldn't find the teams
            lines.append("🔍 Não encontrei esse jogo com segurança.")
            lines.append("")
            lines.append("Verifique se os nomes dos times estão corretos.")
            lines.append("")
            lines.append("💡 Dica: Use o nome completo do time:")
            lines.append("  • Arsenal x Chelsea ✓")
            lines.append("  • Man United vs Liverpool ✓")
            lines.append("  • Benfica x Porto ✓")
        else:
            # User input doesn't look like a match
            lines.append("🤔 Não entendi sua mensagem.")
            lines.append("")
            lines.append("Para analisar um jogo, use o formato:")
            lines.append("  • Time A x Time B")
            lines.append("  • Time A vs Time B")
            lines.append("")
            lines.append("💡 Exemplos:")
            lines.append("  • Chelsea vs Arsenal")
            lines.append("  • Benfica x Porto over 2.5 @1.90")
            lines.append("  • Flamengo vs Palmeiras btts")
        
        lines.append("")
        lines.append("─────────────────────────────────────────────────────────")
        lines.append("Digite /help para ver todos os comandos disponíveis.")
        
        return "\n".join(lines)
    
    def _format_error(self, message: str) -> str:
        """Format error message - clean professional style"""
        lines = []
        lines.append("┌─────────────────────────────────────────────────────────┐")
        lines.append("│  ERROR                                                  │")
        lines.append("├─────────────────────────────────────────────────────────┤")
        lines.append(f"│  {message[:55]:<55} │")
        lines.append("│                                                         │")
        lines.append("│  Examples:                                              │")
        lines.append("│    - Benfica vs Porto                                   │")
        lines.append("│    - Flamengo vs Palmeiras                              │")
        lines.append("│    - Chelsea stats                                      │")
        lines.append("└─────────────────────────────────────────────────────────┘")
        return "\n".join(lines)
    
    def _format_disambiguation_question(self, question: str, options: list) -> str:
        """Format disambiguation question - clean professional style"""
        lines = []
        lines.append("┌─────────────────────────────────────────────────────────┐")
        lines.append("│  CLARIFICATION REQUIRED                                 │")
        lines.append("├─────────────────────────────────────────────────────────┤")
        lines.append(f"│  {question:<55} │")
        lines.append("│                                                         │")
        lines.append("│  Available options:                                     │")
        for i, option in enumerate(options, 1):
            lines.append(f"│    {i}. {option:<51} │")
        lines.append("│                                                         │")
        lines.append("│  Please type the full team name to continue.            │")
        lines.append("└─────────────────────────────────────────────────────────┘")
        return "\n".join(lines)
    
    async def _analyze_match(self, parsed: Dict, user: User) -> str:
        """Analyze match between two teams with strict data validation
        
        IMPORTANT: Only consumes quota if analysis is successful!
        """
        team_a_name = parsed["team_a"]
        team_b_name = parsed["team_b"]
        REQUIRED_GAMES = 10  # FIXED: Always 10 games per team
        markets = parsed.get("markets", [])
        odds = parsed.get("odds", [])
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 1: RESOLVE TEAMS using TeamResolver (with Brazil priority)
        # ═══════════════════════════════════════════════════════════════
        logger.info(f"Resolving match: {team_a_name} vs {team_b_name}")
        
        match_result = await self.team_resolver.resolve_match(team_a_name, team_b_name)
        
        # Handle ambiguous names - DON'T consume quota
        if match_result.get("ambiguous"):
            return self._format_ambiguous_teams(match_result)
        
        # Handle resolution failure - DON'T consume quota
        if not match_result.get("success"):
            return self._format_team_not_found(team_a_name, team_b_name, match_result)
        
        team_a = {
            "id": match_result["team1"]["team_id"],
            "name": match_result["team1"]["team_name"],
            "country": match_result["team1"]["country"]
        }
        team_b = {
            "id": match_result["team2"]["team_id"],
            "name": match_result["team2"]["team_name"],
            "country": match_result["team2"]["country"]
        }
        
        confidence = match_result.get("confidence", 0)
        logger.info(f"Teams resolved: {team_a['name']} vs {team_b['name']} (confidence: {confidence:.0%})")
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 2: FETCH FIXTURES (get extra for filtering)
        # ═══════════════════════════════════════════════════════════════
        fixtures_a_raw = await self.api.get_team_fixtures(team_a["id"], REQUIRED_GAMES * 3)
        fixtures_b_raw = await self.api.get_team_fixtures(team_b["id"], REQUIRED_GAMES * 3)
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 3: VALIDATE AND FILTER FIXTURES
        # ═══════════════════════════════════════════════════════════════
        validated_a = self._validate_fixtures(fixtures_a_raw, team_a["id"], REQUIRED_GAMES)
        validated_b = self._validate_fixtures(fixtures_b_raw, team_b["id"], REQUIRED_GAMES)
        
        # Check if we have enough valid data - DON'T consume quota if not
        if not validated_a["valid"] or not validated_b["valid"]:
            return self._format_data_error(team_a["name"], team_b["name"], validated_a, validated_b)
        
        filtered_a = validated_a["fixtures"]
        filtered_b = validated_b["fixtures"]
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 4: GENERATE ANALYSIS WITH VERIFIED DATA
        # ═══════════════════════════════════════════════════════════════
        analysis = self._generate_match_analysis(
            team_a, team_b, 
            filtered_a, filtered_b, 
            "LAST_10",  # Always last 10 games
            markets, odds,
            validated_a["date_range"], validated_b["date_range"],
            confidence  # Pass confidence for display
        )
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 5: CONSUME QUOTA - Only after successful analysis!
        # ═══════════════════════════════════════════════════════════════
        self._consume_quota(user)
        
        return analysis
    
    def _format_ambiguous_teams(self, match_result: Dict) -> str:
        """Format message when team names are ambiguous"""
        lines = []
        lines.append("🔍 Não encontrei esse jogo com segurança.")
        lines.append("─────────────────────────────────────────────────────────")
        lines.append("")
        lines.append("Você quis dizer:")
        lines.append("")
        
        if match_result["team1"].get("ambiguous"):
            for suggestion in match_result["team1"].get("suggestions", [])[:3]:
                lines.append(f"  • {suggestion}")
        if match_result["team2"].get("ambiguous"):
            for suggestion in match_result["team2"].get("suggestions", [])[:3]:
                lines.append(f"  • {suggestion}")
        
        lines.append("")
        lines.append("💡 Dica: Use o nome completo do time:")
        lines.append("  • Atlético-MG x RB Bragantino ✓")
        lines.append("  • Flamengo x Internacional ✓")
        lines.append("")
        lines.append("⚠️ Esta consulta NÃO consumiu sua cota.")
        
        return "\n".join(lines)
    
    def _format_team_not_found(self, team_a: str, team_b: str, match_result: Dict) -> str:
        """Format message when teams cannot be found"""
        lines = []
        lines.append("🔍 Não encontrei esse jogo com segurança.")
        lines.append("─────────────────────────────────────────────────────────")
        lines.append("")
        lines.append("Verifique se os nomes dos times estão corretos.")
        lines.append("")
        lines.append("💡 Dica: Use o nome completo do time:")
        lines.append("  • Arsenal x Chelsea ✓")
        lines.append("  • Man United vs Liverpool ✓")
        lines.append("  • Benfica x Porto ✓")
        lines.append("")
        lines.append("Digite /help para ver todos os comandos disponíveis.")
        lines.append("")
        lines.append("⚠️ Esta consulta NÃO consumiu sua cota.")
        
        return "\n".join(lines)
    
    def _validate_fixtures(self, fixtures: List[Dict], team_id: int, required: int) -> Dict:
        """Validate fixtures - ensure data quality before analysis
        
        Pipeline "Last N Verified":
        1. Filter only official matches (exclude friendlies, charity, test matches)
        2. Validate date, score, teams
        3. Filter only FINISHED games (FT, AET, PEN)
        4. Sort by date (most recent first) - DETERMINISTIC
        5. Take exactly required number
        
        CRITICAL: This function must be DETERMINISTIC - same input = same output
        No randomness, no user-specific behavior, no cache issues.
        """
        from datetime import datetime
        
        result = {
            "valid": False,
            "fixtures": [],
            "fixture_ids": [],  # For debugging - list of fixture IDs used
            "errors": [],
            "date_range": {"start": None, "end": None},
            "excluded_friendlies": 0,
            "excluded_unfinished": 0,
            "excluded_no_score": 0,
            "total_raw": len(fixtures) if fixtures else 0
        }
        
        if not fixtures:
            result["errors"].append("Nenhum jogo encontrado")
            logger.warning(f"[VALIDATE] No fixtures provided for team_id={team_id}")
            return result
        
        logger.info(f"[VALIDATE] Processing {len(fixtures)} raw fixtures for team_id={team_id}, required={required}")
        
        # Keywords to identify non-official matches
        FRIENDLY_KEYWORDS = [
            "friendly", "amistoso", "charity", "beneficente", "test match",
            "exhibition", "testimonial", "memorial", "trophy friendly",
            "pre-season", "pre season", "preseason", "club friendly"
        ]
        
        # Competition types to exclude
        EXCLUDED_TYPES = ["friendly", "club friendly", "international friendly"]
        
        # Valid final statuses
        FINAL_STATUSES = ["FT", "AET", "PEN"]
        
        valid_fixtures = []
        seen_ids = set()
        excluded_friendly = 0
        excluded_unfinished = 0
        excluded_no_score = 0
        
        for fixture in fixtures:
            fixture_data = fixture.get("fixture", {})
            fixture_id = fixture_data.get("id")
            fixture_date = fixture_data.get("date")
            fixture_status = fixture_data.get("status", {}).get("short", "")
            goals = fixture.get("goals", {})
            teams = fixture.get("teams", {})
            league = fixture.get("league", {})
            
            # ═══════════════════════════════════════════════════════════════
            # VALIDATION 1: Check for duplicates
            # ═══════════════════════════════════════════════════════════════
            if fixture_id in seen_ids:
                continue
            seen_ids.add(fixture_id)
            
            # ═══════════════════════════════════════════════════════════════
            # VALIDATION 2: Filter out friendlies and non-official matches
            # ═══════════════════════════════════════════════════════════════
            league_name = league.get("name", "").lower()
            league_type = league.get("type", "").lower()
            
            # Check if it's a friendly by league type
            if league_type in EXCLUDED_TYPES:
                excluded_friendly += 1
                logger.debug(f"[VALIDATE] Excluded friendly (type): {fixture_id} - {league_name}")
                continue
            
            # Check if it's a friendly by league name
            is_friendly = any(keyword in league_name for keyword in FRIENDLY_KEYWORDS)
            if is_friendly:
                excluded_friendly += 1
                logger.debug(f"[VALIDATE] Excluded friendly (name): {fixture_id} - {league_name}")
                continue
            
            # ═══════════════════════════════════════════════════════════════
            # VALIDATION 3: Check date is valid and not in future
            # ═══════════════════════════════════════════════════════════════
            if not fixture_date:
                continue
            
            try:
                game_date = datetime.fromisoformat(fixture_date.replace("Z", "+00:00"))
                if game_date > datetime.now(game_date.tzinfo):
                    continue  # Skip future games
            except:
                continue
            
            # ═══════════════════════════════════════════════════════════════
            # VALIDATION 4: Check game is FINISHED (FT, AET, PEN only)
            # ═══════════════════════════════════════════════════════════════
            if fixture_status not in FINAL_STATUSES:
                excluded_unfinished += 1
                logger.debug(f"[VALIDATE] Excluded unfinished: {fixture_id} - status={fixture_status}")
                continue
            
            # ═══════════════════════════════════════════════════════════════
            # VALIDATION 5: Check goals are valid (not None)
            # ═══════════════════════════════════════════════════════════════
            home_goals = goals.get("home")
            away_goals = goals.get("away")
            if home_goals is None or away_goals is None:
                excluded_no_score += 1
                logger.debug(f"[VALIDATE] Excluded no score: {fixture_id}")
                continue
            
            # ═══════════════════════════════════════════════════════════════
            # VALIDATION 6: Check teams are valid
            # ═══════════════════════════════════════════════════════════════
            home_team = teams.get("home", {})
            away_team = teams.get("away", {})
            if not home_team.get("id") or not away_team.get("id"):
                continue
            
            # Passed all validations - this is an official finished match
            valid_fixtures.append(fixture)
        
        result["excluded_friendlies"] = excluded_friendly
        result["excluded_unfinished"] = excluded_unfinished
        result["excluded_no_score"] = excluded_no_score
        
        logger.info(f"[VALIDATE] After filtering: {len(valid_fixtures)} valid fixtures (excluded: {excluded_friendly} friendlies, {excluded_unfinished} unfinished, {excluded_no_score} no score)")
        
        # ═══════════════════════════════════════════════════════════════
        # SORT BY DATE (most recent first) - DETERMINISTIC
        # Secondary sort by fixture_id for absolute determinism
        # ═══════════════════════════════════════════════════════════════
        valid_fixtures.sort(
            key=lambda x: (x.get("fixture", {}).get("date", ""), x.get("fixture", {}).get("id", 0)),
            reverse=True
        )
        
        # Take exactly the required number
        final_fixtures = valid_fixtures[:required]
        
        # Store fixture IDs for debugging/verification
        result["fixture_ids"] = [f.get("fixture", {}).get("id") for f in final_fixtures]
        
        # Log the fixtures being used
        logger.info(f"[VALIDATE] Using {len(final_fixtures)} fixtures: {result['fixture_ids']}")
        for i, f in enumerate(final_fixtures):
            fd = f.get("fixture", {})
            teams = f.get("teams", {})
            goals = f.get("goals", {})
            logger.info(f"[VALIDATE] #{i+1}: ID={fd.get('id')} | {fd.get('date', '')[:10]} | {teams.get('home', {}).get('name', '?')} {goals.get('home', '?')}-{goals.get('away', '?')} {teams.get('away', {}).get('name', '?')} | Status={fd.get('status', {}).get('short', '?')}")
        
        if len(final_fixtures) < required:
            result["errors"].append(f"Apenas {len(final_fixtures)} jogos válidos encontrados (necessário: {required})")
            # Still allow analysis with fewer games if we have at least 5
            if len(final_fixtures) >= 5:
                result["valid"] = True
                result["fixtures"] = final_fixtures
        else:
            result["valid"] = True
            result["fixtures"] = final_fixtures
        
        # Calculate date range
        if final_fixtures:
            dates = []
            for f in final_fixtures:
                try:
                    d = datetime.fromisoformat(f.get("fixture", {}).get("date", "").replace("Z", "+00:00"))
                    dates.append(d)
                except:
                    pass
            if dates:
                result["date_range"]["start"] = min(dates).strftime("%d/%m/%Y")
                result["date_range"]["end"] = max(dates).strftime("%d/%m/%Y")
        
        return result
    
    def _format_data_error(self, team_a: str, team_b: str, val_a: Dict, val_b: Dict) -> str:
        """Format error message when data validation fails"""
        lines = []
        lines.append("⚠️ Dados Insuficientes")
        lines.append("─────────────────────────────────────────────────────────")
        lines.append("")
        lines.append(f"Não foi possível obter dados suficientes para análise.")
        lines.append("")
        
        if val_a["errors"]:
            lines.append(f"  {team_a}: {', '.join(val_a['errors'])}")
        if val_b["errors"]:
            lines.append(f"  {team_b}: {', '.join(val_b['errors'])}")
        
        lines.append("")
        lines.append("💡 Tente novamente em alguns minutos ou verifique os nomes dos times.")
        
        return "\n".join(lines)
    
    async def _analyze_team(self, parsed: Dict, user: User) -> str:
        """Analyze team statistics"""
        team_name = parsed["team"]
        n = parsed.get("n", 10)
        home_away = parsed.get("home_away", "all")
        metrics = parsed.get("metrics", ["over_2_5", "btts", "win_rate"])
        
        # Resolve team
        team = await self.api.resolve_team(team_name)
        if not team:
            return f"❌ Time '{team_name}' não encontrado. Verifique a digitação."
        
        # Get fixtures
        fixtures = await self.api.get_team_fixtures(team["id"], n * 2)
        
        # Filter by venue
        filtered = self._filter_fixtures_by_venue(fixtures, team["id"], home_away)
        filtered = filtered[-n:]
        
        # Generate analysis
        return self._generate_team_analysis(team, filtered, home_away, metrics)
    
    def _filter_fixtures_by_venue(self, fixtures: List[Dict], team_id: int, venue: str) -> List[Dict]:
        """Filter fixtures by home/away/all"""
        if venue == "all":
            return fixtures
        
        filtered = []
        for fixture in fixtures:
            teams = fixture.get("teams", {})
            if venue == "home" and teams.get("home", {}).get("id") == team_id:
                filtered.append(fixture)
            elif venue == "away" and teams.get("away", {}).get("id") == team_id:
                filtered.append(fixture)
        
        return filtered
    
    def _generate_match_analysis(self, team_a: Dict, team_b: Dict, fixtures_a: List[Dict], fixtures_b: List[Dict], split_mode: str, markets: List[str] = None, odds: List[str] = None, date_range_a: Dict = None, date_range_b: Dict = None, confidence: float = 1.0) -> str:
        """Generate premium match analysis - Bloomberg/TradingView style"""
        from datetime import datetime
        
        markets = markets or []
        odds = odds or []
        date_range_a = date_range_a or {}
        date_range_b = date_range_b or {}
        
        # Calculate statistics
        stats_a = self._calculate_team_stats(fixtures_a, team_a["id"])
        stats_b = self._calculate_team_stats(fixtures_b, team_b["id"])
        
        # Build premium output
        lines = []
        
        # ═══════════════════════════════════════════════════════════════
        # DATA VERIFICATION BLOCK - Premium confirmation
        # ═══════════════════════════════════════════════════════════════
        games_a = len(fixtures_a)
        games_b = len(fixtures_b)
        lines.append("✅ Dados verificados: últimos 10 jogos de cada equipe")
        lines.append(f"   {team_a['name']}: {games_a} jogos oficiais • {team_b['name']}: {games_b} jogos oficiais")
        if date_range_a.get("start") and date_range_b.get("start"):
            lines.append(f"   Período: {date_range_a.get('end', '')} → {date_range_a.get('start', '')}")
        lines.append("")
        
        # ═══════════════════════════════════════════════════════════════
        # HEADER - Casual, humano e elegante
        # ═══════════════════════════════════════════════════════════════
        lines.append(f"⚽ {team_a['name']} vs {team_b['name']}")
        lines.append(f"📊 Baseado nos últimos {len(fixtures_a)} jogos de cada equipe")
        
        # Show user's markets and odds if provided
        if markets or odds:
            lines.append("")
            if markets:
                lines.append(f"🎯 Seu mercado: {' + '.join(markets)}")
            if odds:
                lines.append(f"💰 Odd informada: {', '.join(odds)}")
        
        lines.append("")
        
        # ═══════════════════════════════════════════════════════════════
        # FORM SECTION - Use first 5 (most recent) since list is sorted newest first
        # ═══════════════════════════════════════════════════════════════
        form_a = self._get_form_string(fixtures_a[:5], team_a['id'])
        form_b = self._get_form_string(fixtures_b[:5], team_b['id'])
        
        lines.append("📈 Forma Recente")
        lines.append("─────────────────────────────────────────────────────────")
        lines.append(f"  {team_a['name'][:15]:<15}  {form_a}")
        lines.append(f"  {team_b['name'][:15]:<15}  {form_b}")
        lines.append("")
        
        # ═══════════════════════════════════════════════════════════════
        # STATISTICS GRID
        # ═══════════════════════════════════════════════════════════════
        avg_over_2_5 = (stats_a['over_2_5'] + stats_b['over_2_5']) / 2
        avg_over_1_5 = (stats_a['over_1_5'] + stats_b['over_1_5']) / 2
        avg_btts = (stats_a['btts'] + stats_b['btts']) / 2
        
        lines.append("📊 Estatísticas (últimos 10 jogos)")
        lines.append("─────────────────────────────────────────────────────────")
        lines.append(f"  {'Mercado':<14} {team_a['name'][:10]:<12} {team_b['name'][:10]:<12} {'Média':<10}")
        lines.append(f"  {'─'*50}")
        lines.append(f"  {'Over 2.5 (FT)':<14} {stats_a['over_2_5']:>6.0f}%      {stats_b['over_2_5']:>6.0f}%      {avg_over_2_5:>6.0f}%")
        lines.append(f"  {'Over 1.5 (FT)':<14} {stats_a['over_1_5']:>6.0f}%      {stats_b['over_1_5']:>6.0f}%      {avg_over_1_5:>6.0f}%")
        lines.append(f"  {'BTTS (FT)':<14} {stats_a['btts']:>6.0f}%      {stats_b['btts']:>6.0f}%      {avg_btts:>6.0f}%")
        lines.append(f"  {'Média Gols':<14} {stats_a['avg_total_goals']:>6.1f}       {stats_b['avg_total_goals']:>6.1f}       {(stats_a['avg_total_goals']+stats_b['avg_total_goals'])/2:>6.1f}")
        lines.append(f"  {'Gols Marcados':<14} {stats_a['avg_goals_for']:>6.1f}       {stats_b['avg_goals_for']:>6.1f}")
        lines.append(f"  {'Gols Sofridos':<14} {stats_a['avg_goals_against']:>6.1f}       {stats_b['avg_goals_against']:>6.1f}")
        lines.append(f"  {'Vitórias':<14} {stats_a['win_rate']:>6.0f}%      {stats_b['win_rate']:>6.0f}%")
        lines.append(f"  {'Clean Sheet':<14} {stats_a['clean_sheet_rate']:>6.0f}%      {stats_b['clean_sheet_rate']:>6.0f}%")
        lines.append("")
        
        # Add legend for form
        lines.append("  📝 Legenda: V=Vitória, E=Empate, D=Derrota")
        lines.append("")
        
        # ═══════════════════════════════════════════════════════════════
        # BEST BETS - PROBABILITY BARS
        # ═══════════════════════════════════════════════════════════════
        lines.append("🎯 Apostas Recomendadas")
        lines.append("─────────────────────────────────────────────────────────")
        
        # Calculate probabilities (capped at 99%)
        team_a_scores = self._cap_probability(100 - stats_a.get("failed_to_score_rate", 0))
        team_b_scores = self._cap_probability(100 - stats_b.get("failed_to_score_rate", 0))
        
        bets = [
            ("Over 1.5 Gols", self._cap_probability(avg_over_1_5)),
            ("Over 2.5 Gols", self._cap_probability(avg_over_2_5)),
            ("Under 2.5 Gols", self._cap_probability(100 - avg_over_2_5)),
            ("Ambos Marcam", self._cap_probability(avg_btts)),
            ("Ambos Não Marcam", self._cap_probability(100 - avg_btts)),
            (f"{team_a['name'][:12]} Marca", team_a_scores),
            (f"{team_b['name'][:12]} Marca", team_b_scores),
        ]
        
        # Sort by probability
        bets.sort(key=lambda x: x[1], reverse=True)
        
        for bet_name, prob in bets[:7]:
            bar = self._create_probability_bar(prob)
            conf = "ALTA" if prob >= 65 else "MÉDIA" if prob >= 50 else "BAIXA"
            # Calculate fair odds: odd_justa = 1 / (prob / 100)
            fair_odds = round(100 / prob, 2) if prob > 0 else 0
            fair_odds_str = f"Odd justa: {fair_odds:.2f}" if fair_odds > 0 else ""
            lines.append(f"  {bet_name:<22} {prob:>5.0f}%  {bar}  [{conf}] {fair_odds_str}")
        
        lines.append("")
        
        # ═══════════════════════════════════════════════════════════════
        # ODD VALUE ANALYSIS (if user provided odds)
        # ═══════════════════════════════════════════════════════════════
        if odds and markets:
            lines.append("💰 Análise de Valor")
            lines.append("─────────────────────────────────────────────────────────")
            
            for odd_str in odds:
                try:
                    odd_value = float(odd_str.replace(',', '.'))
                    implied_prob = 100 / odd_value
                    
                    # Find matching market probability
                    market_prob = None
                    for market in markets:
                        market_lower = market.lower()
                        if "over 2.5" in market_lower:
                            market_prob = avg_over_2_5
                        elif "over 1.5" in market_lower:
                            market_prob = avg_over_1_5
                        elif "under 2.5" in market_lower:
                            market_prob = 100 - avg_over_2_5
                        elif "ambos marcam" in market_lower or "btts" in market_lower:
                            if "não" in market_lower or "no" in market_lower:
                                market_prob = 100 - avg_btts
                            else:
                                market_prob = avg_btts
                    
                    if market_prob:
                        fair_odds = 100 / market_prob if market_prob > 0 else 1
                        edge = ((odd_value - fair_odds) / fair_odds) * 100 if fair_odds > 0 else 0
                        value = market_prob - implied_prob
                        
                        if edge >= 5:
                            lines.append("")
                            lines.append("  💎 ═══════════════════════════════════════════════")
                            lines.append("  💎 OPORTUNIDADE DE VALOR DETECTADA NESTE MERCADO!")
                            lines.append("  💎 ═══════════════════════════════════════════════")
                            lines.append(f"  ✅ Odd {odd_value:.2f} tem VALOR!")
                            lines.append(f"     Prob. implícita: {implied_prob:.0f}% | Nossa análise: {market_prob:.0f}%")
                            lines.append(f"     Edge estimado: +{edge:.1f}%")
                            lines.append("")
                        elif value > -5:
                            lines.append(f"  ⚠️ Odd {odd_value:.2f} é JUSTA (Prob. implícita: {implied_prob:.0f}% | Nossa: {market_prob:.0f}%)")
                        else:
                            lines.append(f"  ❌ Odd {odd_value:.2f} SEM VALOR (Prob. implícita: {implied_prob:.0f}% | Nossa: {market_prob:.0f}%)")
                    else:
                        lines.append(f"  📊 Odd informada: {odd_value:.2f} (Prob. implícita: {implied_prob:.0f}%)")
                except:
                    pass
            
            lines.append("")
        
        # ═══════════════════════════════════════════════════════════════
        # AI INSIGHT BOX
        # ═══════════════════════════════════════════════════════════════
        lines.append("💡 Insight de Mercado")
        lines.append("─────────────────────────────────────────────────────────")
        
        insights = self._generate_market_insights(stats_a, stats_b, team_a['name'], team_b['name'])
        for insight in insights[:2]:
            lines.append(f"  {insight}")
        
        lines.append("")
        
        # ═══════════════════════════════════════════════════════════════
        # FOOTER
        # ═══════════════════════════════════════════════════════════════
        timestamp = datetime.utcnow().strftime("%H:%M UTC")
        lines.append("─────────────────────────────────────────────────────────")
        lines.append(f"  BetFaro | {timestamp}")
        lines.append("─────────────────────────────────────────────────────────")
        
        return "\n".join(lines)
    
    def _cap_probability(self, prob: float) -> float:
        """Cap probability at 99% maximum - never show 100%"""
        if prob >= 100:
            return 99
        if prob <= 0:
            return 1
        return min(99, max(1, prob))
    
    def _create_probability_bar(self, probability: float) -> str:
        """Create ASCII probability bar"""
        prob = self._cap_probability(probability)
        filled = int(prob / 10)
        empty = 10 - filled
        return "[" + "=" * filled + " " * empty + "]"
    
    def _generate_market_insights(self, stats_a: Dict, stats_b: Dict, name_a: str, name_b: str) -> List[str]:
        """Generate market insights in PT-BR"""
        insights = []
        
        avg_over_2_5 = (stats_a.get("over_2_5", 0) + stats_b.get("over_2_5", 0)) / 2
        avg_btts = (stats_a.get("btts", 0) + stats_b.get("btts", 0)) / 2
        
        if avg_over_2_5 >= 60:
            insights.append("Padrão de muitos gols detectado. Over 2.5 com valor positivo.")
        elif avg_over_2_5 <= 40:
            insights.append("Tendência de poucos gols. Under 2.5 apresenta boas odds.")
        
        if avg_btts >= 60:
            insights.append("Ambos os times marcam com frequência. BTTS Sim recomendado.")
        elif avg_btts <= 35:
            insights.append("Tendência de clean sheet. Considere BTTS Não.")
        
        if stats_a.get("win_rate", 0) >= 60 and stats_b.get("win_rate", 0) <= 40:
            insights.append(f"{name_a} em ótima fase. Vitória do mandante com valor.")
        elif stats_b.get("win_rate", 0) >= 60 and stats_a.get("win_rate", 0) <= 40:
            insights.append(f"{name_b} em boa forma. Vitória do visitante pode ter valor.")
        
        if not insights:
            insights.append("Jogo equilibrado. Considere apostas combinadas.")
        
        return insights
    
    def _get_best_picks(self, stats_a: Dict, stats_b: Dict, ht_a: Dict, ht_b: Dict, name_a: str, name_b: str) -> List[str]:
        """Get best picks sorted by probability"""
        picks = []
        
        # Calculate combined probabilities
        avg_over_2_5 = (stats_a.get("over_2_5", 0) + stats_b.get("over_2_5", 0)) / 2
        avg_under_2_5 = 100 - avg_over_2_5
        avg_btts = (stats_a.get("btts", 0) + stats_b.get("btts", 0)) / 2
        avg_btts_no = 100 - avg_btts
        avg_over_1_5 = (stats_a.get("over_1_5", 0) + stats_b.get("over_1_5", 0)) / 2
        
        team_a_score = 100 - stats_a.get("failed_to_score_rate", 0)
        team_b_score = 100 - stats_b.get("failed_to_score_rate", 0)
        
        # Create picks with probabilities
        all_picks = [
            (avg_over_2_5, f"⚽ **Over 2.5** → {avg_over_2_5:.0f}%", "high" if avg_over_2_5 >= 60 else "medium" if avg_over_2_5 >= 45 else "low"),
            (avg_under_2_5, f"⚽ **Under 2.5** → {avg_under_2_5:.0f}%", "high" if avg_under_2_5 >= 60 else "medium" if avg_under_2_5 >= 45 else "low"),
            (avg_btts, f"🤝 **BTTS Sim** → {avg_btts:.0f}%", "high" if avg_btts >= 60 else "medium" if avg_btts >= 45 else "low"),
            (avg_btts_no, f"🚫 **BTTS Não** → {avg_btts_no:.0f}%", "high" if avg_btts_no >= 60 else "medium" if avg_btts_no >= 45 else "low"),
            (avg_over_1_5, f"⚽ **Over 1.5** → {avg_over_1_5:.0f}%", "high" if avg_over_1_5 >= 70 else "medium" if avg_over_1_5 >= 55 else "low"),
            (team_a_score, f"🎯 **{name_a} marca** → {team_a_score:.0f}%", "high" if team_a_score >= 75 else "medium" if team_a_score >= 60 else "low"),
            (team_b_score, f"🎯 **{name_b} marca** → {team_b_score:.0f}%", "high" if team_b_score >= 75 else "medium" if team_b_score >= 60 else "low"),
        ]
        
        # Sort by probability and filter high confidence
        all_picks.sort(key=lambda x: x[0], reverse=True)
        
        for prob, text, confidence in all_picks:
            if confidence == "high":
                picks.append(f"🟢 {text}")
            elif confidence == "medium":
                picks.append(f"� {text}")
            else:
                picks.append(f"� {text}")
        
        return picks
    
    def _generate_insights(self, stats_a: Dict, stats_b: Dict, name_a: str, name_b: str, fixtures_a: List, fixtures_b: List) -> List[str]:
        """Generate quick insights about the match"""
        insights = []
        
        # Over/Under trend
        if stats_a.get("over_2_5", 0) >= 60 and stats_b.get("over_2_5", 0) >= 60:
            insights.append(f"Ambos times com alto índice de Over 2.5 - jogo com potencial de gols")
        elif stats_a.get("over_2_5", 0) <= 40 and stats_b.get("over_2_5", 0) <= 40:
            insights.append(f"Ambos times com baixo índice de gols - considere Under 2.5")
        
        # BTTS trend
        if stats_a.get("btts", 0) >= 60 and stats_b.get("btts", 0) >= 60:
            insights.append(f"Alta probabilidade de ambos marcarem")
        
        # Clean sheet
        if stats_a.get("clean_sheet_rate", 0) >= 40:
            insights.append(f"{name_a} mantém clean sheet em {stats_a['clean_sheet_rate']:.0f}% dos jogos")
        if stats_b.get("clean_sheet_rate", 0) >= 40:
            insights.append(f"{name_b} mantém clean sheet em {stats_b['clean_sheet_rate']:.0f}% dos jogos")
        
        # Recent form - use first 5 (most recent) since list is sorted newest first
        if len(fixtures_a) >= 5:
            recent_wins_a = sum(1 for f in fixtures_a[:5] if self._get_result(f, fixtures_a[0].get("teams", {}).get("home", {}).get("id", 0)) == "W")
            if recent_wins_a >= 4:
                insights.append(f"{name_a} em excelente fase - {recent_wins_a}/5 vitórias")
        
        return insights
    
    def _get_result(self, fixture: Dict, team_id: int) -> str:
        """Get result for a team in a fixture"""
        teams = fixture.get("teams", {})
        goals = fixture.get("goals", {})
        home_goals = goals.get("home", 0)
        away_goals = goals.get("away", 0)
        
        if teams.get("home", {}).get("id") == team_id:
            return "W" if home_goals > away_goals else "D" if home_goals == away_goals else "L"
        else:
            return "W" if away_goals > home_goals else "D" if away_goals == home_goals else "L"
    
    def _generate_team_analysis(self, team: Dict, fixtures: List[Dict], home_away: str, metrics: List[str]) -> str:
        """Generate team statistics analysis - premium trader terminal style"""
        from datetime import datetime
        
        if not fixtures:
            return self._format_error(f"Insufficient data for {team['name']}")
        
        stats = self._calculate_team_stats(fixtures, team["id"])
        
        lines = []
        
        # Header
        lines.append("┌─────────────────────────────────────────────────────────┐")
        lines.append("│  TEAM INTELLIGENCE                                      │")
        lines.append("├─────────────────────────────────────────────────────────┤")
        lines.append(f"│  {team['name'].upper():^55} │")
        lines.append(f"│  Sample: {len(fixtures)} matches | Filter: {home_away.upper():<20}     │")
        lines.append("└─────────────────────────────────────────────────────────┘")
        lines.append("")
        
        # Form - use first 5 (most recent) since list is sorted newest first
        form = self._get_form_string(fixtures[:5], team['id'])
        lines.append("RECENT FORM (Last 5)")
        lines.append("─────────────────────────────────────────────────────────")
        lines.append(f"  {form}")
        lines.append("")
        
        # Statistics Grid
        lines.append("STATISTICS")
        lines.append("─────────────────────────────────────────────────────────")
        lines.append(f"  {'METRIC':<20} {'VALUE':<15} {'RATING':<10}")
        lines.append(f"  {'─'*45}")
        
        stat_items = [
            ("Over 2.5", stats['over_2_5'], "%"),
            ("Over 1.5", stats['over_1_5'], "%"),
            ("BTTS", stats['btts'], "%"),
            ("Win Rate", stats['win_rate'], "%"),
            ("Clean Sheet", stats['clean_sheet_rate'], "%"),
            ("Avg Goals", stats['avg_total_goals'], ""),
            ("Goals For", stats['avg_goals_for'], ""),
            ("Goals Against", stats['avg_goals_against'], ""),
        ]
        
        for name, value, suffix in stat_items:
            if suffix == "%":
                rating = "HIGH" if value >= 60 else "MED" if value >= 40 else "LOW"
                lines.append(f"  {name:<20} {value:>6.0f}%        [{rating}]")
            else:
                lines.append(f"  {name:<20} {value:>6.1f}")
        
        lines.append("")
        
        # Recent Results
        lines.append("RECENT RESULTS")
        lines.append("─────────────────────────────────────────────────────────")
        
        for fixture in fixtures[:5]:
            teams_data = fixture.get("teams", {})
            goals = fixture.get("goals", {})
            home_team = teams_data.get("home", {})
            away_team = teams_data.get("away", {})
            home_goals = goals.get("home", 0)
            away_goals = goals.get("away", 0)
            
            if home_team.get("id") == team["id"]:
                result = "W" if home_goals > away_goals else "D" if home_goals == away_goals else "L"
                opponent = away_team.get('name', 'Unknown')[:15]
                score = f"{home_goals}-{away_goals}"
                venue = "H"
            else:
                result = "W" if away_goals > home_goals else "D" if away_goals == home_goals else "L"
                opponent = home_team.get('name', 'Unknown')[:15]
                score = f"{away_goals}-{home_goals}"
                venue = "A"
            
            lines.append(f"  [{result}] {score}  vs {opponent:<15} ({venue})")
        
        lines.append("")
        
        # Footer
        timestamp = datetime.utcnow().strftime("%H:%M UTC")
        lines.append("─────────────────────────────────────────────────────────")
        lines.append(f"  Generated by BetFaro | {timestamp}")
        lines.append("─────────────────────────────────────────────────────────")
        
        return "\n".join(lines)
    
    def _calculate_team_stats(self, fixtures: List[Dict], team_id: int) -> Dict:
        """Calculate team statistics from EXACTLY the fixtures provided.
        
        CRITICAL RULES:
        - Over/Under 2.5 (FT) = total goals of the MATCH (home + away), NOT team's goals
        - BTTS = home_goals > 0 AND away_goals > 0 (both teams scored in the match)
        - Win/Draw/Loss = from perspective of team_id
        - All stats calculated from the SAME fixture set
        
        Returns dict with:
        - over_0_5, over_1_5, over_2_5, over_3_5: % of matches with total goals > X
        - btts: % of matches where both teams scored
        - win_rate, draw_rate, loss_rate: % from team's perspective
        - clean_sheet_rate: % where team conceded 0
        - failed_to_score_rate: % where team scored 0
        - avg_goals_for: average goals scored BY the team
        - avg_goals_against: average goals conceded BY the team
        - avg_total_goals: average total goals per match (home + away)
        """
        if not fixtures:
            return {
                "over_0_5": 0, "over_1_5": 0, "over_2_5": 0, "over_3_5": 0,
                "btts": 0, "win_rate": 0, "draw_rate": 0, "loss_rate": 0,
                "clean_sheet_rate": 0, "failed_to_score_rate": 0,
                "avg_goals_for": 0, "avg_goals_against": 0, "avg_total_goals": 0,
                "fixtures_used": 0
            }
        
        # Counters
        over_0_5_count = 0
        over_1_5_count = 0
        over_2_5_count = 0
        over_3_5_count = 0
        btts_count = 0
        wins = 0
        draws = 0
        losses = 0
        clean_sheets = 0
        failed_to_score = 0
        total_goals_for = 0
        total_goals_against = 0
        total_match_goals = 0
        
        # Log fixtures being analyzed for debugging
        logger.info(f"[STATS] Calculating stats for team_id={team_id} from {len(fixtures)} fixtures")
        
        for i, fixture in enumerate(fixtures):
            teams = fixture.get("teams", {})
            goals = fixture.get("goals", {})
            home_team = teams.get("home", {})
            away_team = teams.get("away", {})
            fixture_data = fixture.get("fixture", {})
            
            # Get goals - ensure they are integers
            home_goals = goals.get("home")
            away_goals = goals.get("away")
            
            # Skip if goals are None
            if home_goals is None or away_goals is None:
                logger.warning(f"[STATS] Skipping fixture {fixture_data.get('id')} - missing goals")
                continue
            
            home_goals = int(home_goals)
            away_goals = int(away_goals)
            
            # TOTAL GOALS OF THE MATCH (for Over/Under calculations)
            match_total_goals = home_goals + away_goals
            total_match_goals += match_total_goals
            
            # Determine if team was home or away
            is_home = home_team.get("id") == team_id
            
            # Goals FOR and AGAINST from team's perspective
            if is_home:
                goals_for = home_goals
                goals_against = away_goals
            else:
                goals_for = away_goals
                goals_against = home_goals
            
            total_goals_for += goals_for
            total_goals_against += goals_against
            
            # ═══════════════════════════════════════════════════════════════
            # OVER/UNDER - Based on MATCH TOTAL (home + away), NOT team's goals
            # ═══════════════════════════════════════════════════════════════
            if match_total_goals > 0:
                over_0_5_count += 1
            if match_total_goals > 1:
                over_1_5_count += 1
            if match_total_goals > 2:
                over_2_5_count += 1
            if match_total_goals > 3:
                over_3_5_count += 1
            
            # ═══════════════════════════════════════════════════════════════
            # BTTS - Both teams scored (home > 0 AND away > 0)
            # ═══════════════════════════════════════════════════════════════
            if home_goals > 0 and away_goals > 0:
                btts_count += 1
            
            # ═══════════════════════════════════════════════════════════════
            # WIN/DRAW/LOSS - From team's perspective
            # ═══════════════════════════════════════════════════════════════
            if goals_for > goals_against:
                wins += 1
            elif goals_for == goals_against:
                draws += 1
            else:
                losses += 1
            
            # ═══════════════════════════════════════════════════════════════
            # CLEAN SHEET / FAILED TO SCORE
            # ═══════════════════════════════════════════════════════════════
            if goals_against == 0:
                clean_sheets += 1
            if goals_for == 0:
                failed_to_score += 1
            
            # Debug log each fixture
            fixture_date = fixture_data.get("date", "")[:10]
            result = "W" if goals_for > goals_against else "D" if goals_for == goals_against else "L"
            logger.debug(f"[STATS] #{i+1} {fixture_date} | {home_team.get('name','?')} {home_goals}-{away_goals} {away_team.get('name','?')} | Team {'H' if is_home else 'A'} | {result} | Total={match_total_goals} | BTTS={'Y' if home_goals > 0 and away_goals > 0 else 'N'}")
        
        # Calculate percentages and averages
        total = len(fixtures)
        if total == 0:
            return {
                "over_0_5": 0, "over_1_5": 0, "over_2_5": 0, "over_3_5": 0,
                "btts": 0, "win_rate": 0, "draw_rate": 0, "loss_rate": 0,
                "clean_sheet_rate": 0, "failed_to_score_rate": 0,
                "avg_goals_for": 0, "avg_goals_against": 0, "avg_total_goals": 0,
                "fixtures_used": 0
            }
        
        stats = {
            "over_0_5": (over_0_5_count / total) * 100,
            "over_1_5": (over_1_5_count / total) * 100,
            "over_2_5": (over_2_5_count / total) * 100,
            "over_3_5": (over_3_5_count / total) * 100,
            "btts": (btts_count / total) * 100,
            "win_rate": (wins / total) * 100,
            "draw_rate": (draws / total) * 100,
            "loss_rate": (losses / total) * 100,
            "clean_sheet_rate": (clean_sheets / total) * 100,
            "failed_to_score_rate": (failed_to_score / total) * 100,
            "avg_goals_for": total_goals_for / total,
            "avg_goals_against": total_goals_against / total,
            "avg_total_goals": total_match_goals / total,
            "fixtures_used": total
        }
        
        logger.info(f"[STATS] Results: Over2.5={stats['over_2_5']:.0f}% BTTS={stats['btts']:.0f}% Wins={stats['win_rate']:.0f}% AvgGoals={stats['avg_total_goals']:.1f}")
        
        return stats
    
    def _calculate_ht_stats(self, fixtures: List[Dict], team_id: int) -> Dict:
        """Calculate half-time statistics"""
        if not fixtures:
            return {"ht_over_0_5": 0, "ht_over_1_5": 0}
        
        ht_over_0_5 = 0
        ht_over_1_5 = 0
        
        for fixture in fixtures:
            # Note: API-Football doesn't provide HT goals in basic fixtures
            # This is a placeholder - would need /fixtures/statistics endpoint
            # For now, estimate based on typical distribution
            ft_goals = fixture.get("goals", {}).get("home", 0) + fixture.get("goals", {}).get("away", 0)
            
            # Rough estimation: ~60% of FT goals come in HT
            ht_goals_estimated = max(0, ft_goals - 1)
            
            if ht_goals_estimated > 0: ht_over_0_5 += 1
            if ht_goals_estimated > 1: ht_over_1_5 += 1
        
        total = len(fixtures)
        return {
            "ht_over_0_5": (ht_over_0_5 / total) * 100,
            "ht_over_1_5": (ht_over_1_5 / total) * 100
        }
    
    def _calculate_advanced_stats(self, fixtures: List[Dict]) -> Tuple[Dict, Dict]:
        """Calculate corners and cards statistics"""
        corners = {"sample": 0, "avg": 0, "over_8_5": 0, "over_9_5": 0, "over_10_5": 0}
        cards = {"sample": 0, "avg": 0, "over_3_5": 0, "over_4_5": 0}
        
        # Note: This would require /fixtures/statistics endpoint
        # For now, return empty stats
        return corners, cards
    
    def _get_result(self, fixture: Dict, team_id: int) -> str:
        """Get single match result (W/D/L) from team_id perspective
        
        CRITICAL: This must correctly determine W/D/L from the perspective of team_id
        - W = team_id scored MORE goals than opponent
        - D = team_id scored SAME goals as opponent
        - L = team_id scored FEWER goals than opponent
        """
        teams = fixture.get("teams", {})
        goals = fixture.get("goals", {})
        home_team = teams.get("home", {})
        
        # Get goals with proper None handling
        home_goals = goals.get("home")
        away_goals = goals.get("away")
        
        # Return None if goals are missing
        if home_goals is None or away_goals is None:
            return None
        
        # Convert to int to be safe
        home_goals = int(home_goals)
        away_goals = int(away_goals)
        
        # Determine if team_id was home or away
        is_home = home_team.get("id") == team_id
        
        # Calculate goals FOR and AGAINST from team_id perspective
        if is_home:
            goals_for = home_goals
            goals_against = away_goals
        else:
            goals_for = away_goals
            goals_against = home_goals
        
        # Determine result from team_id perspective
        if goals_for > goals_against:
            return "W"
        elif goals_for == goals_against:
            return "D"
        else:
            return "L"
    
    def _get_form_string(self, fixtures: List[Dict], team_id: int) -> str:
        """Get form string for last games using _get_result
        
        Returns PT-BR format: V (Vitória), E (Empate), D (Derrota)
        """
        form = []
        
        # Map W/D/L to PT-BR V/E/D
        result_map = {
            "W": "V",  # Vitória
            "D": "E",  # Empate
            "L": "D"   # Derrota
        }
        
        for fixture in fixtures:
            result = self._get_result(fixture, team_id)
            if result:
                # Convert to PT-BR
                pt_result = result_map.get(result, result)
                form.append(pt_result)
                
                # Debug log for verification
                teams = fixture.get("teams", {})
                goals = fixture.get("goals", {})
                home_team = teams.get("home", {})
                away_team = teams.get("away", {})
                fixture_date = fixture.get("fixture", {}).get("date", "")[:10]
                home_name = home_team.get("name", "?")
                away_name = away_team.get("name", "?")
                home_goals = goals.get("home", 0)
                away_goals = goals.get("away", 0)
                is_home = home_team.get("id") == team_id
                logger.debug(f"[FORM] {fixture_date} | {home_name} {home_goals}-{away_goals} {away_name} | TeamID {team_id} {'(H)' if is_home else '(A)'} → {result}")
        
        return " ".join(form)
    
    def _generate_main_picks(self, stats_a: Dict, stats_b: Dict, ht_a: Dict, ht_b: Dict, corners_a: Dict, corners_b: Dict, cards_a: Dict, cards_b: Dict) -> List[str]:
        """Generate main picks with probabilities"""
        picks = []
        
        # Goal picks
        avg_over_2_5 = (stats_a.get("over_2_5", 0) + stats_b.get("over_2_5", 0)) / 2
        avg_btts = (stats_a.get("btts", 0) + stats_b.get("btts", 0)) / 2
        avg_over_1_5 = (stats_a.get("over_1_5", 0) + stats_b.get("over_1_5", 0)) / 2
        
        picks.append(f"⚽ Over 2.5: {avg_over_2_5:.1f}%")
        picks.append(f"⚽ Under 2.5: {100 - avg_over_2_5:.1f}%")
        picks.append(f"⚽ BTTS SIM: {avg_btts:.1f}%")
        picks.append(f"⚽ BTTS NÃO: {100 - avg_btts:.1f}%")
        picks.append(f"⚽ Over 1.5: {avg_over_1_5:.1f}%")
        
        # HT picks
        avg_ht_over_0_5 = (ht_a.get("ht_over_0_5", 0) + ht_b.get("ht_over_0_5", 0)) / 2
        avg_ht_over_1_5 = (ht_a.get("ht_over_1_5", 0) + ht_b.get("ht_over_1_5", 0)) / 2
        
        picks.append(f"⏰ HT Over 0.5: {avg_ht_over_0_5:.1f}%")
        picks.append(f"⏰ HT Over 1.5: {avg_ht_over_1_5:.1f}%")
        
        # Double chance
        team_a_win_rate = stats_a.get("win_rate", 0)
        team_b_win_rate = stats_b.get("win_rate", 0)
        draw_rate = (stats_a.get("draw_rate", 0) + stats_b.get("draw_rate", 0)) / 2
        
        picks.append(f"🛡️ Dupla Chance 1X: {team_a_win_rate + draw_rate:.1f}%")
        picks.append(f"🛡️ Dupla Chance X2: {team_b_win_rate + draw_rate:.1f}%")
        
        # Team to score
        team_a_score_rate = 100 - stats_a.get("failed_to_score_rate", 0)
        team_b_score_rate = 100 - stats_b.get("failed_to_score_rate", 0)
        
        picks.append(f"🎯 {stats_a.get('team_name', 'Time A')} marca: {team_a_score_rate:.1f}%")
        picks.append(f"🎯 {stats_b.get('team_name', 'Time B')} marca: {team_b_score_rate:.1f}%")
        
        # Combination picks (approximate probability)
        under_3_5 = (100 - ((stats_a.get("over_3_5", 0) + stats_b.get("over_3_5", 0)) / 2))
        combo_1x_under_3_5 = (team_a_win_rate + draw_rate + under_3_5) / 2
        picks.append(f"🔥 Under 3.5 & 1X: ~{combo_1x_under_3_5:.1f}%")
        
        return picks
    
    def _generate_trends(self, fixtures_a: List[Dict], fixtures_b: List[Dict], team_a_name: str, team_b_name: str) -> List[str]:
        """Generate trend insights"""
        trends = []
        
        # Analyze patterns - use first 5 (most recent) since list is sorted newest first
        if len(fixtures_a) >= 5:
            a_over_2_5_recent = sum(1 for f in fixtures_a[:5] if (f.get("goals", {}).get("home", 0) + f.get("goals", {}).get("away", 0)) > 2)
            trends.append(f"📈 {team_a_name}: {a_over_2_5_recent}/5 últimos jogos com Over 2.5")
        
        if len(fixtures_b) >= 5:
            b_btts_recent = sum(1 for f in fixtures_b[:5] if f.get("goals", {}).get("home", 0) > 0 and f.get("goals", {}).get("away", 0) > 0)
            trends.append(f"📈 {team_b_name}: {b_btts_recent}/5 últimos jogos com BTTS")
        
        # Head to head (if available)
        # This would require additional API calls to get H2H fixtures
        
        return trends
    
    def _get_user_plan(self, user: User) -> str:
        """Get user's plan safely"""
        plan = 'free'
        subscription = getattr(user, 'subscription', None)
        if subscription:
            sub_plan = getattr(subscription, 'plan', None)
            if sub_plan:
                plan = sub_plan.lower()
        return plan
    
    def _has_remaining_quota(self, user: User) -> bool:
        """Check if user has remaining quota WITHOUT consuming it"""
        from datetime import date
        
        try:
            plan = self._get_user_plan(user)
            daily_limit = self.PLAN_LIMITS.get(plan, 5)
            
            today = date.today().isoformat()
            if not hasattr(self, '_usage_cache'):
                self._usage_cache = {}
            
            user_id = getattr(user, 'id', 'anonymous')
            cache_key = f"{user_id}_{today}"
            current_usage = self._usage_cache.get(cache_key, 0)
            
            return current_usage < daily_limit
        except Exception as e:
            logger.warning(f"Error checking quota: {e}")
            return True
    
    def _consume_quota(self, user: User) -> bool:
        """Consume one quota unit - ONLY call after successful analysis"""
        from datetime import date
        
        try:
            plan = self._get_user_plan(user)
            daily_limit = self.PLAN_LIMITS.get(plan, 5)
            
            today = date.today().isoformat()
            if not hasattr(self, '_usage_cache'):
                self._usage_cache = {}
            
            user_id = getattr(user, 'id', 'anonymous')
            cache_key = f"{user_id}_{today}"
            current_usage = self._usage_cache.get(cache_key, 0)
            
            if current_usage >= daily_limit:
                return False
            
            self._usage_cache[cache_key] = current_usage + 1
            logger.info(f"Quota consumed for user {user_id}: {current_usage + 1}/{daily_limit}")
            return True
        except Exception as e:
            logger.warning(f"Error consuming quota: {e}")
            return True
    
    def _check_analysis_limit(self, user: User) -> bool:
        """DEPRECATED: Use _has_remaining_quota and _consume_quota instead"""
        return self._has_remaining_quota(user)
    
    def _format_limit_reached(self, user: User) -> str:
        """Format message when user reaches their daily analysis limit"""
        plan = 'Free'
        subscription = getattr(user, 'subscription', None)
        if subscription and getattr(subscription, 'plan', None):
            plan = subscription.plan
        
        daily_limit = self.PLAN_LIMITS.get(plan.lower(), 5)
        
        lines = []
        lines.append("⚠️ Limite Diário Atingido")
        lines.append("─────────────────────────────────────────────────────────")
        lines.append("")
        lines.append(f"Você atingiu o limite diário do seu plano ({daily_limit} análises).")
        lines.append("")
        lines.append("Faça upgrade para continuar analisando:")
        lines.append("")
        if plan.lower() == 'free':
            lines.append("  📊 Pro  → 25 análises/dia  (R$49/mês)")
            lines.append("  👑 Elite → 100 análises/dia (R$99/mês)")
        elif plan.lower() == 'pro':
            lines.append("  👑 Elite → 100 análises/dia (R$99/mês)")
        lines.append("")
        lines.append("💡 Acesse /plans para fazer upgrade agora.")
        
        return "\n".join(lines)
