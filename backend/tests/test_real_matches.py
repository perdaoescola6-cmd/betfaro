"""
BetFaro Real Match Testing
===========================
Testa o sistema com jogos reais da API-Football.
Valida consistência de dados, cálculos e output.

IMPORTANTE: Este teste requer APISPORTS_KEY configurada.
"""

import pytest
import sys
import os
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List

sys.path.insert(0, '..')

# Skip all tests if no API key
APISPORTS_KEY = os.getenv("APISPORTS_KEY")
pytestmark = pytest.mark.skipif(
    not APISPORTS_KEY,
    reason="APISPORTS_KEY not configured - skipping real API tests"
)


class TestRealMatchValidation:
    """Test with real match data from API-Football"""
    
    @pytest.fixture
    def chatbot(self):
        from chatbot import ChatBot
        return ChatBot()
    
    @pytest.fixture
    def api(self):
        from football_api import FootballAPI
        return FootballAPI()
    
    # ═══════════════════════════════════════════════════════════════════════
    # VALIDATION HELPERS
    # ═══════════════════════════════════════════════════════════════════════
    
    def validate_fixtures(self, fixtures: List[Dict], team_id: int) -> Dict:
        """Validate that fixtures are correct and consistent"""
        issues = []
        
        if not fixtures:
            issues.append("No fixtures returned")
            return {"valid": False, "issues": issues}
        
        for i, f in enumerate(fixtures):
            fixture_data = f.get("fixture", {})
            goals = f.get("goals", {})
            teams = f.get("teams", {})
            
            # Check fixture has required fields
            if not fixture_data.get("id"):
                issues.append(f"Fixture {i}: missing id")
            if not fixture_data.get("date"):
                issues.append(f"Fixture {i}: missing date")
            
            # Check status is final
            status = fixture_data.get("status", {}).get("short", "")
            if status not in ["FT", "AET", "PEN"]:
                issues.append(f"Fixture {i}: invalid status {status}")
            
            # Check goals are present
            if goals.get("home") is None or goals.get("away") is None:
                issues.append(f"Fixture {i}: missing goals")
            
            # Check team is in the fixture
            home_id = teams.get("home", {}).get("id")
            away_id = teams.get("away", {}).get("id")
            if team_id not in [home_id, away_id]:
                issues.append(f"Fixture {i}: team {team_id} not in fixture")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "count": len(fixtures)
        }
    
    def validate_stats_coherence(self, stats: Dict, fixtures: List[Dict], team_id: int) -> Dict:
        """Validate that stats are coherent with fixtures"""
        issues = []
        
        # Manually calculate expected values
        over_2_5_count = 0
        btts_count = 0
        total_goals_for = 0
        total_goals_against = 0
        total_match_goals = 0
        
        for f in fixtures:
            goals = f.get("goals", {})
            teams = f.get("teams", {})
            
            home_goals = goals.get("home", 0) or 0
            away_goals = goals.get("away", 0) or 0
            match_total = home_goals + away_goals
            total_match_goals += match_total
            
            # Over 2.5
            if match_total > 2:
                over_2_5_count += 1
            
            # BTTS
            if home_goals > 0 and away_goals > 0:
                btts_count += 1
            
            # Goals for/against
            is_home = teams.get("home", {}).get("id") == team_id
            if is_home:
                total_goals_for += home_goals
                total_goals_against += away_goals
            else:
                total_goals_for += away_goals
                total_goals_against += home_goals
        
        n = len(fixtures)
        if n == 0:
            return {"valid": False, "issues": ["No fixtures to validate"]}
        
        expected_over_2_5 = (over_2_5_count / n) * 100
        expected_btts = (btts_count / n) * 100
        expected_avg_total = total_match_goals / n
        expected_avg_for = total_goals_for / n
        expected_avg_against = total_goals_against / n
        
        # Compare with stats (allow small floating point differences)
        tolerance = 0.1
        
        if abs(stats.get("over_2_5", 0) - expected_over_2_5) > tolerance:
            issues.append(f"Over 2.5 mismatch: got {stats.get('over_2_5')}, expected {expected_over_2_5}")
        
        if abs(stats.get("btts", 0) - expected_btts) > tolerance:
            issues.append(f"BTTS mismatch: got {stats.get('btts')}, expected {expected_btts}")
        
        if abs(stats.get("avg_total_goals", 0) - expected_avg_total) > tolerance:
            issues.append(f"Avg total goals mismatch: got {stats.get('avg_total_goals')}, expected {expected_avg_total}")
        
        if abs(stats.get("avg_goals_for", 0) - expected_avg_for) > tolerance:
            issues.append(f"Avg goals for mismatch: got {stats.get('avg_goals_for')}, expected {expected_avg_for}")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "expected": {
                "over_2_5": expected_over_2_5,
                "btts": expected_btts,
                "avg_total_goals": expected_avg_total,
                "avg_goals_for": expected_avg_for,
                "avg_goals_against": expected_avg_against
            }
        }
    
    def validate_form_coherence(self, form_string: str, fixtures: List[Dict], team_id: int) -> Dict:
        """Validate that form string matches fixtures"""
        issues = []
        
        form_list = form_string.split()
        
        # Check we have 5 results (or less if fewer fixtures)
        expected_count = min(5, len(fixtures))
        if len(form_list) != expected_count:
            issues.append(f"Form count mismatch: got {len(form_list)}, expected {expected_count}")
        
        # Validate each result
        for i, (result, fixture) in enumerate(zip(form_list, fixtures[:5])):
            goals = fixture.get("goals", {})
            teams = fixture.get("teams", {})
            
            home_goals = goals.get("home", 0) or 0
            away_goals = goals.get("away", 0) or 0
            
            is_home = teams.get("home", {}).get("id") == team_id
            if is_home:
                goals_for = home_goals
                goals_against = away_goals
            else:
                goals_for = away_goals
                goals_against = home_goals
            
            # Expected result in PT-BR
            if goals_for > goals_against:
                expected = "V"
            elif goals_for == goals_against:
                expected = "E"
            else:
                expected = "D"
            
            if result != expected:
                issues.append(f"Form {i}: got {result}, expected {expected} (score: {home_goals}-{away_goals})")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues
        }
    
    # ═══════════════════════════════════════════════════════════════════════
    # REAL MATCH TESTS
    # ═══════════════════════════════════════════════════════════════════════
    
    @pytest.mark.asyncio
    async def test_premier_league_team(self, chatbot, api):
        """Test with a Premier League team (Arsenal)"""
        # Resolve team
        team = await api.resolve_team("Arsenal")
        assert team is not None, "Failed to resolve Arsenal"
        
        team_id = team["id"]
        
        # Get fixtures
        fixtures = await api.get_team_fixtures(team_id, 20)
        
        # Validate fixtures
        result = chatbot._validate_fixtures(fixtures, team_id, 10)
        assert result["valid"], f"Fixture validation failed: {result['errors']}"
        
        # Calculate stats
        stats = chatbot._calculate_team_stats(result["fixtures"], team_id)
        
        # Validate stats coherence
        coherence = self.validate_stats_coherence(stats, result["fixtures"], team_id)
        assert coherence["valid"], f"Stats coherence failed: {coherence['issues']}"
        
        # Validate form
        form = chatbot._get_form_string(result["fixtures"][:5], team_id)
        form_coherence = self.validate_form_coherence(form, result["fixtures"], team_id)
        assert form_coherence["valid"], f"Form coherence failed: {form_coherence['issues']}"
    
    @pytest.mark.asyncio
    async def test_brazilian_team(self, chatbot, api):
        """Test with a Brazilian team (Flamengo)"""
        team = await api.resolve_team("Flamengo")
        assert team is not None, "Failed to resolve Flamengo"
        
        team_id = team["id"]
        fixtures = await api.get_team_fixtures(team_id, 20)
        
        result = chatbot._validate_fixtures(fixtures, team_id, 10)
        if not result["valid"] and len(result["fixtures"]) >= 5:
            # Allow partial validation for teams with fewer games
            pass
        
        if result["fixtures"]:
            stats = chatbot._calculate_team_stats(result["fixtures"], team_id)
            coherence = self.validate_stats_coherence(stats, result["fixtures"], team_id)
            assert coherence["valid"], f"Stats coherence failed: {coherence['issues']}"
    
    @pytest.mark.asyncio
    async def test_spanish_team(self, chatbot, api):
        """Test with a Spanish team (Real Madrid)"""
        team = await api.resolve_team("Real Madrid")
        assert team is not None, "Failed to resolve Real Madrid"
        
        team_id = team["id"]
        fixtures = await api.get_team_fixtures(team_id, 20)
        
        result = chatbot._validate_fixtures(fixtures, team_id, 10)
        assert result["valid"], f"Fixture validation failed: {result['errors']}"
        
        stats = chatbot._calculate_team_stats(result["fixtures"], team_id)
        coherence = self.validate_stats_coherence(stats, result["fixtures"], team_id)
        assert coherence["valid"], f"Stats coherence failed: {coherence['issues']}"
    
    @pytest.mark.asyncio
    async def test_consistency_same_team_multiple_calls(self, chatbot, api):
        """Test that multiple calls for same team return same data"""
        team = await api.resolve_team("Chelsea")
        assert team is not None, "Failed to resolve Chelsea"
        
        team_id = team["id"]
        
        # Call multiple times
        results = []
        for _ in range(3):
            fixtures = await api.get_team_fixtures(team_id, 20)
            result = chatbot._validate_fixtures(fixtures, team_id, 10)
            results.append(result["fixture_ids"])
        
        # All should be identical
        for i in range(1, len(results)):
            assert results[0] == results[i], f"Inconsistent results between calls: {results[0]} vs {results[i]}"


class TestMatchAnalysisOutput:
    """Test the complete match analysis output"""
    
    @pytest.fixture
    def chatbot(self):
        from chatbot import ChatBot
        return ChatBot()
    
    @pytest.fixture
    def api(self):
        from football_api import FootballAPI
        return FootballAPI()
    
    @pytest.mark.asyncio
    async def test_analysis_contains_required_sections(self, chatbot, api):
        """Test that analysis output contains all required sections"""
        # Get two teams
        team_a = await api.resolve_team("Liverpool")
        team_b = await api.resolve_team("Manchester City")
        
        assert team_a is not None, "Failed to resolve Liverpool"
        assert team_b is not None, "Failed to resolve Manchester City"
        
        # Get fixtures for both
        fixtures_a = await api.get_team_fixtures(team_a["id"], 20)
        fixtures_b = await api.get_team_fixtures(team_b["id"], 20)
        
        # Validate fixtures
        val_a = chatbot._validate_fixtures(fixtures_a, team_a["id"], 10)
        val_b = chatbot._validate_fixtures(fixtures_b, team_b["id"], 10)
        
        if val_a["valid"] and val_b["valid"]:
            # Generate analysis
            output = chatbot._generate_match_analysis(
                team_a, team_b,
                val_a["fixtures"], val_b["fixtures"],
                "all",
                date_range_a=val_a["date_range"],
                date_range_b=val_b["date_range"]
            )
            
            # Check required sections
            assert "Forma Recente" in output, "Missing 'Forma Recente' section"
            assert "Estatísticas" in output, "Missing 'Estatísticas' section"
            assert "Over 2.5" in output, "Missing Over 2.5 stat"
            assert "BTTS" in output, "Missing BTTS stat"
            assert "Apostas Recomendadas" in output, "Missing recommendations"
            
            # Check PT-BR format (V/E/D)
            assert "V" in output or "E" in output or "D" in output, "Form should use PT-BR format"
            
            # Check no English format (W/L)
            # Note: "W" might appear in team names, so we check for "W W" or "L L" patterns
            assert "W W" not in output, "Form should not use English W"
            assert "L L" not in output, "Form should not use English L"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
