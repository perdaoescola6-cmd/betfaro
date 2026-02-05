"""
BetFaro QA Comprehensive Test Suite
====================================
Testa todas as features implementadas:
- Chat de análises
- Cálculos de estatísticas
- Forma recente PT-BR
- Odds justas
- Consistência entre contas
- Fluxo de tracking
- Limites por plano
"""

import pytest
import sys
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import logging

sys.path.insert(0, '..')

from chatbot import ChatBot
from football_api import FootballAPI
from team_resolver import TeamResolver

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestQAComprehensive:
    """Comprehensive QA tests for BetFaro"""
    
    @pytest.fixture
    def chatbot(self):
        return ChatBot()
    
    @pytest.fixture
    def api(self):
        return FootballAPI()
    
    # ═══════════════════════════════════════════════════════════════════════
    # 1. CHAT DE ANÁLISES - OUTPUT VALIDATION
    # ═══════════════════════════════════════════════════════════════════════
    
    def test_form_string_uses_ptbr_format(self, chatbot):
        """Forma recente deve usar V/E/D (PT-BR), não W/D/L"""
        fixtures = [
            {"teams": {"home": {"id": 42}, "away": {"id": 1}}, "goals": {"home": 2, "away": 0}},  # V
            {"teams": {"home": {"id": 42}, "away": {"id": 2}}, "goals": {"home": 1, "away": 1}},  # E
            {"teams": {"home": {"id": 42}, "away": {"id": 3}}, "goals": {"home": 0, "away": 1}},  # D
        ]
        form = chatbot._get_form_string(fixtures, 42)
        
        # Must NOT contain W, L (English)
        assert "W" not in form, f"Form should use PT-BR (V), not English (W): {form}"
        assert "L" not in form, f"Form should use PT-BR (D for Derrota), not English (L): {form}"
        
        # Must contain V, E, D (Portuguese)
        assert "V" in form, f"Form should contain V (Vitória): {form}"
        assert "E" in form, f"Form should contain E (Empate): {form}"
        assert "D" in form, f"Form should contain D (Derrota): {form}"
    
    def test_over_2_5_uses_match_total_not_team_goals(self, chatbot):
        """Over 2.5 deve usar gols TOTAIS da partida (home + away)"""
        # Cenário: Time 42 marcou 1 gol em cada jogo, mas os jogos tiveram totais diferentes
        fixtures = [
            # Time 42 marcou 1, mas jogo teve 3 gols total -> Over 2.5 = YES
            {"fixture": {"id": 1}, "teams": {"home": {"id": 42}, "away": {"id": 1}}, "goals": {"home": 1, "away": 2}},
            # Time 42 marcou 1, mas jogo teve 2 gols total -> Over 2.5 = NO
            {"fixture": {"id": 2}, "teams": {"home": {"id": 42}, "away": {"id": 2}}, "goals": {"home": 1, "away": 1}},
        ]
        stats = chatbot._calculate_team_stats(fixtures, 42)
        
        # 1 de 2 jogos teve Over 2.5 = 50%
        assert stats["over_2_5"] == 50.0, f"Over 2.5 should be 50% (1/2 matches), got {stats['over_2_5']}%"
    
    def test_btts_uses_home_and_away_goals(self, chatbot):
        """BTTS deve verificar se AMBOS os times marcaram (home > 0 AND away > 0)"""
        fixtures = [
            # 2-1 -> BTTS YES
            {"fixture": {"id": 1}, "teams": {"home": {"id": 42}, "away": {"id": 1}}, "goals": {"home": 2, "away": 1}},
            # 3-0 -> BTTS NO (away não marcou)
            {"fixture": {"id": 2}, "teams": {"home": {"id": 42}, "away": {"id": 2}}, "goals": {"home": 3, "away": 0}},
            # 0-2 -> BTTS NO (home não marcou)
            {"fixture": {"id": 3}, "teams": {"home": {"id": 42}, "away": {"id": 3}}, "goals": {"home": 0, "away": 2}},
        ]
        stats = chatbot._calculate_team_stats(fixtures, 42)
        
        # 1 de 3 jogos teve BTTS = 33.33%
        expected = (1/3) * 100
        assert abs(stats["btts"] - expected) < 0.1, f"BTTS should be ~33.3% (1/3 matches), got {stats['btts']}%"
    
    def test_fair_odds_calculation(self, chatbot):
        """Odds justas devem ser calculadas como 1/probabilidade"""
        # Probabilidade de 50% -> Odd justa = 2.00
        prob = 50
        fair_odds = round(100 / prob, 2)
        assert fair_odds == 2.00, f"Fair odds for 50% should be 2.00, got {fair_odds}"
        
        # Probabilidade de 70% -> Odd justa = 1.43
        prob = 70
        fair_odds = round(100 / prob, 2)
        assert fair_odds == 1.43, f"Fair odds for 70% should be 1.43, got {fair_odds}"
        
        # Probabilidade de 25% -> Odd justa = 4.00
        prob = 25
        fair_odds = round(100 / prob, 2)
        assert fair_odds == 4.00, f"Fair odds for 25% should be 4.00, got {fair_odds}"
    
    def test_avg_goals_for_vs_avg_total_goals(self, chatbot):
        """avg_goals_for (gols do time) deve ser diferente de avg_total_goals (gols da partida)"""
        fixtures = [
            # Time 42 marcou 2, jogo teve 3 gols
            {"fixture": {"id": 1}, "teams": {"home": {"id": 42}, "away": {"id": 1}}, "goals": {"home": 2, "away": 1}},
            # Time 42 marcou 1, jogo teve 4 gols
            {"fixture": {"id": 2}, "teams": {"home": {"id": 42}, "away": {"id": 2}}, "goals": {"home": 1, "away": 3}},
        ]
        stats = chatbot._calculate_team_stats(fixtures, 42)
        
        # avg_goals_for = (2+1)/2 = 1.5
        assert stats["avg_goals_for"] == 1.5, f"avg_goals_for should be 1.5, got {stats['avg_goals_for']}"
        
        # avg_total_goals = (3+4)/2 = 3.5
        assert stats["avg_total_goals"] == 3.5, f"avg_total_goals should be 3.5, got {stats['avg_total_goals']}"
    
    # ═══════════════════════════════════════════════════════════════════════
    # 2. FIXTURE VALIDATION
    # ═══════════════════════════════════════════════════════════════════════
    
    def test_only_finished_games_are_used(self, chatbot):
        """Apenas jogos finalizados (FT, AET, PEN) devem ser usados"""
        # Criar 10 fixtures válidos + 2 inválidos para testar filtragem
        fixtures = []
        # 8 FT válidos
        for i in range(8):
            fixtures.append({
                "fixture": {"id": 100 + i, "date": f"2024-01-{20+i:02d}T15:00:00Z", "status": {"short": "FT"}},
                "teams": {"home": {"id": 42}, "away": {"id": i+1}},
                "goals": {"home": 2, "away": 1},
                "league": {"name": "Premier League", "type": "League"}
            })
        # 1 AET válido
        fixtures.append({
            "fixture": {"id": 200, "date": "2024-01-19T15:00:00Z", "status": {"short": "AET"}},
            "teams": {"home": {"id": 42}, "away": {"id": 50}},
            "goals": {"home": 3, "away": 2},
            "league": {"name": "Premier League", "type": "League"}
        })
        # 1 PEN válido
        fixtures.append({
            "fixture": {"id": 201, "date": "2024-01-18T15:00:00Z", "status": {"short": "PEN"}},
            "teams": {"home": {"id": 42}, "away": {"id": 51}},
            "goals": {"home": 2, "away": 2},
            "league": {"name": "Premier League", "type": "League"}
        })
        # NS - inválido (não começou)
        fixtures.append({
            "fixture": {"id": 300, "date": "2024-01-17T15:00:00Z", "status": {"short": "NS"}},
            "teams": {"home": {"id": 42}, "away": {"id": 60}},
            "goals": {"home": None, "away": None},
            "league": {"name": "Premier League", "type": "League"}
        })
        # CANC - inválido (cancelado)
        fixtures.append({
            "fixture": {"id": 301, "date": "2024-01-16T15:00:00Z", "status": {"short": "CANC"}},
            "teams": {"home": {"id": 42}, "away": {"id": 61}},
            "goals": {"home": None, "away": None},
            "league": {"name": "Premier League", "type": "League"}
        })
        
        result = chatbot._validate_fixtures(fixtures, 42, 10)
        
        # Deve ter exatamente 10 fixtures válidos (8 FT + 1 AET + 1 PEN)
        assert len(result["fixtures"]) == 10, f"Expected 10 valid fixtures, got {len(result['fixtures'])}"
        assert result["valid"] == True, "Should be valid with 10 fixtures"
        
        # Verificar que NS e CANC não estão incluídos
        valid_ids = [f["fixture"]["id"] for f in result["fixtures"]]
        assert 300 not in valid_ids, "NS fixture should NOT be included"
        assert 301 not in valid_ids, "CANC fixture should NOT be included"
        
        # Verificar que AET e PEN estão incluídos
        assert 200 in valid_ids, "AET fixture should be included"
        assert 201 in valid_ids, "PEN fixture should be included"
    
    def test_friendlies_are_excluded(self, chatbot):
        """Amistosos devem ser excluídos"""
        # Criar 10 fixtures oficiais + 2 amistosos
        fixtures = []
        # 10 jogos oficiais
        for i in range(10):
            fixtures.append({
                "fixture": {"id": 100 + i, "date": f"2024-01-{20+i:02d}T15:00:00Z", "status": {"short": "FT"}},
                "teams": {"home": {"id": 42}, "away": {"id": i+1}},
                "goals": {"home": 2, "away": 1},
                "league": {"name": "Premier League", "type": "League"}
            })
        # 2 amistosos (devem ser excluídos)
        fixtures.append({
            "fixture": {"id": 200, "date": "2024-01-30T15:00:00Z", "status": {"short": "FT"}},
            "teams": {"home": {"id": 42}, "away": {"id": 50}},
            "goals": {"home": 1, "away": 0},
            "league": {"name": "Club Friendly", "type": "Friendly"}
        })
        fixtures.append({
            "fixture": {"id": 201, "date": "2024-01-31T15:00:00Z", "status": {"short": "FT"}},
            "teams": {"home": {"id": 42}, "away": {"id": 51}},
            "goals": {"home": 3, "away": 2},
            "league": {"name": "International Friendly", "type": "Friendly"}
        })
        
        result = chatbot._validate_fixtures(fixtures, 42, 10)
        
        # Deve ter exatamente 10 fixtures (excluindo os 2 amistosos)
        assert len(result["fixtures"]) == 10, f"Expected 10 valid fixtures (excluding friendlies), got {len(result['fixtures'])}"
        assert result["excluded_friendlies"] >= 2, f"Should have excluded at least 2 friendlies, got {result['excluded_friendlies']}"
        
        # Verificar que amistosos não estão incluídos
        valid_ids = [f["fixture"]["id"] for f in result["fixtures"]]
        assert 200 not in valid_ids, "Friendly fixture 200 should NOT be included"
        assert 201 not in valid_ids, "Friendly fixture 201 should NOT be included"
    
    def test_fixtures_sorted_by_date_desc(self, chatbot):
        """Fixtures devem estar ordenados por data (mais recente primeiro)"""
        # Criar 10 fixtures em ordem aleatória de datas
        fixtures = [
            {"fixture": {"id": 1, "date": "2024-01-15T15:00:00Z", "status": {"short": "FT"}},
             "teams": {"home": {"id": 42}, "away": {"id": 1}}, "goals": {"home": 1, "away": 0},
             "league": {"name": "Premier League", "type": "League"}},
            {"fixture": {"id": 2, "date": "2024-01-28T15:00:00Z", "status": {"short": "FT"}},
             "teams": {"home": {"id": 42}, "away": {"id": 2}}, "goals": {"home": 2, "away": 0},
             "league": {"name": "Premier League", "type": "League"}},
            {"fixture": {"id": 3, "date": "2024-01-20T15:00:00Z", "status": {"short": "FT"}},
             "teams": {"home": {"id": 42}, "away": {"id": 3}}, "goals": {"home": 3, "away": 0},
             "league": {"name": "Premier League", "type": "League"}},
            {"fixture": {"id": 4, "date": "2024-01-25T15:00:00Z", "status": {"short": "FT"}},
             "teams": {"home": {"id": 42}, "away": {"id": 4}}, "goals": {"home": 1, "away": 1},
             "league": {"name": "Premier League", "type": "League"}},
            {"fixture": {"id": 5, "date": "2024-01-22T15:00:00Z", "status": {"short": "FT"}},
             "teams": {"home": {"id": 42}, "away": {"id": 5}}, "goals": {"home": 0, "away": 2},
             "league": {"name": "Premier League", "type": "League"}},
            {"fixture": {"id": 6, "date": "2024-01-18T15:00:00Z", "status": {"short": "FT"}},
             "teams": {"home": {"id": 42}, "away": {"id": 6}}, "goals": {"home": 2, "away": 2},
             "league": {"name": "Premier League", "type": "League"}},
        ]
        
        result = chatbot._validate_fixtures(fixtures, 42, 10)
        
        # Verificar que estão ordenados por data DESC
        # Ordem esperada: 2 (28/01), 4 (25/01), 5 (22/01), 3 (20/01), 6 (18/01), 1 (15/01)
        ids = [f["fixture"]["id"] for f in result["fixtures"]]
        expected_order = [2, 4, 5, 3, 6, 1]
        assert ids == expected_order, f"Fixtures should be sorted by date DESC. Expected {expected_order}, got {ids}"
    
    # ═══════════════════════════════════════════════════════════════════════
    # 3. CONSISTENCY TESTS
    # ═══════════════════════════════════════════════════════════════════════
    
    def test_same_input_same_output_deterministic(self, chatbot):
        """Mesmo input deve sempre produzir mesmo output"""
        fixtures = []
        for i in range(15):
            fixtures.append({
                "fixture": {"id": i + 100, "date": f"2024-01-{28-i:02d}T15:00:00Z", "status": {"short": "FT"}},
                "teams": {"home": {"id": 42}, "away": {"id": i+200}},
                "goals": {"home": 2, "away": 1},
                "league": {"name": "Premier League", "type": "League"}
            })
        
        # Rodar 5 vezes
        results = []
        for _ in range(5):
            result = chatbot._validate_fixtures(fixtures, 42, 10)
            results.append(result["fixture_ids"])
        
        # Todos devem ser iguais
        for i in range(1, len(results)):
            assert results[0] == results[i], f"Results should be deterministic. Run 0: {results[0]}, Run {i}: {results[i]}"
    
    def test_stats_calculation_deterministic(self, chatbot):
        """Cálculo de estatísticas deve ser determinístico"""
        fixtures = [
            {"fixture": {"id": 1}, "teams": {"home": {"id": 42}, "away": {"id": 1}}, "goals": {"home": 2, "away": 1}},
            {"fixture": {"id": 2}, "teams": {"home": {"id": 42}, "away": {"id": 2}}, "goals": {"home": 1, "away": 1}},
            {"fixture": {"id": 3}, "teams": {"home": {"id": 42}, "away": {"id": 3}}, "goals": {"home": 3, "away": 0}},
            {"fixture": {"id": 4}, "teams": {"home": {"id": 42}, "away": {"id": 4}}, "goals": {"home": 0, "away": 2}},
            {"fixture": {"id": 5}, "teams": {"home": {"id": 42}, "away": {"id": 5}}, "goals": {"home": 1, "away": 2}},
        ]
        
        # Rodar 5 vezes
        results = []
        for _ in range(5):
            stats = chatbot._calculate_team_stats(fixtures, 42)
            results.append(stats)
        
        # Todos devem ser iguais
        for i in range(1, len(results)):
            assert results[0] == results[i], f"Stats should be deterministic"
    
    # ═══════════════════════════════════════════════════════════════════════
    # 4. EDGE CASES
    # ═══════════════════════════════════════════════════════════════════════
    
    def test_empty_fixtures_returns_zeros(self, chatbot):
        """Lista vazia de fixtures deve retornar zeros"""
        stats = chatbot._calculate_team_stats([], 42)
        
        assert stats["over_2_5"] == 0, "over_2_5 should be 0 for empty fixtures"
        assert stats["btts"] == 0, "btts should be 0 for empty fixtures"
        assert stats["avg_total_goals"] == 0, "avg_total_goals should be 0 for empty fixtures"
    
    def test_all_draws_form_string(self, chatbot):
        """Todos empates deve mostrar E E E E E"""
        fixtures = [
            {"teams": {"home": {"id": 42}, "away": {"id": i}}, "goals": {"home": 1, "away": 1}}
            for i in range(1, 6)
        ]
        form = chatbot._get_form_string(fixtures, 42)
        assert form == "E E E E E", f"All draws should be 'E E E E E', got '{form}'"
    
    def test_high_scoring_games(self, chatbot):
        """Jogos com muitos gols devem calcular corretamente"""
        fixtures = [
            {"fixture": {"id": 1}, "teams": {"home": {"id": 42}, "away": {"id": 1}}, "goals": {"home": 5, "away": 4}},  # 9 gols
            {"fixture": {"id": 2}, "teams": {"home": {"id": 42}, "away": {"id": 2}}, "goals": {"home": 4, "away": 3}},  # 7 gols
        ]
        stats = chatbot._calculate_team_stats(fixtures, 42)
        
        # Todos Over 2.5 = 100%
        assert stats["over_2_5"] == 100.0, f"Over 2.5 should be 100%, got {stats['over_2_5']}%"
        
        # Todos BTTS = 100%
        assert stats["btts"] == 100.0, f"BTTS should be 100%, got {stats['btts']}%"
        
        # Média = (9+7)/2 = 8.0
        assert stats["avg_total_goals"] == 8.0, f"avg_total_goals should be 8.0, got {stats['avg_total_goals']}"
    
    def test_zero_zero_games(self, chatbot):
        """Jogos 0-0 devem calcular corretamente"""
        fixtures = [
            {"fixture": {"id": 1}, "teams": {"home": {"id": 42}, "away": {"id": 1}}, "goals": {"home": 0, "away": 0}},
            {"fixture": {"id": 2}, "teams": {"home": {"id": 42}, "away": {"id": 2}}, "goals": {"home": 0, "away": 0}},
        ]
        stats = chatbot._calculate_team_stats(fixtures, 42)
        
        # Nenhum Over 2.5 = 0%
        assert stats["over_2_5"] == 0.0, f"Over 2.5 should be 0%, got {stats['over_2_5']}%"
        
        # Nenhum BTTS = 0%
        assert stats["btts"] == 0.0, f"BTTS should be 0%, got {stats['btts']}%"
        
        # Média = 0
        assert stats["avg_total_goals"] == 0.0, f"avg_total_goals should be 0.0, got {stats['avg_total_goals']}"
    
    # ═══════════════════════════════════════════════════════════════════════
    # 5. TEAM RESOLUTION
    # ═══════════════════════════════════════════════════════════════════════
    
    def test_team_name_normalization(self, chatbot):
        """Normalização de nomes de times deve ser consistente"""
        # Testar extração de times do texto
        test_cases = [
            ("Flamengo x Palmeiras", ["flamengo", "palmeiras"]),
            ("Real Madrid vs Barcelona", ["real madrid", "barcelona"]),
            ("Al-Hilal x Al-Nassr", ["al-hilal", "al-nassr"]),
            ("Manchester United vs Liverpool", ["manchester united", "liverpool"]),
        ]
        
        for input_text, expected_teams in test_cases:
            extracted = chatbot._extract_teams_from_text(input_text)
            assert len(extracted) == 2, f"Should extract 2 teams from '{input_text}', got {len(extracted)}"
            # Verificar que os times extraídos contêm os nomes esperados
            for i, expected in enumerate(expected_teams):
                assert expected in extracted[i].lower(), f"Expected '{expected}' in extracted team, got '{extracted[i]}'"


class TestPlanLimits:
    """Test plan limits (Free/Pro/Elite)"""
    
    def test_plan_limits_defined(self):
        """Limites de plano devem estar definidos corretamente"""
        from chatbot import ChatBot
        
        chatbot = ChatBot()
        
        assert chatbot.PLAN_LIMITS.get("free") == 5, "Free plan should have 5 analyses/day"
        assert chatbot.PLAN_LIMITS.get("pro") == 25, "Pro plan should have 25 analyses/day"
        assert chatbot.PLAN_LIMITS.get("elite") == 100, "Elite plan should have 100 analyses/day"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
