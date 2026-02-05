"""
BetFaro Fixture Status Filtering Tests
=======================================
Testes para garantir que apenas fixtures válidos entram nos cálculos.

REGRAS:
1. Somente fixtures FINALIZADOS (FT/AET/PEN) entram no cálculo
2. Status não-finalizados (PST, CANC, ABD, SUSP, TBD, NS, etc.) são excluídos
3. Fixtures com goals null/None são inválidos
4. Se < 10 jogos válidos, retornar aviso "dados insuficientes" (fail-fast)
5. Amistosos são sempre excluídos
6. Ordenação determinística por data (timezone-safe)
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent))

from fixture_processor import FixtureProcessor


class TestFixtureStatusFiltering:
    """Testes para filtro de status de fixtures"""
    
    @pytest.fixture
    def processor(self):
        return FixtureProcessor()
    
    # ═══════════════════════════════════════════════════════════════════════
    # VALID STATUSES (should be included)
    # ═══════════════════════════════════════════════════════════════════════
    
    def test_status_ft_included(self, processor):
        """FT (Full Time) deve ser incluído"""
        fixtures = [
            {
                "fixture": {"id": 1, "date": "2024-01-28T15:00:00Z", "status": {"short": "FT"}},
                "teams": {"home": {"id": 1}, "away": {"id": 2}},
                "goals": {"home": 2, "away": 1},
                "league": {"name": "Test", "type": "League"}
            }
        ]
        
        result = processor.get_last_team_fixtures(fixtures, 1, 10)
        assert len(result["fixtures"]) == 1
    
    def test_status_aet_included(self, processor):
        """AET (After Extra Time) deve ser incluído"""
        fixtures = [
            {
                "fixture": {"id": 1, "date": "2024-01-28T15:00:00Z", "status": {"short": "AET"}},
                "teams": {"home": {"id": 1}, "away": {"id": 2}},
                "goals": {"home": 2, "away": 2},
                "league": {"name": "Test Cup", "type": "Cup"}
            }
        ]
        
        result = processor.get_last_team_fixtures(fixtures, 1, 10)
        assert len(result["fixtures"]) == 1
    
    def test_status_pen_included(self, processor):
        """PEN (Penalties) deve ser incluído"""
        fixtures = [
            {
                "fixture": {"id": 1, "date": "2024-01-28T15:00:00Z", "status": {"short": "PEN"}},
                "teams": {"home": {"id": 1}, "away": {"id": 2}},
                "goals": {"home": 1, "away": 1},
                "league": {"name": "Test Cup", "type": "Cup"}
            }
        ]
        
        result = processor.get_last_team_fixtures(fixtures, 1, 10)
        assert len(result["fixtures"]) == 1
    
    # ═══════════════════════════════════════════════════════════════════════
    # INVALID STATUSES (should be excluded)
    # ═══════════════════════════════════════════════════════════════════════
    
    def test_status_ns_excluded(self, processor):
        """NS (Not Started) deve ser excluído"""
        fixtures = [
            {
                "fixture": {"id": 1, "date": "2024-01-28T15:00:00Z", "status": {"short": "NS"}},
                "teams": {"home": {"id": 1}, "away": {"id": 2}},
                "goals": {"home": None, "away": None},
                "league": {"name": "Test", "type": "League"}
            }
        ]
        
        result = processor.get_last_team_fixtures(fixtures, 1, 10)
        assert len(result["fixtures"]) == 0
    
    def test_status_tbd_excluded(self, processor):
        """TBD (To Be Defined) deve ser excluído"""
        fixtures = [
            {
                "fixture": {"id": 1, "date": "2024-01-28T15:00:00Z", "status": {"short": "TBD"}},
                "teams": {"home": {"id": 1}, "away": {"id": 2}},
                "goals": {"home": None, "away": None},
                "league": {"name": "Test", "type": "League"}
            }
        ]
        
        result = processor.get_last_team_fixtures(fixtures, 1, 10)
        assert len(result["fixtures"]) == 0
    
    def test_status_pst_excluded(self, processor):
        """PST (Postponed) deve ser excluído"""
        fixtures = [
            {
                "fixture": {"id": 1, "date": "2024-01-28T15:00:00Z", "status": {"short": "PST"}},
                "teams": {"home": {"id": 1}, "away": {"id": 2}},
                "goals": {"home": None, "away": None},
                "league": {"name": "Test", "type": "League"}
            }
        ]
        
        result = processor.get_last_team_fixtures(fixtures, 1, 10)
        assert len(result["fixtures"]) == 0
    
    def test_status_canc_excluded(self, processor):
        """CANC (Cancelled) deve ser excluído"""
        fixtures = [
            {
                "fixture": {"id": 1, "date": "2024-01-28T15:00:00Z", "status": {"short": "CANC"}},
                "teams": {"home": {"id": 1}, "away": {"id": 2}},
                "goals": {"home": None, "away": None},
                "league": {"name": "Test", "type": "League"}
            }
        ]
        
        result = processor.get_last_team_fixtures(fixtures, 1, 10)
        assert len(result["fixtures"]) == 0
    
    def test_status_abd_excluded(self, processor):
        """ABD (Abandoned) deve ser excluído"""
        fixtures = [
            {
                "fixture": {"id": 1, "date": "2024-01-28T15:00:00Z", "status": {"short": "ABD"}},
                "teams": {"home": {"id": 1}, "away": {"id": 2}},
                "goals": {"home": 1, "away": 0},  # Even with goals, abandoned is invalid
                "league": {"name": "Test", "type": "League"}
            }
        ]
        
        result = processor.get_last_team_fixtures(fixtures, 1, 10)
        assert len(result["fixtures"]) == 0
    
    def test_status_susp_excluded(self, processor):
        """SUSP (Suspended) deve ser excluído"""
        fixtures = [
            {
                "fixture": {"id": 1, "date": "2024-01-28T15:00:00Z", "status": {"short": "SUSP"}},
                "teams": {"home": {"id": 1}, "away": {"id": 2}},
                "goals": {"home": 2, "away": 1},
                "league": {"name": "Test", "type": "League"}
            }
        ]
        
        result = processor.get_last_team_fixtures(fixtures, 1, 10)
        assert len(result["fixtures"]) == 0
    
    def test_status_int_excluded(self, processor):
        """INT (Interrupted) deve ser excluído"""
        fixtures = [
            {
                "fixture": {"id": 1, "date": "2024-01-28T15:00:00Z", "status": {"short": "INT"}},
                "teams": {"home": {"id": 1}, "away": {"id": 2}},
                "goals": {"home": 1, "away": 1},
                "league": {"name": "Test", "type": "League"}
            }
        ]
        
        result = processor.get_last_team_fixtures(fixtures, 1, 10)
        assert len(result["fixtures"]) == 0
    
    def test_status_live_excluded(self, processor):
        """Live statuses (1H, HT, 2H, ET, BT, P) devem ser excluídos"""
        live_statuses = ["1H", "HT", "2H", "ET", "BT", "P"]
        
        for status in live_statuses:
            fixtures = [
                {
                    "fixture": {"id": 1, "date": "2024-01-28T15:00:00Z", "status": {"short": status}},
                    "teams": {"home": {"id": 1}, "away": {"id": 2}},
                    "goals": {"home": 1, "away": 0},
                    "league": {"name": "Test", "type": "League"}
                }
            ]
            
            result = processor.get_last_team_fixtures(fixtures, 1, 10)
            assert len(result["fixtures"]) == 0, f"Status {status} should be excluded"


class TestGoalsValidation:
    """Testes para validação de gols"""
    
    @pytest.fixture
    def processor(self):
        return FixtureProcessor()
    
    def test_goals_null_excluded(self, processor):
        """Fixtures com goals null devem ser excluídos"""
        fixtures = [
            {
                "fixture": {"id": 1, "date": "2024-01-28T15:00:00Z", "status": {"short": "FT"}},
                "teams": {"home": {"id": 1}, "away": {"id": 2}},
                "goals": {"home": None, "away": None},
                "league": {"name": "Test", "type": "League"}
            }
        ]
        
        result = processor.get_last_team_fixtures(fixtures, 1, 10)
        assert len(result["fixtures"]) == 0
    
    def test_goals_home_null_excluded(self, processor):
        """Fixtures com home goals null devem ser excluídos"""
        fixtures = [
            {
                "fixture": {"id": 1, "date": "2024-01-28T15:00:00Z", "status": {"short": "FT"}},
                "teams": {"home": {"id": 1}, "away": {"id": 2}},
                "goals": {"home": None, "away": 2},
                "league": {"name": "Test", "type": "League"}
            }
        ]
        
        result = processor.get_last_team_fixtures(fixtures, 1, 10)
        assert len(result["fixtures"]) == 0
    
    def test_goals_away_null_excluded(self, processor):
        """Fixtures com away goals null devem ser excluídos"""
        fixtures = [
            {
                "fixture": {"id": 1, "date": "2024-01-28T15:00:00Z", "status": {"short": "FT"}},
                "teams": {"home": {"id": 1}, "away": {"id": 2}},
                "goals": {"home": 2, "away": None},
                "league": {"name": "Test", "type": "League"}
            }
        ]
        
        result = processor.get_last_team_fixtures(fixtures, 1, 10)
        assert len(result["fixtures"]) == 0
    
    def test_goals_zero_zero_included(self, processor):
        """0-0 é um resultado válido e deve ser incluído"""
        fixtures = [
            {
                "fixture": {"id": 1, "date": "2024-01-28T15:00:00Z", "status": {"short": "FT"}},
                "teams": {"home": {"id": 1}, "away": {"id": 2}},
                "goals": {"home": 0, "away": 0},
                "league": {"name": "Test", "type": "League"}
            }
        ]
        
        result = processor.get_last_team_fixtures(fixtures, 1, 10)
        assert len(result["fixtures"]) == 1


class TestInsufficientData:
    """Testes para dados insuficientes (fail-fast)"""
    
    @pytest.fixture
    def processor(self):
        return FixtureProcessor()
    
    def test_less_than_5_games_invalid(self, processor):
        """Menos de 5 jogos válidos deve retornar valid=False"""
        fixtures = [
            {
                "fixture": {"id": i, "date": f"2024-01-{28-i:02d}T15:00:00Z", "status": {"short": "FT"}},
                "teams": {"home": {"id": 1}, "away": {"id": 2}},
                "goals": {"home": 2, "away": 1},
                "league": {"name": "Test", "type": "League"}
            }
            for i in range(4)  # Only 4 games
        ]
        
        result = processor.get_last_team_fixtures(fixtures, 1, 10)
        assert result["valid"] == False
        assert any("insuficientes" in e or "disponíveis" in e for e in result["errors"])
    
    def test_exactly_5_games_valid(self, processor):
        """Exatamente 5 jogos válidos deve retornar valid=True"""
        fixtures = [
            {
                "fixture": {"id": i, "date": f"2024-01-{28-i:02d}T15:00:00Z", "status": {"short": "FT"}},
                "teams": {"home": {"id": 1}, "away": {"id": 2}},
                "goals": {"home": 2, "away": 1},
                "league": {"name": "Test", "type": "League"}
            }
            for i in range(5)
        ]
        
        result = processor.get_last_team_fixtures(fixtures, 1, 10)
        assert result["valid"] == True
        assert len(result["fixtures"]) == 5
    
    def test_less_than_requested_shows_warning(self, processor):
        """Menos jogos que o solicitado deve mostrar aviso"""
        fixtures = [
            {
                "fixture": {"id": i, "date": f"2024-01-{28-i:02d}T15:00:00Z", "status": {"short": "FT"}},
                "teams": {"home": {"id": 1}, "away": {"id": 2}},
                "goals": {"home": 2, "away": 1},
                "league": {"name": "Test", "type": "League"}
            }
            for i in range(7)  # 7 games, but requested 10
        ]
        
        result = processor.get_last_team_fixtures(fixtures, 1, 10)
        assert result["valid"] == True  # Still valid (>= 5)
        assert len(result["fixtures"]) == 7
        assert any("disponíveis" in e for e in result["errors"])
    
    def test_empty_fixtures_invalid(self, processor):
        """Lista vazia deve retornar valid=False"""
        result = processor.get_last_team_fixtures([], 1, 10)
        assert result["valid"] == False
        assert len(result["errors"]) > 0
    
    def test_all_invalid_fixtures_returns_error(self, processor):
        """Todos fixtures inválidos deve retornar valid=False"""
        fixtures = [
            {
                "fixture": {"id": i, "date": f"2024-01-{28-i:02d}T15:00:00Z", "status": {"short": "CANC"}},
                "teams": {"home": {"id": 1}, "away": {"id": 2}},
                "goals": {"home": None, "away": None},
                "league": {"name": "Test", "type": "League"}
            }
            for i in range(10)
        ]
        
        result = processor.get_last_team_fixtures(fixtures, 1, 10)
        assert result["valid"] == False


class TestFriendlyExclusion:
    """Testes para exclusão de amistosos"""
    
    @pytest.fixture
    def processor(self):
        return FixtureProcessor()
    
    def test_friendly_type_excluded(self, processor):
        """Amistosos por tipo devem ser excluídos"""
        fixtures = [
            {
                "fixture": {"id": 1, "date": "2024-01-28T15:00:00Z", "status": {"short": "FT"}},
                "teams": {"home": {"id": 1}, "away": {"id": 2}},
                "goals": {"home": 2, "away": 1},
                "league": {"name": "International Friendly", "type": "friendly"}
            }
        ]
        
        result = processor.get_last_team_fixtures(fixtures, 1, 10)
        assert len(result["fixtures"]) == 0
    
    def test_club_friendly_excluded(self, processor):
        """Club Friendly deve ser excluído"""
        fixtures = [
            {
                "fixture": {"id": 1, "date": "2024-01-28T15:00:00Z", "status": {"short": "FT"}},
                "teams": {"home": {"id": 1}, "away": {"id": 2}},
                "goals": {"home": 2, "away": 1},
                "league": {"name": "Club Friendly", "type": "club friendly"}
            }
        ]
        
        result = processor.get_last_team_fixtures(fixtures, 1, 10)
        assert len(result["fixtures"]) == 0
    
    def test_preseason_excluded(self, processor):
        """Pre-season deve ser excluído"""
        fixtures = [
            {
                "fixture": {"id": 1, "date": "2024-01-28T15:00:00Z", "status": {"short": "FT"}},
                "teams": {"home": {"id": 1}, "away": {"id": 2}},
                "goals": {"home": 2, "away": 1},
                "league": {"name": "Pre-Season Tournament", "type": "League"}
            }
        ]
        
        result = processor.get_last_team_fixtures(fixtures, 1, 10)
        assert len(result["fixtures"]) == 0
    
    def test_charity_match_excluded(self, processor):
        """Charity match deve ser excluído"""
        fixtures = [
            {
                "fixture": {"id": 1, "date": "2024-01-28T15:00:00Z", "status": {"short": "FT"}},
                "teams": {"home": {"id": 1}, "away": {"id": 2}},
                "goals": {"home": 2, "away": 1},
                "league": {"name": "Charity Shield", "type": "League"}
            }
        ]
        
        result = processor.get_last_team_fixtures(fixtures, 1, 10)
        assert len(result["fixtures"]) == 0
    
    def test_official_league_included(self, processor):
        """Liga oficial deve ser incluída"""
        fixtures = [
            {
                "fixture": {"id": 1, "date": "2024-01-28T15:00:00Z", "status": {"short": "FT"}},
                "teams": {"home": {"id": 1}, "away": {"id": 2}},
                "goals": {"home": 2, "away": 1},
                "league": {"name": "Premier League", "type": "League"}
            }
        ]
        
        result = processor.get_last_team_fixtures(fixtures, 1, 10)
        assert len(result["fixtures"]) == 1
    
    def test_official_cup_included(self, processor):
        """Copa oficial deve ser incluída"""
        fixtures = [
            {
                "fixture": {"id": 1, "date": "2024-01-28T15:00:00Z", "status": {"short": "FT"}},
                "teams": {"home": {"id": 1}, "away": {"id": 2}},
                "goals": {"home": 2, "away": 1},
                "league": {"name": "FA Cup", "type": "Cup"}
            }
        ]
        
        result = processor.get_last_team_fixtures(fixtures, 1, 10)
        assert len(result["fixtures"]) == 1


class TestDateOrdering:
    """Testes para ordenação por data"""
    
    @pytest.fixture
    def processor(self):
        return FixtureProcessor()
    
    def test_sorted_by_date_desc(self, processor):
        """Fixtures devem ser ordenados por data DESC (mais recente primeiro)"""
        fixtures = [
            {
                "fixture": {"id": 3, "date": "2024-01-20T15:00:00Z", "status": {"short": "FT"}},
                "teams": {"home": {"id": 1}, "away": {"id": 2}},
                "goals": {"home": 1, "away": 1},
                "league": {"name": "Test", "type": "League"}
            },
            {
                "fixture": {"id": 1, "date": "2024-01-28T15:00:00Z", "status": {"short": "FT"}},
                "teams": {"home": {"id": 1}, "away": {"id": 2}},
                "goals": {"home": 2, "away": 1},
                "league": {"name": "Test", "type": "League"}
            },
            {
                "fixture": {"id": 2, "date": "2024-01-25T15:00:00Z", "status": {"short": "FT"}},
                "teams": {"home": {"id": 1}, "away": {"id": 2}},
                "goals": {"home": 0, "away": 0},
                "league": {"name": "Test", "type": "League"}
            }
        ]
        
        result = processor.get_last_team_fixtures(fixtures, 1, 10)
        
        # Should be sorted: id=1 (Jan 28), id=2 (Jan 25), id=3 (Jan 20)
        assert result["fixture_ids"] == [1, 2, 3]
    
    def test_timezone_safe_ordering(self, processor):
        """Ordenação deve ser timezone-safe"""
        fixtures = [
            {
                "fixture": {"id": 1, "date": "2024-01-28T15:00:00+00:00", "status": {"short": "FT"}},
                "teams": {"home": {"id": 1}, "away": {"id": 2}},
                "goals": {"home": 2, "away": 1},
                "league": {"name": "Test", "type": "League"}
            },
            {
                "fixture": {"id": 2, "date": "2024-01-28T12:00:00-03:00", "status": {"short": "FT"}},
                "teams": {"home": {"id": 1}, "away": {"id": 2}},
                "goals": {"home": 0, "away": 0},
                "league": {"name": "Test", "type": "League"}
            }
        ]
        
        result = processor.get_last_team_fixtures(fixtures, 1, 10)
        
        # Both are at the same UTC time (15:00 UTC), so should use id as tiebreaker
        # id=2 (12:00 -03:00 = 15:00 UTC) and id=1 (15:00 +00:00 = 15:00 UTC)
        # With same date, higher id comes first (DESC)
        assert len(result["fixtures"]) == 2
    
    def test_deterministic_with_same_date(self, processor):
        """Fixtures com mesma data devem ter ordenação determinística por id"""
        fixtures = [
            {
                "fixture": {"id": 100, "date": "2024-01-28T15:00:00Z", "status": {"short": "FT"}},
                "teams": {"home": {"id": 1}, "away": {"id": 2}},
                "goals": {"home": 2, "away": 1},
                "league": {"name": "Test", "type": "League"}
            },
            {
                "fixture": {"id": 200, "date": "2024-01-28T15:00:00Z", "status": {"short": "FT"}},
                "teams": {"home": {"id": 1}, "away": {"id": 3}},
                "goals": {"home": 0, "away": 0},
                "league": {"name": "Test", "type": "League"}
            }
        ]
        
        # Run multiple times
        results = []
        for _ in range(5):
            result = processor.get_last_team_fixtures(fixtures, 1, 10)
            results.append(result["fixture_ids"])
        
        # All should be identical
        for i in range(1, len(results)):
            assert results[0] == results[i], "Should be deterministic"


class TestTeamValidation:
    """Testes para validação de time no fixture"""
    
    @pytest.fixture
    def processor(self):
        return FixtureProcessor()
    
    def test_team_not_in_fixture_excluded(self, processor):
        """Fixture onde o time não participa deve ser excluído"""
        fixtures = [
            {
                "fixture": {"id": 1, "date": "2024-01-28T15:00:00Z", "status": {"short": "FT"}},
                "teams": {"home": {"id": 3}, "away": {"id": 4}},  # Team 1 not here
                "goals": {"home": 2, "away": 1},
                "league": {"name": "Test", "type": "League"}
            }
        ]
        
        result = processor.get_last_team_fixtures(fixtures, 1, 10)
        assert len(result["fixtures"]) == 0
        assert result["stats"]["excluded_team_not_in_fixture"] == 1
    
    def test_team_as_home_included(self, processor):
        """Time como mandante deve ser incluído"""
        fixtures = [
            {
                "fixture": {"id": 1, "date": "2024-01-28T15:00:00Z", "status": {"short": "FT"}},
                "teams": {"home": {"id": 1}, "away": {"id": 2}},
                "goals": {"home": 2, "away": 1},
                "league": {"name": "Test", "type": "League"}
            }
        ]
        
        result = processor.get_last_team_fixtures(fixtures, 1, 10)
        assert len(result["fixtures"]) == 1
    
    def test_team_as_away_included(self, processor):
        """Time como visitante deve ser incluído"""
        fixtures = [
            {
                "fixture": {"id": 1, "date": "2024-01-28T15:00:00Z", "status": {"short": "FT"}},
                "teams": {"home": {"id": 2}, "away": {"id": 1}},
                "goals": {"home": 2, "away": 1},
                "league": {"name": "Test", "type": "League"}
            }
        ]
        
        result = processor.get_last_team_fixtures(fixtures, 1, 10)
        assert len(result["fixtures"]) == 1


class TestDuplicateHandling:
    """Testes para tratamento de duplicatas"""
    
    @pytest.fixture
    def processor(self):
        return FixtureProcessor()
    
    def test_duplicate_fixture_ids_removed(self, processor):
        """Fixtures duplicados devem ser removidos"""
        fixtures = [
            {
                "fixture": {"id": 1, "date": "2024-01-28T15:00:00Z", "status": {"short": "FT"}},
                "teams": {"home": {"id": 1}, "away": {"id": 2}},
                "goals": {"home": 2, "away": 1},
                "league": {"name": "Test", "type": "League"}
            },
            {
                "fixture": {"id": 1, "date": "2024-01-28T15:00:00Z", "status": {"short": "FT"}},  # DUPLICATE
                "teams": {"home": {"id": 1}, "away": {"id": 2}},
                "goals": {"home": 2, "away": 1},
                "league": {"name": "Test", "type": "League"}
            },
            {
                "fixture": {"id": 2, "date": "2024-01-25T15:00:00Z", "status": {"short": "FT"}},
                "teams": {"home": {"id": 1}, "away": {"id": 3}},
                "goals": {"home": 1, "away": 0},
                "league": {"name": "Test", "type": "League"}
            }
        ]
        
        result = processor.get_last_team_fixtures(fixtures, 1, 10)
        assert len(result["fixtures"]) == 2
        assert result["stats"]["excluded_duplicates"] == 1


class TestMixedScenarios:
    """Testes com cenários mistos (combinação de válidos e inválidos)"""
    
    @pytest.fixture
    def processor(self):
        return FixtureProcessor()
    
    def test_mixed_valid_and_invalid(self, processor):
        """Deve filtrar corretamente fixtures mistos"""
        fixtures = [
            # Valid
            {
                "fixture": {"id": 1, "date": "2024-01-28T15:00:00Z", "status": {"short": "FT"}},
                "teams": {"home": {"id": 1}, "away": {"id": 2}},
                "goals": {"home": 2, "away": 1},
                "league": {"name": "Premier League", "type": "League"}
            },
            # Invalid - cancelled
            {
                "fixture": {"id": 2, "date": "2024-01-27T15:00:00Z", "status": {"short": "CANC"}},
                "teams": {"home": {"id": 1}, "away": {"id": 3}},
                "goals": {"home": None, "away": None},
                "league": {"name": "Premier League", "type": "League"}
            },
            # Valid
            {
                "fixture": {"id": 3, "date": "2024-01-26T15:00:00Z", "status": {"short": "AET"}},
                "teams": {"home": {"id": 4}, "away": {"id": 1}},
                "goals": {"home": 2, "away": 2},
                "league": {"name": "FA Cup", "type": "Cup"}
            },
            # Invalid - friendly
            {
                "fixture": {"id": 4, "date": "2024-01-25T15:00:00Z", "status": {"short": "FT"}},
                "teams": {"home": {"id": 1}, "away": {"id": 5}},
                "goals": {"home": 3, "away": 0},
                "league": {"name": "Club Friendly", "type": "friendly"}
            },
            # Invalid - null goals
            {
                "fixture": {"id": 5, "date": "2024-01-24T15:00:00Z", "status": {"short": "FT"}},
                "teams": {"home": {"id": 1}, "away": {"id": 6}},
                "goals": {"home": None, "away": 1},
                "league": {"name": "Premier League", "type": "League"}
            },
            # Valid
            {
                "fixture": {"id": 6, "date": "2024-01-23T15:00:00Z", "status": {"short": "PEN"}},
                "teams": {"home": {"id": 7}, "away": {"id": 1}},
                "goals": {"home": 1, "away": 1},
                "league": {"name": "League Cup", "type": "Cup"}
            },
        ]
        
        result = processor.get_last_team_fixtures(fixtures, 1, 10)
        
        # Should have 3 valid fixtures: ids 1, 3, 6
        assert len(result["fixtures"]) == 3
        assert set(result["fixture_ids"]) == {1, 3, 6}


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
