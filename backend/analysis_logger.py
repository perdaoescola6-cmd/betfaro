"""
BetFaro Analysis Logger
========================
Logs estruturados em JSON para auditoria completa de análises.
Permite rastrear qualquer output incorreto.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import os

logger = logging.getLogger(__name__)


class AnalysisLogger:
    """
    Logger estruturado para análises do chat.
    Registra todos os dados necessários para auditoria.
    """
    
    def __init__(self):
        self.log_file = os.getenv("ANALYSIS_LOG_FILE", "analysis_audit.jsonl")
        self.enable_file_logging = os.getenv("ENABLE_ANALYSIS_FILE_LOG", "false").lower() == "true"
    
    def log_analysis(
        self,
        user_id: int,
        original_query: str,
        team_a: Dict,
        team_b: Dict,
        fixtures_a: List[Dict],
        fixtures_b: List[Dict],
        stats_a: Dict,
        stats_b: Dict,
        form_a: str,
        form_b: str,
        fair_odds: Dict,
        success: bool,
        error_message: Optional[str] = None
    ) -> Dict:
        """
        Log completo de uma análise para auditoria.
        
        Returns:
            Dict com todos os dados logados (para verificação)
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Extrair fixture IDs e placares
        fixtures_a_summary = self._summarize_fixtures(fixtures_a, team_a.get("id"))
        fixtures_b_summary = self._summarize_fixtures(fixtures_b, team_b.get("id"))
        
        log_entry = {
            "timestamp_utc": timestamp,
            "user_id": user_id,
            "original_query": original_query,
            "success": success,
            "error_message": error_message,
            
            # Teams resolved
            "team_a": {
                "id": team_a.get("id"),
                "name": team_a.get("name"),
                "country": team_a.get("country")
            },
            "team_b": {
                "id": team_b.get("id"),
                "name": team_b.get("name"),
                "country": team_b.get("country")
            },
            
            # Fixtures used (last 10)
            "fixtures_a": {
                "count": len(fixtures_a),
                "ids": [f.get("fixture", {}).get("id") for f in fixtures_a],
                "details": fixtures_a_summary
            },
            "fixtures_b": {
                "count": len(fixtures_b),
                "ids": [f.get("fixture", {}).get("id") for f in fixtures_b],
                "details": fixtures_b_summary
            },
            
            # Form (last 5 games) in PT-BR
            "form_a": form_a,
            "form_b": form_b,
            
            # Statistics calculated
            "stats_a": {
                "over_2_5_pct": stats_a.get("over_2_5", 0),
                "over_1_5_pct": stats_a.get("over_1_5", 0),
                "btts_pct": stats_a.get("btts", 0),
                "avg_total_goals": stats_a.get("avg_total_goals", 0),
                "avg_goals_for": stats_a.get("avg_goals_for", 0),
                "avg_goals_against": stats_a.get("avg_goals_against", 0),
                "win_rate": stats_a.get("win_rate", 0),
                "clean_sheet_rate": stats_a.get("clean_sheet_rate", 0)
            },
            "stats_b": {
                "over_2_5_pct": stats_b.get("over_2_5", 0),
                "over_1_5_pct": stats_b.get("over_1_5", 0),
                "btts_pct": stats_b.get("btts", 0),
                "avg_total_goals": stats_b.get("avg_total_goals", 0),
                "avg_goals_for": stats_b.get("avg_goals_for", 0),
                "avg_goals_against": stats_b.get("avg_goals_against", 0),
                "win_rate": stats_b.get("win_rate", 0),
                "clean_sheet_rate": stats_b.get("clean_sheet_rate", 0)
            },
            
            # Combined stats
            "combined_stats": {
                "avg_over_2_5_pct": (stats_a.get("over_2_5", 0) + stats_b.get("over_2_5", 0)) / 2,
                "avg_btts_pct": (stats_a.get("btts", 0) + stats_b.get("btts", 0)) / 2,
                "avg_total_goals": (stats_a.get("avg_total_goals", 0) + stats_b.get("avg_total_goals", 0)) / 2
            },
            
            # Fair odds calculated
            "fair_odds": fair_odds
        }
        
        # Log to console (structured JSON)
        logger.info(f"[ANALYSIS_AUDIT] {json.dumps(log_entry, ensure_ascii=False)}")
        
        # Optionally log to file
        if self.enable_file_logging:
            self._write_to_file(log_entry)
        
        return log_entry
    
    def log_analysis_failure(
        self,
        user_id: int,
        original_query: str,
        error_type: str,
        error_details: str,
        partial_data: Optional[Dict] = None
    ) -> Dict:
        """
        Log de falha na análise (dados incompletos, inconsistentes, etc.)
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        
        log_entry = {
            "timestamp_utc": timestamp,
            "user_id": user_id,
            "original_query": original_query,
            "success": False,
            "error_type": error_type,
            "error_details": error_details,
            "partial_data": partial_data
        }
        
        logger.warning(f"[ANALYSIS_FAILURE] {json.dumps(log_entry, ensure_ascii=False)}")
        
        if self.enable_file_logging:
            self._write_to_file(log_entry)
        
        return log_entry
    
    def _summarize_fixtures(self, fixtures: List[Dict], team_id: int) -> List[Dict]:
        """
        Summarize fixtures for logging (id, date, score, result)
        """
        summary = []
        for f in fixtures[:10]:  # Max 10
            fixture_data = f.get("fixture", {})
            goals = f.get("goals", {})
            teams = f.get("teams", {})
            
            home_id = teams.get("home", {}).get("id")
            away_id = teams.get("away", {}).get("id")
            home_name = teams.get("home", {}).get("name", "?")
            away_name = teams.get("away", {}).get("name", "?")
            home_goals = goals.get("home", 0) or 0
            away_goals = goals.get("away", 0) or 0
            
            # Determine result for this team
            is_home = home_id == team_id
            if is_home:
                goals_for = home_goals
                goals_against = away_goals
            else:
                goals_for = away_goals
                goals_against = home_goals
            
            if goals_for > goals_against:
                result = "V"
            elif goals_for == goals_against:
                result = "E"
            else:
                result = "D"
            
            summary.append({
                "fixture_id": fixture_data.get("id"),
                "date": fixture_data.get("date", "")[:10],
                "home_team": home_name,
                "away_team": away_name,
                "score": f"{home_goals}-{away_goals}",
                "result_for_team": result,
                "total_goals": home_goals + away_goals
            })
        
        return summary
    
    def _write_to_file(self, log_entry: Dict):
        """Write log entry to JSONL file"""
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"[ANALYSIS_LOGGER] Failed to write to file: {e}")
    
    def validate_consistency(
        self,
        fixtures: List[Dict],
        stats: Dict,
        form: str,
        team_id: int
    ) -> Dict:
        """
        Validate that stats and form are consistent with fixtures.
        Returns validation result with any inconsistencies found.
        
        CRITICAL: This is the fail-fast check. If inconsistent, analysis should NOT proceed.
        """
        issues = []
        
        if not fixtures:
            return {"valid": False, "issues": ["No fixtures to validate"]}
        
        # Manually recalculate everything
        over_2_5_count = 0
        over_1_5_count = 0
        btts_count = 0
        total_goals_for = 0
        total_goals_against = 0
        total_match_goals = 0
        wins = 0
        draws = 0
        losses = 0
        clean_sheets = 0
        
        expected_form = []
        
        for i, f in enumerate(fixtures):
            goals = f.get("goals", {})
            teams = f.get("teams", {})
            
            home_goals = goals.get("home")
            away_goals = goals.get("away")
            
            # Validate goals are present
            if home_goals is None or away_goals is None:
                issues.append(f"Fixture {i}: missing goals data")
                continue
            
            home_goals = int(home_goals)
            away_goals = int(away_goals)
            match_total = home_goals + away_goals
            total_match_goals += match_total
            
            # Over calculations (using MATCH total, not team goals)
            if match_total > 2:
                over_2_5_count += 1
            if match_total > 1:
                over_1_5_count += 1
            
            # BTTS (both teams scored)
            if home_goals > 0 and away_goals > 0:
                btts_count += 1
            
            # Goals for/against
            is_home = teams.get("home", {}).get("id") == team_id
            if is_home:
                goals_for = home_goals
                goals_against = away_goals
            else:
                goals_for = away_goals
                goals_against = home_goals
            
            total_goals_for += goals_for
            total_goals_against += goals_against
            
            # Win/Draw/Loss
            if goals_for > goals_against:
                wins += 1
                if i < 5:
                    expected_form.append("V")
            elif goals_for == goals_against:
                draws += 1
                if i < 5:
                    expected_form.append("E")
            else:
                losses += 1
                if i < 5:
                    expected_form.append("D")
            
            # Clean sheet
            if goals_against == 0:
                clean_sheets += 1
        
        n = len(fixtures)
        if n == 0:
            return {"valid": False, "issues": ["No valid fixtures after filtering"]}
        
        # Expected values
        expected_over_2_5 = round((over_2_5_count / n) * 100, 1)
        expected_over_1_5 = round((over_1_5_count / n) * 100, 1)
        expected_btts = round((btts_count / n) * 100, 1)
        expected_avg_total = round(total_match_goals / n, 2)
        expected_avg_for = round(total_goals_for / n, 2)
        expected_avg_against = round(total_goals_against / n, 2)
        expected_win_rate = round((wins / n) * 100, 1)
        expected_form_str = " ".join(expected_form)
        
        # Compare with provided stats (tolerance for floating point)
        tolerance = 0.5
        
        if abs(stats.get("over_2_5", 0) - expected_over_2_5) > tolerance:
            issues.append(f"Over 2.5 mismatch: got {stats.get('over_2_5')}, expected {expected_over_2_5}")
        
        if abs(stats.get("over_1_5", 0) - expected_over_1_5) > tolerance:
            issues.append(f"Over 1.5 mismatch: got {stats.get('over_1_5')}, expected {expected_over_1_5}")
        
        if abs(stats.get("btts", 0) - expected_btts) > tolerance:
            issues.append(f"BTTS mismatch: got {stats.get('btts')}, expected {expected_btts}")
        
        if abs(stats.get("avg_total_goals", 0) - expected_avg_total) > tolerance:
            issues.append(f"Avg total goals mismatch: got {stats.get('avg_total_goals')}, expected {expected_avg_total}")
        
        # Validate form string
        if form != expected_form_str:
            issues.append(f"Form mismatch: got '{form}', expected '{expected_form_str}'")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "expected": {
                "over_2_5": expected_over_2_5,
                "over_1_5": expected_over_1_5,
                "btts": expected_btts,
                "avg_total_goals": expected_avg_total,
                "avg_goals_for": expected_avg_for,
                "avg_goals_against": expected_avg_against,
                "win_rate": expected_win_rate,
                "form": expected_form_str
            }
        }


# Global instance
analysis_logger = AnalysisLogger()
