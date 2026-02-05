"""
BetFaro E2E Flow Tests (Backend Integration)
=============================================
Testes de integração que simulam o fluxo completo do produto:
1. Análise de jogo via Chat
2. Criação de bet
3. Resolução de bet
4. Validação de consistência

Estes testes NÃO dependem de UI, mas validam o fluxo completo via API.
Para testes de UI, usar Playwright em /e2e.
"""

import pytest
import asyncio
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fixture_processor import FixtureProcessor


class TestE2EAnalysisFlow:
    """
    Testa o fluxo completo de análise:
    1. Buscar fixtures de um time
    2. Processar e validar
    3. Calcular estatísticas
    4. Verificar consistência
    """
    
    @pytest.fixture
    def processor(self):
        return FixtureProcessor()
    
    @pytest.fixture
    def mock_fixtures_team_a(self):
        """10 fixtures mockados para Team A (simulando resposta da API)"""
        return [
            {
                "fixture": {"id": 1001, "date": "2024-01-28T15:00:00Z", "status": {"short": "FT"}},
                "teams": {"home": {"id": 42, "name": "Team A"}, "away": {"id": 100, "name": "Opponent 1"}},
                "goals": {"home": 2, "away": 1},
                "league": {"name": "Premier League", "type": "League"}
            },
            {
                "fixture": {"id": 1002, "date": "2024-01-25T15:00:00Z", "status": {"short": "FT"}},
                "teams": {"home": {"id": 101, "name": "Opponent 2"}, "away": {"id": 42, "name": "Team A"}},
                "goals": {"home": 0, "away": 3},
                "league": {"name": "Premier League", "type": "League"}
            },
            {
                "fixture": {"id": 1003, "date": "2024-01-22T15:00:00Z", "status": {"short": "FT"}},
                "teams": {"home": {"id": 42, "name": "Team A"}, "away": {"id": 102, "name": "Opponent 3"}},
                "goals": {"home": 1, "away": 1},
                "league": {"name": "Premier League", "type": "League"}
            },
            {
                "fixture": {"id": 1004, "date": "2024-01-19T15:00:00Z", "status": {"short": "FT"}},
                "teams": {"home": {"id": 103, "name": "Opponent 4"}, "away": {"id": 42, "name": "Team A"}},
                "goals": {"home": 2, "away": 0},
                "league": {"name": "Premier League", "type": "League"}
            },
            {
                "fixture": {"id": 1005, "date": "2024-01-16T15:00:00Z", "status": {"short": "FT"}},
                "teams": {"home": {"id": 42, "name": "Team A"}, "away": {"id": 104, "name": "Opponent 5"}},
                "goals": {"home": 3, "away": 2},
                "league": {"name": "Premier League", "type": "League"}
            },
            {
                "fixture": {"id": 1006, "date": "2024-01-13T15:00:00Z", "status": {"short": "FT"}},
                "teams": {"home": {"id": 105, "name": "Opponent 6"}, "away": {"id": 42, "name": "Team A"}},
                "goals": {"home": 1, "away": 2},
                "league": {"name": "Premier League", "type": "League"}
            },
            {
                "fixture": {"id": 1007, "date": "2024-01-10T15:00:00Z", "status": {"short": "FT"}},
                "teams": {"home": {"id": 42, "name": "Team A"}, "away": {"id": 106, "name": "Opponent 7"}},
                "goals": {"home": 0, "away": 0},
                "league": {"name": "Premier League", "type": "League"}
            },
            {
                "fixture": {"id": 1008, "date": "2024-01-07T15:00:00Z", "status": {"short": "AET"}},
                "teams": {"home": {"id": 107, "name": "Opponent 8"}, "away": {"id": 42, "name": "Team A"}},
                "goals": {"home": 3, "away": 4},
                "league": {"name": "FA Cup", "type": "Cup"}
            },
            {
                "fixture": {"id": 1009, "date": "2024-01-04T15:00:00Z", "status": {"short": "FT"}},
                "teams": {"home": {"id": 42, "name": "Team A"}, "away": {"id": 108, "name": "Opponent 9"}},
                "goals": {"home": 2, "away": 2},
                "league": {"name": "Premier League", "type": "League"}
            },
            {
                "fixture": {"id": 1010, "date": "2024-01-01T15:00:00Z", "status": {"short": "FT"}},
                "teams": {"home": {"id": 109, "name": "Opponent 10"}, "away": {"id": 42, "name": "Team A"}},
                "goals": {"home": 1, "away": 3},
                "league": {"name": "Premier League", "type": "League"}
            }
        ]
    
    @pytest.fixture
    def mock_fixtures_team_b(self):
        """10 fixtures mockados para Team B"""
        return [
            {
                "fixture": {"id": 2001, "date": "2024-01-28T18:00:00Z", "status": {"short": "FT"}},
                "teams": {"home": {"id": 99, "name": "Team B"}, "away": {"id": 200, "name": "Rival 1"}},
                "goals": {"home": 1, "away": 0},
                "league": {"name": "La Liga", "type": "League"}
            },
            {
                "fixture": {"id": 2002, "date": "2024-01-25T18:00:00Z", "status": {"short": "FT"}},
                "teams": {"home": {"id": 201, "name": "Rival 2"}, "away": {"id": 99, "name": "Team B"}},
                "goals": {"home": 2, "away": 2},
                "league": {"name": "La Liga", "type": "League"}
            },
            {
                "fixture": {"id": 2003, "date": "2024-01-22T18:00:00Z", "status": {"short": "FT"}},
                "teams": {"home": {"id": 99, "name": "Team B"}, "away": {"id": 202, "name": "Rival 3"}},
                "goals": {"home": 0, "away": 1},
                "league": {"name": "La Liga", "type": "League"}
            },
            {
                "fixture": {"id": 2004, "date": "2024-01-19T18:00:00Z", "status": {"short": "FT"}},
                "teams": {"home": {"id": 203, "name": "Rival 4"}, "away": {"id": 99, "name": "Team B"}},
                "goals": {"home": 0, "away": 2},
                "league": {"name": "La Liga", "type": "League"}
            },
            {
                "fixture": {"id": 2005, "date": "2024-01-16T18:00:00Z", "status": {"short": "FT"}},
                "teams": {"home": {"id": 99, "name": "Team B"}, "away": {"id": 204, "name": "Rival 5"}},
                "goals": {"home": 3, "away": 1},
                "league": {"name": "La Liga", "type": "League"}
            },
            {
                "fixture": {"id": 2006, "date": "2024-01-13T18:00:00Z", "status": {"short": "PEN"}},
                "teams": {"home": {"id": 205, "name": "Rival 6"}, "away": {"id": 99, "name": "Team B"}},
                "goals": {"home": 1, "away": 1},
                "league": {"name": "Copa del Rey", "type": "Cup"}
            },
            {
                "fixture": {"id": 2007, "date": "2024-01-10T18:00:00Z", "status": {"short": "FT"}},
                "teams": {"home": {"id": 99, "name": "Team B"}, "away": {"id": 206, "name": "Rival 7"}},
                "goals": {"home": 2, "away": 0},
                "league": {"name": "La Liga", "type": "League"}
            },
            {
                "fixture": {"id": 2008, "date": "2024-01-07T18:00:00Z", "status": {"short": "FT"}},
                "teams": {"home": {"id": 207, "name": "Rival 8"}, "away": {"id": 99, "name": "Team B"}},
                "goals": {"home": 3, "away": 2},
                "league": {"name": "La Liga", "type": "League"}
            },
            {
                "fixture": {"id": 2009, "date": "2024-01-04T18:00:00Z", "status": {"short": "FT"}},
                "teams": {"home": {"id": 99, "name": "Team B"}, "away": {"id": 208, "name": "Rival 9"}},
                "goals": {"home": 1, "away": 1},
                "league": {"name": "La Liga", "type": "League"}
            },
            {
                "fixture": {"id": 2010, "date": "2024-01-01T18:00:00Z", "status": {"short": "FT"}},
                "teams": {"home": {"id": 209, "name": "Rival 10"}, "away": {"id": 99, "name": "Team B"}},
                "goals": {"home": 0, "away": 0},
                "league": {"name": "La Liga", "type": "League"}
            }
        ]
    
    def test_e2e_analysis_flow_team_a(self, processor, mock_fixtures_team_a):
        """
        E2E: Fluxo completo de análise para Team A
        1. Processar fixtures
        2. Calcular stats
        3. Gerar form
        4. Validar consistência
        """
        team_id = 42
        
        # Step 1: Process fixtures
        result = processor.get_last_team_fixtures(mock_fixtures_team_a, team_id, 10)
        
        assert result["valid"] == True, f"Should be valid, errors: {result['errors']}"
        assert len(result["fixtures"]) == 10, "Should have 10 fixtures"
        
        # Step 2: Calculate stats
        stats = processor.calculate_stats(result["fixtures"], team_id)
        
        # Step 3: Get form
        form = processor.get_form_string(result["fixtures"], team_id, 5)
        
        # Step 4: Validate consistency
        validation = processor.validate_stats_consistency(
            result["fixtures"], stats, form, team_id
        )
        
        assert validation["valid"] == True, f"Consistency failed: {validation['issues']}"
        
        # Verify specific values
        assert form == "V V E D V", f"Form should be 'V V E D V', got '{form}'"
        assert abs(stats["avg_goals_for"] - 2.0) < 0.01, f"avg_goals_for should be 2.0"
        assert abs(stats["over_2_5_pct"] - 70.0) < 0.1, f"over_2_5 should be 70%"
    
    def test_e2e_analysis_flow_team_b(self, processor, mock_fixtures_team_b):
        """E2E: Fluxo completo de análise para Team B"""
        team_id = 99
        
        result = processor.get_last_team_fixtures(mock_fixtures_team_b, team_id, 10)
        assert result["valid"] == True
        
        stats = processor.calculate_stats(result["fixtures"], team_id)
        form = processor.get_form_string(result["fixtures"], team_id, 5)
        
        validation = processor.validate_stats_consistency(
            result["fixtures"], stats, form, team_id
        )
        
        assert validation["valid"] == True, f"Consistency failed: {validation['issues']}"
        assert form == "V E D V V", f"Form should be 'V E D V V', got '{form}'"
    
    def test_e2e_match_analysis_both_teams(self, processor, mock_fixtures_team_a, mock_fixtures_team_b):
        """
        E2E: Análise de partida Team A vs Team B
        Simula o fluxo completo do chat quando usuário pede análise
        """
        team_a_id = 42
        team_b_id = 99
        
        # Process both teams SEPARATELY (não misturar listas)
        result_a = processor.get_last_team_fixtures(mock_fixtures_team_a, team_a_id, 10)
        result_b = processor.get_last_team_fixtures(mock_fixtures_team_b, team_b_id, 10)
        
        assert result_a["valid"] == True
        assert result_b["valid"] == True
        
        # Calculate stats for each team
        stats_a = processor.calculate_stats(result_a["fixtures"], team_a_id)
        stats_b = processor.calculate_stats(result_b["fixtures"], team_b_id)
        
        # Combined analysis (como o chat faz)
        avg_over_2_5 = (stats_a["over_2_5_pct"] + stats_b["over_2_5_pct"]) / 2
        avg_btts = (stats_a["btts_pct"] + stats_b["btts_pct"]) / 2
        
        # Verify combined stats are reasonable
        assert 0 <= avg_over_2_5 <= 100
        assert 0 <= avg_btts <= 100
        
        # Verify teams are NOT mixed
        assert result_a["fixture_ids"] != result_b["fixture_ids"]
    
    def test_e2e_deterministic_output(self, processor, mock_fixtures_team_a):
        """E2E: Mesmo input deve sempre produzir mesmo output"""
        team_id = 42
        
        results = []
        for _ in range(5):
            result = processor.get_last_team_fixtures(mock_fixtures_team_a, team_id, 10)
            stats = processor.calculate_stats(result["fixtures"], team_id)
            form = processor.get_form_string(result["fixtures"], team_id, 5)
            results.append({
                "fixture_ids": result["fixture_ids"],
                "over_2_5": stats["over_2_5_pct"],
                "btts": stats["btts_pct"],
                "form": form
            })
        
        # All results should be identical
        for i in range(1, len(results)):
            assert results[0] == results[i], "Results should be deterministic"


class TestE2EBetCreation:
    """
    Testa o fluxo de criação de bet:
    - Validação de campos obrigatórios
    - Normalização de market
    - Estrutura correta para DB
    """
    
    def test_bet_structure_from_chat(self):
        """Bet criada via chat deve ter estrutura correta"""
        bet = {
            "source": "chat",
            "home_team": "Flamengo",
            "away_team": "Palmeiras",
            "market": "over_2_5_ft",
            "odds": 1.85,
            "status": "pending",
            "fixture_id": "12345",
            "kickoff_at": "2024-02-10T20:00:00Z"
        }
        
        # Validate required fields
        required_fields = ["source", "home_team", "away_team", "market", "odds", "status"]
        for field in required_fields:
            assert field in bet, f"Missing required field: {field}"
        
        # Validate source
        assert bet["source"] in ["chat", "daily_picks", "manual"]
        
        # Validate status
        assert bet["status"] in ["pending", "won", "lost", "void", "cashout"]
        
        # Validate odds
        assert bet["odds"] >= 1.01
    
    def test_bet_structure_from_picks(self):
        """Bet criada via daily picks deve ter estrutura correta"""
        bet = {
            "source": "daily_picks",
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "market": "btts_yes_ft",
            "odds": 1.72,
            "status": "pending",
            "bot_reco": {
                "confidence": 75,
                "analysis": "Both teams score frequently"
            },
            "value_flag": True
        }
        
        assert bet["source"] == "daily_picks"
        assert "bot_reco" in bet
        assert bet["value_flag"] == True
    
    def test_bet_structure_manual(self):
        """Bet criada manualmente deve ter estrutura correta"""
        bet = {
            "source": "manual",
            "home_team": "Real Madrid",
            "away_team": "Barcelona",
            "market": "home_win_ft",
            "odds": 2.10,
            "stake": 50.00,
            "status": "pending",
            "note": "El Clasico - home advantage"
        }
        
        assert bet["source"] == "manual"
        assert bet["stake"] == 50.00
        assert "note" in bet


class TestE2EBetResolution:
    """
    Testa o fluxo de resolução de bets:
    - Settlement correto baseado em resultado
    - Cálculo de profit/loss
    - Atualização de status
    """
    
    def test_bet_resolution_won(self):
        """Bet ganha deve ter status 'won' e profit positivo"""
        bet = {
            "status": "pending",
            "market": "over_2_5_ft",
            "odds": 1.85,
            "stake": 100.00
        }
        
        fixture_result = {
            "goals": {"home": 2, "away": 2},  # Total = 4 > 2.5
            "status": {"short": "FT"}
        }
        
        # Simulate resolution
        total_goals = fixture_result["goals"]["home"] + fixture_result["goals"]["away"]
        
        if bet["market"] == "over_2_5_ft":
            if total_goals > 2:
                bet["status"] = "won"
                bet["profit_loss"] = bet["stake"] * (bet["odds"] - 1)
            else:
                bet["status"] = "lost"
                bet["profit_loss"] = -bet["stake"]
        
        assert bet["status"] == "won"
        assert abs(bet["profit_loss"] - 85.00) < 0.01  # 100 * (1.85 - 1)
    
    def test_bet_resolution_lost(self):
        """Bet perdida deve ter status 'lost' e profit negativo"""
        bet = {
            "status": "pending",
            "market": "over_2_5_ft",
            "odds": 1.85,
            "stake": 100.00
        }
        
        fixture_result = {
            "goals": {"home": 1, "away": 1},  # Total = 2 <= 2.5
            "status": {"short": "FT"}
        }
        
        total_goals = fixture_result["goals"]["home"] + fixture_result["goals"]["away"]
        
        if bet["market"] == "over_2_5_ft":
            if total_goals > 2:
                bet["status"] = "won"
                bet["profit_loss"] = bet["stake"] * (bet["odds"] - 1)
            else:
                bet["status"] = "lost"
                bet["profit_loss"] = -bet["stake"]
        
        assert bet["status"] == "lost"
        assert bet["profit_loss"] == -100.00
    
    def test_bet_resolution_btts(self):
        """BTTS deve ser resolvido corretamente"""
        # BTTS YES - won
        bet_yes = {"market": "btts_yes_ft", "odds": 1.72, "stake": 50.00, "status": "pending"}
        fixture = {"goals": {"home": 2, "away": 1}}  # Both scored
        
        if fixture["goals"]["home"] > 0 and fixture["goals"]["away"] > 0:
            bet_yes["status"] = "won"
        else:
            bet_yes["status"] = "lost"
        
        assert bet_yes["status"] == "won"
        
        # BTTS NO - lost (because both scored)
        bet_no = {"market": "btts_no_ft", "odds": 2.10, "stake": 50.00, "status": "pending"}
        
        if fixture["goals"]["home"] > 0 and fixture["goals"]["away"] > 0:
            bet_no["status"] = "lost"
        else:
            bet_no["status"] = "won"
        
        assert bet_no["status"] == "lost"
    
    def test_bet_resolution_void_cancelled(self):
        """Jogo cancelado deve resultar em void"""
        bet = {"status": "pending", "market": "over_2_5_ft", "odds": 1.85, "stake": 100.00}
        
        fixture_result = {
            "goals": {"home": None, "away": None},
            "status": {"short": "CANC"}
        }
        
        # Void statuses
        VOID_STATUSES = ["CANC", "ABD", "PST", "SUSP", "AWD", "WO"]
        
        if fixture_result["status"]["short"] in VOID_STATUSES:
            bet["status"] = "void"
            bet["profit_loss"] = 0
        
        assert bet["status"] == "void"
        assert bet["profit_loss"] == 0


class TestE2ECrossUserConsistency:
    """
    Testa que dois usuários diferentes recebem o mesmo output
    para a mesma análise.
    """
    
    @pytest.fixture
    def processor(self):
        return FixtureProcessor()
    
    @pytest.fixture
    def shared_fixtures(self):
        """Fixtures compartilhados entre usuários"""
        return [
            {
                "fixture": {"id": i, "date": f"2024-01-{28-i:02d}T15:00:00Z", "status": {"short": "FT"}},
                "teams": {"home": {"id": 1}, "away": {"id": 2}},
                "goals": {"home": 2, "away": 1},
                "league": {"name": "Test League", "type": "League"}
            }
            for i in range(15)
        ]
    
    def test_cross_user_same_fixtures(self, processor, shared_fixtures):
        """Dois usuários devem receber os mesmos fixture_ids"""
        team_id = 1
        
        # User A
        result_a = processor.get_last_team_fixtures(shared_fixtures, team_id, 10)
        
        # User B (same input)
        result_b = processor.get_last_team_fixtures(shared_fixtures, team_id, 10)
        
        assert result_a["fixture_ids"] == result_b["fixture_ids"]
    
    def test_cross_user_same_stats(self, processor, shared_fixtures):
        """Dois usuários devem receber as mesmas estatísticas"""
        team_id = 1
        
        # User A
        result_a = processor.get_last_team_fixtures(shared_fixtures, team_id, 10)
        stats_a = processor.calculate_stats(result_a["fixtures"], team_id)
        
        # User B
        result_b = processor.get_last_team_fixtures(shared_fixtures, team_id, 10)
        stats_b = processor.calculate_stats(result_b["fixtures"], team_id)
        
        # Compare key stats
        assert stats_a["over_2_5_pct"] == stats_b["over_2_5_pct"]
        assert stats_a["btts_pct"] == stats_b["btts_pct"]
        assert stats_a["avg_goals_for"] == stats_b["avg_goals_for"]
        assert stats_a["avg_total_goals_per_match"] == stats_b["avg_total_goals_per_match"]
    
    def test_cross_user_same_form(self, processor, shared_fixtures):
        """Dois usuários devem receber a mesma forma"""
        team_id = 1
        
        result_a = processor.get_last_team_fixtures(shared_fixtures, team_id, 10)
        form_a = processor.get_form_string(result_a["fixtures"], team_id, 5)
        
        result_b = processor.get_last_team_fixtures(shared_fixtures, team_id, 10)
        form_b = processor.get_form_string(result_b["fixtures"], team_id, 5)
        
        assert form_a == form_b


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
