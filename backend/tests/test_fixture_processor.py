"""
BetFaro Fixture Processor Tests
================================
Testes de regressão com snapshots e property-based tests.

OBJETIVO: Garantir 0% de erro nos cálculos.
"""

import pytest
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fixture_processor import FixtureProcessor, fixture_processor


class TestFixtureProcessorSnapshots:
    """Testes com snapshots offline - não dependem da API"""
    
    @pytest.fixture
    def processor(self):
        return FixtureProcessor()
    
    @pytest.fixture
    def team_a_data(self):
        snapshot_path = Path(__file__).parent / "fixtures_snapshots" / "team_a_fixtures.json"
        with open(snapshot_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    @pytest.fixture
    def team_b_data(self):
        snapshot_path = Path(__file__).parent / "fixtures_snapshots" / "team_b_fixtures.json"
        with open(snapshot_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    # ═══════════════════════════════════════════════════════════════════════
    # TEAM A SNAPSHOT TESTS
    # ═══════════════════════════════════════════════════════════════════════
    
    def test_team_a_fixture_count(self, processor, team_a_data):
        """Team A deve retornar exatamente 10 fixtures"""
        result = processor.get_last_team_fixtures(
            team_a_data["fixtures"], 
            team_a_data["team_id"], 
            10
        )
        assert result["valid"] == True
        assert len(result["fixtures"]) == 10
    
    def test_team_a_form_string(self, processor, team_a_data):
        """Team A form string deve ser V V E D V"""
        result = processor.get_last_team_fixtures(
            team_a_data["fixtures"], 
            team_a_data["team_id"], 
            10
        )
        form = processor.get_form_string(result["fixtures"], team_a_data["team_id"], 5)
        expected = team_a_data["expected_stats"]["form_5"]
        assert form == expected, f"Form mismatch: got '{form}', expected '{expected}'"
    
    def test_team_a_avg_goals_for(self, processor, team_a_data):
        """Team A avg_goals_for deve ser 2.0"""
        result = processor.get_last_team_fixtures(
            team_a_data["fixtures"], 
            team_a_data["team_id"], 
            10
        )
        stats = processor.calculate_stats(result["fixtures"], team_a_data["team_id"])
        expected = team_a_data["expected_stats"]["avg_goals_for"]
        assert abs(stats["avg_goals_for"] - expected) < 0.01, \
            f"avg_goals_for mismatch: got {stats['avg_goals_for']}, expected {expected}"
    
    def test_team_a_avg_goals_against(self, processor, team_a_data):
        """Team A avg_goals_against deve ser 1.3"""
        result = processor.get_last_team_fixtures(
            team_a_data["fixtures"], 
            team_a_data["team_id"], 
            10
        )
        stats = processor.calculate_stats(result["fixtures"], team_a_data["team_id"])
        expected = team_a_data["expected_stats"]["avg_goals_against"]
        assert abs(stats["avg_goals_against"] - expected) < 0.01, \
            f"avg_goals_against mismatch: got {stats['avg_goals_against']}, expected {expected}"
    
    def test_team_a_avg_total_goals(self, processor, team_a_data):
        """Team A avg_total_goals_per_match deve ser 3.3"""
        result = processor.get_last_team_fixtures(
            team_a_data["fixtures"], 
            team_a_data["team_id"], 
            10
        )
        stats = processor.calculate_stats(result["fixtures"], team_a_data["team_id"])
        expected = team_a_data["expected_stats"]["avg_total_goals_per_match"]
        assert abs(stats["avg_total_goals_per_match"] - expected) < 0.01, \
            f"avg_total_goals mismatch: got {stats['avg_total_goals_per_match']}, expected {expected}"
    
    def test_team_a_over_2_5(self, processor, team_a_data):
        """Team A over_2_5_pct deve ser 70%"""
        result = processor.get_last_team_fixtures(
            team_a_data["fixtures"], 
            team_a_data["team_id"], 
            10
        )
        stats = processor.calculate_stats(result["fixtures"], team_a_data["team_id"])
        expected = team_a_data["expected_stats"]["over_2_5_pct"]
        assert abs(stats["over_2_5_pct"] - expected) < 0.1, \
            f"over_2_5 mismatch: got {stats['over_2_5_pct']}, expected {expected}"
    
    def test_team_a_btts(self, processor, team_a_data):
        """Team A btts_pct deve ser 60%"""
        result = processor.get_last_team_fixtures(
            team_a_data["fixtures"], 
            team_a_data["team_id"], 
            10
        )
        stats = processor.calculate_stats(result["fixtures"], team_a_data["team_id"])
        expected = team_a_data["expected_stats"]["btts_pct"]
        assert abs(stats["btts_pct"] - expected) < 0.1, \
            f"btts mismatch: got {stats['btts_pct']}, expected {expected}"
    
    def test_team_a_win_rate(self, processor, team_a_data):
        """Team A win_rate deve ser 60%"""
        result = processor.get_last_team_fixtures(
            team_a_data["fixtures"], 
            team_a_data["team_id"], 
            10
        )
        stats = processor.calculate_stats(result["fixtures"], team_a_data["team_id"])
        expected = team_a_data["expected_stats"]["win_rate_pct"]
        assert abs(stats["win_rate_pct"] - expected) < 0.1, \
            f"win_rate mismatch: got {stats['win_rate_pct']}, expected {expected}"
    
    # ═══════════════════════════════════════════════════════════════════════
    # TEAM B SNAPSHOT TESTS
    # ═══════════════════════════════════════════════════════════════════════
    
    def test_team_b_fixture_count(self, processor, team_b_data):
        """Team B deve retornar exatamente 10 fixtures"""
        result = processor.get_last_team_fixtures(
            team_b_data["fixtures"], 
            team_b_data["team_id"], 
            10
        )
        assert result["valid"] == True
        assert len(result["fixtures"]) == 10
    
    def test_team_b_form_string(self, processor, team_b_data):
        """Team B form string deve ser V E D V V"""
        result = processor.get_last_team_fixtures(
            team_b_data["fixtures"], 
            team_b_data["team_id"], 
            10
        )
        form = processor.get_form_string(result["fixtures"], team_b_data["team_id"], 5)
        expected = team_b_data["expected_stats"]["form_5"]
        assert form == expected, f"Form mismatch: got '{form}', expected '{expected}'"
    
    def test_team_b_avg_goals_for(self, processor, team_b_data):
        """Team B avg_goals_for deve ser 1.4"""
        result = processor.get_last_team_fixtures(
            team_b_data["fixtures"], 
            team_b_data["team_id"], 
            10
        )
        stats = processor.calculate_stats(result["fixtures"], team_b_data["team_id"])
        expected = team_b_data["expected_stats"]["avg_goals_for"]
        assert abs(stats["avg_goals_for"] - expected) < 0.01, \
            f"avg_goals_for mismatch: got {stats['avg_goals_for']}, expected {expected}"
    
    def test_team_b_avg_total_goals(self, processor, team_b_data):
        """Team B avg_total_goals_per_match deve ser 2.3"""
        result = processor.get_last_team_fixtures(
            team_b_data["fixtures"], 
            team_b_data["team_id"], 
            10
        )
        stats = processor.calculate_stats(result["fixtures"], team_b_data["team_id"])
        expected = team_b_data["expected_stats"]["avg_total_goals_per_match"]
        assert abs(stats["avg_total_goals_per_match"] - expected) < 0.01, \
            f"avg_total_goals mismatch: got {stats['avg_total_goals_per_match']}, expected {expected}"
    
    def test_team_b_over_2_5(self, processor, team_b_data):
        """Team B over_2_5_pct deve ser 30%"""
        result = processor.get_last_team_fixtures(
            team_b_data["fixtures"], 
            team_b_data["team_id"], 
            10
        )
        stats = processor.calculate_stats(result["fixtures"], team_b_data["team_id"])
        expected = team_b_data["expected_stats"]["over_2_5_pct"]
        assert abs(stats["over_2_5_pct"] - expected) < 0.1, \
            f"over_2_5 mismatch: got {stats['over_2_5_pct']}, expected {expected}"


class TestPropertyBased:
    """Property-based tests para garantir invariantes"""
    
    @pytest.fixture
    def processor(self):
        return FixtureProcessor()
    
    def test_avg_total_goals_equals_sum_divided_by_n(self, processor):
        """avg_total_goals_per_match == sum(home + away) / n"""
        fixtures = [
            {"fixture": {"id": i, "date": f"2024-01-{28-i:02d}T15:00:00Z", "status": {"short": "FT"}},
             "teams": {"home": {"id": 1}, "away": {"id": 2}},
             "goals": {"home": 2, "away": 1},
             "league": {"name": "Test", "type": "League"}}
            for i in range(10)
        ]
        
        stats = processor.calculate_stats(fixtures, 1)
        
        # Manual calculation
        total = sum(f["goals"]["home"] + f["goals"]["away"] for f in fixtures)
        expected = total / len(fixtures)
        
        assert abs(stats["avg_total_goals_per_match"] - expected) < 0.001
    
    def test_avg_goals_for_never_uses_total_goals(self, processor):
        """avg_goals_for deve usar apenas gols do time, não total"""
        # Team 1 always scores 1, opponent always scores 3
        fixtures = [
            {"fixture": {"id": i, "date": f"2024-01-{28-i:02d}T15:00:00Z", "status": {"short": "FT"}},
             "teams": {"home": {"id": 1}, "away": {"id": 2}},
             "goals": {"home": 1, "away": 3},  # Team 1 (home) scores 1
             "league": {"name": "Test", "type": "League"}}
            for i in range(10)
        ]
        
        stats = processor.calculate_stats(fixtures, 1)
        
        # Team 1 scored 1 in each game
        assert stats["avg_goals_for"] == 1.0, f"avg_goals_for should be 1.0, got {stats['avg_goals_for']}"
        
        # Total goals per match is 4
        assert stats["avg_total_goals_per_match"] == 4.0, f"avg_total should be 4.0, got {stats['avg_total_goals_per_match']}"
        
        # These should be DIFFERENT
        assert stats["avg_goals_for"] != stats["avg_total_goals_per_match"]
    
    def test_form_matches_goals_comparison(self, processor):
        """Forma V/E/D deve corresponder a goals_for vs goals_against"""
        fixtures = [
            # Win: 2-1 (home)
            {"fixture": {"id": 1, "date": "2024-01-28T15:00:00Z", "status": {"short": "FT"}},
             "teams": {"home": {"id": 1}, "away": {"id": 2}},
             "goals": {"home": 2, "away": 1},
             "league": {"name": "Test", "type": "League"}},
            # Draw: 1-1 (away)
            {"fixture": {"id": 2, "date": "2024-01-27T15:00:00Z", "status": {"short": "FT"}},
             "teams": {"home": {"id": 3}, "away": {"id": 1}},
             "goals": {"home": 1, "away": 1},
             "league": {"name": "Test", "type": "League"}},
            # Loss: 0-2 (home)
            {"fixture": {"id": 3, "date": "2024-01-26T15:00:00Z", "status": {"short": "FT"}},
             "teams": {"home": {"id": 1}, "away": {"id": 4}},
             "goals": {"home": 0, "away": 2},
             "league": {"name": "Test", "type": "League"}},
        ]
        
        form = processor.get_form_string(fixtures, 1, 3)
        assert form == "V E D", f"Form should be 'V E D', got '{form}'"
    
    def test_percentages_between_0_and_100(self, processor):
        """Todos os percentuais devem estar entre 0 e 100"""
        fixtures = [
            {"fixture": {"id": i, "date": f"2024-01-{28-i:02d}T15:00:00Z", "status": {"short": "FT"}},
             "teams": {"home": {"id": 1}, "away": {"id": 2}},
             "goals": {"home": i % 3, "away": (i + 1) % 3},
             "league": {"name": "Test", "type": "League"}}
            for i in range(10)
        ]
        
        stats = processor.calculate_stats(fixtures, 1)
        
        pct_fields = [
            "over_0_5_pct", "over_1_5_pct", "over_2_5_pct", "over_3_5_pct",
            "btts_pct", "win_rate_pct", "draw_rate_pct", "loss_rate_pct",
            "clean_sheet_pct", "failed_to_score_pct"
        ]
        
        for field in pct_fields:
            value = stats.get(field, 0)
            assert 0 <= value <= 100, f"{field} should be between 0 and 100, got {value}"
    
    def test_over_under_uses_match_total_not_team_goals(self, processor):
        """Over/Under deve usar total da partida, não gols do time"""
        # Team 1 scores 1, opponent scores 2 -> total = 3 -> Over 2.5 = YES
        fixtures = [
            {"fixture": {"id": 1, "date": "2024-01-28T15:00:00Z", "status": {"short": "FT"}},
             "teams": {"home": {"id": 1}, "away": {"id": 2}},
             "goals": {"home": 1, "away": 2},  # Total = 3
             "league": {"name": "Test", "type": "League"}},
        ]
        
        stats = processor.calculate_stats(fixtures, 1)
        
        # Over 2.5 should be 100% (total = 3 > 2)
        assert stats["over_2_5_pct"] == 100.0, f"Over 2.5 should be 100%, got {stats['over_2_5_pct']}"
        
        # But team only scored 1 goal
        assert stats["avg_goals_for"] == 1.0
    
    def test_btts_uses_home_and_away_not_team_perspective(self, processor):
        """BTTS deve verificar se home > 0 AND away > 0"""
        fixtures = [
            # BTTS YES: 2-1
            {"fixture": {"id": 1, "date": "2024-01-28T15:00:00Z", "status": {"short": "FT"}},
             "teams": {"home": {"id": 1}, "away": {"id": 2}},
             "goals": {"home": 2, "away": 1},
             "league": {"name": "Test", "type": "League"}},
            # BTTS NO: 3-0
            {"fixture": {"id": 2, "date": "2024-01-27T15:00:00Z", "status": {"short": "FT"}},
             "teams": {"home": {"id": 1}, "away": {"id": 3}},
             "goals": {"home": 3, "away": 0},
             "league": {"name": "Test", "type": "League"}},
        ]
        
        stats = processor.calculate_stats(fixtures, 1)
        
        # 1 of 2 games had BTTS = 50%
        assert stats["btts_pct"] == 50.0, f"BTTS should be 50%, got {stats['btts_pct']}"
    
    def test_deterministic_output(self, processor):
        """Mesmo input deve sempre produzir mesmo output"""
        fixtures = [
            {"fixture": {"id": i, "date": f"2024-01-{28-i:02d}T15:00:00Z", "status": {"short": "FT"}},
             "teams": {"home": {"id": 1}, "away": {"id": 2}},
             "goals": {"home": 2, "away": 1},
             "league": {"name": "Test", "type": "League"}}
            for i in range(15)
        ]
        
        # Run 5 times
        results = []
        for _ in range(5):
            result = processor.get_last_team_fixtures(fixtures, 1, 10)
            results.append(result["fixture_ids"])
        
        # All should be identical
        for i in range(1, len(results)):
            assert results[0] == results[i], f"Results should be deterministic"
    
    def test_no_duplicates_in_output(self, processor):
        """Output não deve ter fixtures duplicados"""
        # Input with duplicates
        fixtures = [
            {"fixture": {"id": 1, "date": "2024-01-28T15:00:00Z", "status": {"short": "FT"}},
             "teams": {"home": {"id": 1}, "away": {"id": 2}},
             "goals": {"home": 2, "away": 1},
             "league": {"name": "Test", "type": "League"}},
            {"fixture": {"id": 1, "date": "2024-01-28T15:00:00Z", "status": {"short": "FT"}},  # DUPLICATE
             "teams": {"home": {"id": 1}, "away": {"id": 2}},
             "goals": {"home": 2, "away": 1},
             "league": {"name": "Test", "type": "League"}},
            {"fixture": {"id": 2, "date": "2024-01-27T15:00:00Z", "status": {"short": "FT"}},
             "teams": {"home": {"id": 1}, "away": {"id": 3}},
             "goals": {"home": 1, "away": 0},
             "league": {"name": "Test", "type": "League"}},
        ]
        
        result = processor.get_last_team_fixtures(fixtures, 1, 10)
        
        # Should have 2 unique fixtures, not 3
        assert len(result["fixtures"]) == 2
        assert len(set(result["fixture_ids"])) == len(result["fixture_ids"])
    
    def test_team_must_be_in_fixture(self, processor):
        """Time deve participar do fixture"""
        fixtures = [
            # Team 1 is in this fixture
            {"fixture": {"id": 1, "date": "2024-01-28T15:00:00Z", "status": {"short": "FT"}},
             "teams": {"home": {"id": 1}, "away": {"id": 2}},
             "goals": {"home": 2, "away": 1},
             "league": {"name": "Test", "type": "League"}},
            # Team 1 is NOT in this fixture
            {"fixture": {"id": 2, "date": "2024-01-27T15:00:00Z", "status": {"short": "FT"}},
             "teams": {"home": {"id": 3}, "away": {"id": 4}},
             "goals": {"home": 1, "away": 0},
             "league": {"name": "Test", "type": "League"}},
        ]
        
        result = processor.get_last_team_fixtures(fixtures, 1, 10)
        
        # Should only have 1 fixture (the one with team 1)
        assert len(result["fixtures"]) == 1
        assert result["fixture_ids"] == [1]


class TestConsistencyValidation:
    """Testes de validação de consistência"""
    
    @pytest.fixture
    def processor(self):
        return FixtureProcessor()
    
    def test_validate_correct_stats(self, processor):
        """Stats corretas devem passar na validação"""
        fixtures = [
            {"fixture": {"id": i, "date": f"2024-01-{28-i:02d}T15:00:00Z", "status": {"short": "FT"}},
             "teams": {"home": {"id": 1}, "away": {"id": 2}},
             "goals": {"home": 2, "away": 1},
             "league": {"name": "Test", "type": "League"}}
            for i in range(10)
        ]
        
        stats = processor.calculate_stats(fixtures, 1)
        form = processor.get_form_string(fixtures, 1, 5)
        
        validation = processor.validate_stats_consistency(fixtures, stats, form, 1)
        
        assert validation["valid"] == True, f"Should be valid, issues: {validation['issues']}"
    
    def test_validate_incorrect_stats(self, processor):
        """Stats incorretas devem falhar na validação"""
        fixtures = [
            {"fixture": {"id": i, "date": f"2024-01-{28-i:02d}T15:00:00Z", "status": {"short": "FT"}},
             "teams": {"home": {"id": 1}, "away": {"id": 2}},
             "goals": {"home": 2, "away": 1},
             "league": {"name": "Test", "type": "League"}}
            for i in range(10)
        ]
        
        # Intentionally wrong stats
        wrong_stats = {
            "over_2_5": 99.0,  # Should be 100%
            "btts": 99.0,  # Should be 100%
            "avg_total_goals": 5.0,  # Should be 3.0
            "avg_goals_for": 5.0,  # Should be 2.0
        }
        
        validation = processor.validate_stats_consistency(fixtures, wrong_stats, "V V V V V", 1)
        
        assert validation["valid"] == False, "Should be invalid with wrong stats"
        assert len(validation["issues"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
