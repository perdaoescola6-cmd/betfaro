"""
BetFaro Fixture Processor - CANONICAL MODULE
=============================================
Módulo único e canônico para coleta, validação e processamento de fixtures.
REGRA: Todas as análises DEVEM usar este módulo para garantir consistência.

Autor: BetFaro Engineering
Versão: 1.0.0 (Production-Grade)
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
import os

logger = logging.getLogger(__name__)

# Environment flag for audit mode
ANALYSIS_AUDIT = os.getenv("ANALYSIS_AUDIT", "false").lower() == "true"


class FixtureProcessor:
    """
    Processador canônico de fixtures.
    
    GARANTIAS:
    1. Mesmo input -> Mesmo output (determinístico)
    2. Apenas jogos oficiais (FT, AET, PEN)
    3. Sem duplicatas
    4. Ordenação determinística (date DESC, id DESC)
    5. Time participa do jogo (validação)
    """
    
    # Valid final statuses
    FINAL_STATUSES = ["FT", "AET", "PEN"]
    
    # Keywords to identify non-official matches
    FRIENDLY_KEYWORDS = [
        "friendly", "amistoso", "charity", "beneficente", "test match",
        "exhibition", "testimonial", "memorial", "trophy friendly",
        "pre-season", "pre season", "preseason", "club friendly"
    ]
    
    # Competition types to exclude
    EXCLUDED_TYPES = ["friendly", "club friendly", "international friendly"]
    
    def get_last_team_fixtures(
        self, 
        raw_fixtures: List[Dict], 
        team_id: int, 
        n: int = 10
    ) -> Dict:
        """
        FUNÇÃO CANÔNICA para obter os últimos N jogos oficiais de um time.
        
        Args:
            raw_fixtures: Lista de fixtures da API
            team_id: ID do time
            n: Número de jogos desejados (default: 10)
        
        Returns:
            Dict com:
            - valid: bool - se conseguiu obter jogos suficientes
            - fixtures: List[Dict] - lista de fixtures válidos
            - fixture_ids: List[int] - IDs dos fixtures usados
            - audit_data: Dict - dados para auditoria (se ANALYSIS_AUDIT=true)
            - errors: List[str] - erros encontrados
        
        GARANTIAS:
        1. Apenas jogos oficiais finalizados (FT, AET, PEN)
        2. Sem amistosos
        3. Sem duplicatas
        4. Time participa do jogo
        5. Ordenação determinística (date DESC, id DESC)
        6. Exatamente N jogos (ou menos se não houver)
        """
        result = {
            "valid": False,
            "fixtures": [],
            "fixture_ids": [],
            "audit_data": [],
            "errors": [],
            "stats": {
                "total_raw": len(raw_fixtures) if raw_fixtures else 0,
                "excluded_friendlies": 0,
                "excluded_unfinished": 0,
                "excluded_no_score": 0,
                "excluded_team_not_in_fixture": 0,
                "excluded_duplicates": 0,
                "excluded_future": 0
            }
        }
        
        if not raw_fixtures:
            result["errors"].append("Nenhum fixture recebido da API")
            logger.warning(f"[FIXTURE_PROCESSOR] No fixtures provided for team_id={team_id}")
            return result
        
        logger.info(f"[FIXTURE_PROCESSOR] Processing {len(raw_fixtures)} raw fixtures for team_id={team_id}, required={n}")
        
        valid_fixtures = []
        seen_ids = set()
        
        for fixture in raw_fixtures:
            fixture_data = fixture.get("fixture", {})
            fixture_id = fixture_data.get("id")
            fixture_date = fixture_data.get("date", "")
            fixture_status = fixture_data.get("status", {}).get("short", "")
            goals = fixture.get("goals", {})
            teams = fixture.get("teams", {})
            league = fixture.get("league", {})
            
            # ═══════════════════════════════════════════════════════════════
            # VALIDATION 1: Check for duplicates
            # ═══════════════════════════════════════════════════════════════
            if fixture_id is None:
                continue
            if fixture_id in seen_ids:
                result["stats"]["excluded_duplicates"] += 1
                continue
            seen_ids.add(fixture_id)
            
            # ═══════════════════════════════════════════════════════════════
            # VALIDATION 2: Check team participates in fixture
            # ═══════════════════════════════════════════════════════════════
            home_team = teams.get("home", {})
            away_team = teams.get("away", {})
            home_id = home_team.get("id")
            away_id = away_team.get("id")
            
            if team_id not in [home_id, away_id]:
                result["stats"]["excluded_team_not_in_fixture"] += 1
                logger.debug(f"[FIXTURE_PROCESSOR] Team {team_id} not in fixture {fixture_id} (home={home_id}, away={away_id})")
                continue
            
            # ═══════════════════════════════════════════════════════════════
            # VALIDATION 3: Filter out friendlies
            # ═══════════════════════════════════════════════════════════════
            league_name = league.get("name", "").lower()
            league_type = league.get("type", "").lower()
            
            if league_type in self.EXCLUDED_TYPES:
                result["stats"]["excluded_friendlies"] += 1
                continue
            
            if any(keyword in league_name for keyword in self.FRIENDLY_KEYWORDS):
                result["stats"]["excluded_friendlies"] += 1
                continue
            
            # ═══════════════════════════════════════════════════════════════
            # VALIDATION 4: Check date is valid and not in future
            # ═══════════════════════════════════════════════════════════════
            if not fixture_date:
                continue
            
            try:
                game_date = datetime.fromisoformat(fixture_date.replace("Z", "+00:00"))
                now = datetime.now(timezone.utc)
                if game_date > now:
                    result["stats"]["excluded_future"] += 1
                    continue
            except Exception as e:
                logger.debug(f"[FIXTURE_PROCESSOR] Invalid date for fixture {fixture_id}: {e}")
                continue
            
            # ═══════════════════════════════════════════════════════════════
            # VALIDATION 5: Check game is FINISHED
            # ═══════════════════════════════════════════════════════════════
            if fixture_status not in self.FINAL_STATUSES:
                result["stats"]["excluded_unfinished"] += 1
                continue
            
            # ═══════════════════════════════════════════════════════════════
            # VALIDATION 6: Check goals are valid (not None)
            # ═══════════════════════════════════════════════════════════════
            home_goals = goals.get("home")
            away_goals = goals.get("away")
            
            if home_goals is None or away_goals is None:
                result["stats"]["excluded_no_score"] += 1
                continue
            
            # ═══════════════════════════════════════════════════════════════
            # PASSED ALL VALIDATIONS - Add to valid list
            # ═══════════════════════════════════════════════════════════════
            valid_fixtures.append(fixture)
        
        logger.info(f"[FIXTURE_PROCESSOR] After filtering: {len(valid_fixtures)} valid fixtures")
        
        # ═══════════════════════════════════════════════════════════════
        # SORT BY DATE (most recent first) - DETERMINISTIC
        # Secondary sort by fixture_id for absolute determinism
        # ═══════════════════════════════════════════════════════════════
        valid_fixtures.sort(
            key=lambda x: (
                x.get("fixture", {}).get("date", ""),
                x.get("fixture", {}).get("id", 0)
            ),
            reverse=True
        )
        
        # Take exactly N fixtures
        final_fixtures = valid_fixtures[:n]
        
        # Store fixture IDs
        result["fixture_ids"] = [f.get("fixture", {}).get("id") for f in final_fixtures]
        result["fixtures"] = final_fixtures
        
        # Generate audit data if enabled
        if ANALYSIS_AUDIT or len(final_fixtures) > 0:
            result["audit_data"] = self._generate_audit_data(final_fixtures, team_id)
        
        # Determine validity
        if len(final_fixtures) >= 5:  # Minimum 5 games for analysis
            result["valid"] = True
        else:
            result["errors"].append(f"Apenas {len(final_fixtures)} jogos válidos (mínimo: 5)")
        
        if len(final_fixtures) < n:
            result["errors"].append(f"Apenas {len(final_fixtures)} jogos disponíveis (solicitado: {n})")
        
        logger.info(f"[FIXTURE_PROCESSOR] Final: {len(final_fixtures)} fixtures, valid={result['valid']}, ids={result['fixture_ids'][:5]}...")
        
        return result
    
    def _generate_audit_data(self, fixtures: List[Dict], team_id: int) -> List[Dict]:
        """Generate audit data for each fixture"""
        audit = []
        
        for i, fixture in enumerate(fixtures):
            fixture_data = fixture.get("fixture", {})
            goals = fixture.get("goals", {})
            teams = fixture.get("teams", {})
            
            home_team = teams.get("home", {})
            away_team = teams.get("away", {})
            home_goals = int(goals.get("home", 0) or 0)
            away_goals = int(goals.get("away", 0) or 0)
            
            is_home = home_team.get("id") == team_id
            goals_for = home_goals if is_home else away_goals
            goals_against = away_goals if is_home else home_goals
            total_goals = home_goals + away_goals
            
            # Determine result
            if goals_for > goals_against:
                result = "V"
            elif goals_for == goals_against:
                result = "E"
            else:
                result = "D"
            
            audit.append({
                "index": i + 1,
                "fixture_id": fixture_data.get("id"),
                "date": fixture_data.get("date", "")[:10],
                "home_team": home_team.get("name", "?"),
                "away_team": away_team.get("name", "?"),
                "home_goals": home_goals,
                "away_goals": away_goals,
                "is_home": is_home,
                "goals_for": goals_for,
                "goals_against": goals_against,
                "total_goals": total_goals,
                "result": result,
                "btts": home_goals > 0 and away_goals > 0,
                "over_2_5": total_goals > 2,
                "over_1_5": total_goals > 1
            })
        
        return audit
    
    def calculate_stats(self, fixtures: List[Dict], team_id: int) -> Dict:
        """
        Calcula estatísticas a partir dos fixtures fornecidos.
        
        DEFINIÇÕES CORRETAS:
        - is_home = (fixture.home.id == team_id)
        - goals_for = fixture.goals.home if is_home else fixture.goals.away
        - goals_against = fixture.goals.away if is_home else fixture.goals.home
        - total_goals = fixture.goals.home + fixture.goals.away
        
        MÉTRICAS:
        - avg_total_goals_per_match = avg(total_goals) - média de gols por PARTIDA
        - avg_goals_for = avg(goals_for) - média de gols MARCADOS pelo time
        - avg_goals_against = avg(goals_against) - média de gols SOFRIDOS pelo time
        - over_2_5_pct = count(total_goals >= 3) / n * 100
        - over_1_5_pct = count(total_goals >= 2) / n * 100
        - btts_pct = count(home_goals > 0 AND away_goals > 0) / n * 100
        """
        if not fixtures:
            return self._empty_stats()
        
        n = len(fixtures)
        
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
        
        # Sums for averages
        sum_goals_for = 0
        sum_goals_against = 0
        sum_total_goals = 0
        
        # Process each fixture
        for fixture in fixtures:
            goals = fixture.get("goals", {})
            teams = fixture.get("teams", {})
            
            home_team = teams.get("home", {})
            home_goals = goals.get("home")
            away_goals = goals.get("away")
            
            # Skip if goals are None
            if home_goals is None or away_goals is None:
                continue
            
            home_goals = int(home_goals)
            away_goals = int(away_goals)
            
            # CRITICAL: Determine perspective
            is_home = home_team.get("id") == team_id
            
            # Goals FOR and AGAINST from team's perspective
            goals_for = home_goals if is_home else away_goals
            goals_against = away_goals if is_home else home_goals
            
            # Total goals of the MATCH (for Over/Under)
            total_goals = home_goals + away_goals
            
            # Accumulate sums
            sum_goals_for += goals_for
            sum_goals_against += goals_against
            sum_total_goals += total_goals
            
            # Over/Under counts (based on MATCH total)
            if total_goals > 0:
                over_0_5_count += 1
            if total_goals > 1:
                over_1_5_count += 1
            if total_goals > 2:
                over_2_5_count += 1
            if total_goals > 3:
                over_3_5_count += 1
            
            # BTTS (both teams scored)
            if home_goals > 0 and away_goals > 0:
                btts_count += 1
            
            # Win/Draw/Loss from team's perspective
            if goals_for > goals_against:
                wins += 1
            elif goals_for == goals_against:
                draws += 1
            else:
                losses += 1
            
            # Clean sheet / Failed to score
            if goals_against == 0:
                clean_sheets += 1
            if goals_for == 0:
                failed_to_score += 1
        
        # Calculate percentages and averages
        stats = {
            # Over/Under percentages (based on MATCH total goals)
            "over_0_5_pct": (over_0_5_count / n) * 100,
            "over_1_5_pct": (over_1_5_count / n) * 100,
            "over_2_5_pct": (over_2_5_count / n) * 100,
            "over_3_5_pct": (over_3_5_count / n) * 100,
            
            # BTTS percentage
            "btts_pct": (btts_count / n) * 100,
            
            # Win/Draw/Loss percentages
            "win_rate_pct": (wins / n) * 100,
            "draw_rate_pct": (draws / n) * 100,
            "loss_rate_pct": (losses / n) * 100,
            
            # Clean sheet / Failed to score
            "clean_sheet_pct": (clean_sheets / n) * 100,
            "failed_to_score_pct": (failed_to_score / n) * 100,
            
            # Averages
            "avg_goals_for": sum_goals_for / n,  # Gols MARCADOS pelo time
            "avg_goals_against": sum_goals_against / n,  # Gols SOFRIDOS pelo time
            "avg_total_goals_per_match": sum_total_goals / n,  # Média de gols por PARTIDA
            
            # Raw counts for verification
            "fixtures_used": n,
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "over_2_5_count": over_2_5_count,
            "btts_count": btts_count,
            "sum_goals_for": sum_goals_for,
            "sum_goals_against": sum_goals_against,
            "sum_total_goals": sum_total_goals
        }
        
        # Legacy field names for compatibility
        stats["over_2_5"] = stats["over_2_5_pct"]
        stats["over_1_5"] = stats["over_1_5_pct"]
        stats["btts"] = stats["btts_pct"]
        stats["win_rate"] = stats["win_rate_pct"]
        stats["clean_sheet_rate"] = stats["clean_sheet_pct"]
        stats["failed_to_score_rate"] = stats["failed_to_score_pct"]
        stats["avg_total_goals"] = stats["avg_total_goals_per_match"]
        
        return stats
    
    def _empty_stats(self) -> Dict:
        """Return empty stats dict"""
        return {
            "over_0_5_pct": 0, "over_1_5_pct": 0, "over_2_5_pct": 0, "over_3_5_pct": 0,
            "btts_pct": 0, "win_rate_pct": 0, "draw_rate_pct": 0, "loss_rate_pct": 0,
            "clean_sheet_pct": 0, "failed_to_score_pct": 0,
            "avg_goals_for": 0, "avg_goals_against": 0, "avg_total_goals_per_match": 0,
            "fixtures_used": 0, "wins": 0, "draws": 0, "losses": 0,
            "over_2_5_count": 0, "btts_count": 0,
            "sum_goals_for": 0, "sum_goals_against": 0, "sum_total_goals": 0,
            # Legacy
            "over_2_5": 0, "over_1_5": 0, "btts": 0, "win_rate": 0,
            "clean_sheet_rate": 0, "failed_to_score_rate": 0, "avg_total_goals": 0
        }
    
    def get_form_string(self, fixtures: List[Dict], team_id: int, n: int = 5) -> str:
        """
        Retorna string de forma recente (últimos N jogos).
        
        Formato PT-BR: V (Vitória), E (Empate), D (Derrota)
        
        REGRA:
        - V se goals_for > goals_against
        - E se goals_for == goals_against
        - D se goals_for < goals_against
        """
        form = []
        
        for fixture in fixtures[:n]:
            goals = fixture.get("goals", {})
            teams = fixture.get("teams", {})
            
            home_team = teams.get("home", {})
            home_goals = goals.get("home")
            away_goals = goals.get("away")
            
            if home_goals is None or away_goals is None:
                continue
            
            home_goals = int(home_goals)
            away_goals = int(away_goals)
            
            is_home = home_team.get("id") == team_id
            goals_for = home_goals if is_home else away_goals
            goals_against = away_goals if is_home else home_goals
            
            if goals_for > goals_against:
                form.append("V")
            elif goals_for == goals_against:
                form.append("E")
            else:
                form.append("D")
        
        return " ".join(form)
    
    def validate_stats_consistency(
        self, 
        fixtures: List[Dict], 
        stats: Dict, 
        form: str, 
        team_id: int
    ) -> Dict:
        """
        Valida que as estatísticas são consistentes com os fixtures.
        
        REGRA: Se houver qualquer inconsistência, a análise deve ser BLOQUEADA.
        
        Returns:
            Dict com:
            - valid: bool
            - issues: List[str] - problemas encontrados
        """
        issues = []
        
        if not fixtures:
            return {"valid": False, "issues": ["No fixtures to validate"]}
        
        # Recalculate everything from scratch
        recalc = self.calculate_stats(fixtures, team_id)
        recalc_form = self.get_form_string(fixtures, team_id, 5)
        
        # Tolerance for floating point comparison
        tolerance = 0.5
        
        # Check Over 2.5
        if abs(stats.get("over_2_5", 0) - recalc["over_2_5"]) > tolerance:
            issues.append(f"Over 2.5: got {stats.get('over_2_5'):.1f}%, expected {recalc['over_2_5']:.1f}%")
        
        # Check BTTS
        if abs(stats.get("btts", 0) - recalc["btts"]) > tolerance:
            issues.append(f"BTTS: got {stats.get('btts'):.1f}%, expected {recalc['btts']:.1f}%")
        
        # Check avg_total_goals
        if abs(stats.get("avg_total_goals", 0) - recalc["avg_total_goals"]) > tolerance:
            issues.append(f"Avg Total Goals: got {stats.get('avg_total_goals'):.2f}, expected {recalc['avg_total_goals']:.2f}")
        
        # Check avg_goals_for
        if abs(stats.get("avg_goals_for", 0) - recalc["avg_goals_for"]) > tolerance:
            issues.append(f"Avg Goals For: got {stats.get('avg_goals_for'):.2f}, expected {recalc['avg_goals_for']:.2f}")
        
        # Check form
        if form != recalc_form:
            issues.append(f"Form: got '{form}', expected '{recalc_form}'")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "recalculated": recalc,
            "recalculated_form": recalc_form
        }


# Global instance
fixture_processor = FixtureProcessor()
