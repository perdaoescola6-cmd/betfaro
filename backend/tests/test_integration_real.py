"""
BetFaro Integration Tests - Real Matches
=========================================
Testes de integração com jogos REAIS da API-Football.
Valida consistência de dados, cálculos e output.

Cobertura:
- 10 jogos do Brasil
- 10 jogos da Europa
- 10 jogos da Ásia/Arábia

IMPORTANTE: Requer APISPORTS_KEY configurada.
"""

import pytest
import sys
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import logging

sys.path.insert(0, '..')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Skip all tests if no API key
APISPORTS_KEY = os.getenv("APISPORTS_KEY")

# Test data - teams from different regions
BRAZIL_TEAMS = [
    ("Flamengo", "Palmeiras"),
    ("Corinthians", "São Paulo"),
    ("Atlético-MG", "Cruzeiro"),
    ("Internacional", "Grêmio"),
    ("Fluminense", "Botafogo"),
    ("Santos", "Bahia"),
    ("Fortaleza", "Ceará"),
    ("Athletico-PR", "Coritiba"),
    ("Vasco", "Flamengo"),
    ("Red Bull Bragantino", "Palmeiras"),
]

EUROPE_TEAMS = [
    ("Arsenal", "Chelsea"),
    ("Liverpool", "Manchester City"),
    ("Real Madrid", "Barcelona"),
    ("Bayern Munich", "Borussia Dortmund"),
    ("PSG", "Marseille"),
    ("Juventus", "Inter"),
    ("AC Milan", "Napoli"),
    ("Benfica", "Porto"),
    ("Ajax", "PSV"),
    ("Atletico Madrid", "Sevilla"),
]

ASIA_TEAMS = [
    ("Al-Hilal", "Al-Nassr"),
    ("Al-Ittihad", "Al-Ahli"),
    ("Al-Shabab", "Al-Fateh"),
    ("Al-Taawoun", "Al-Khaleej"),
    ("Damac", "Al-Riyadh"),
    ("Urawa Red Diamonds", "Yokohama F. Marinos"),
    ("Kawasaki Frontale", "Vissel Kobe"),
    ("Jeonbuk Motors", "Ulsan Hyundai"),
    ("Shanghai Port", "Beijing Guoan"),
    ("Guangzhou FC", "Shandong Taishan"),
]


class IntegrationTestResult:
    """Store results of integration tests"""
    def __init__(self):
        self.total = 0
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.results = []
    
    def add_result(self, match: str, region: str, status: str, details: Dict):
        self.total += 1
        if status == "PASSED":
            self.passed += 1
        elif status == "FAILED":
            self.failed += 1
        else:
            self.skipped += 1
        
        self.results.append({
            "match": match,
            "region": region,
            "status": status,
            "details": details
        })
    
    def to_dict(self) -> Dict:
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "pass_rate": f"{(self.passed/self.total)*100:.1f}%" if self.total > 0 else "0%",
            "results": self.results
        }


class TestIntegrationReal:
    """Integration tests with real API data"""
    
    @pytest.fixture
    def chatbot(self):
        from chatbot import ChatBot
        return ChatBot()
    
    @pytest.fixture
    def api(self):
        from football_api import FootballAPI
        return FootballAPI()
    
    @pytest.fixture
    def analysis_logger(self):
        from analysis_logger import AnalysisLogger
        return AnalysisLogger()
    
    def validate_match_data(
        self, 
        chatbot, 
        api, 
        analysis_logger,
        team_a_name: str, 
        team_b_name: str
    ) -> Tuple[bool, Dict]:
        """
        Validate match data for a pair of teams.
        Returns (success, details)
        """
        import asyncio
        
        async def _validate():
            details = {
                "team_a_name": team_a_name,
                "team_b_name": team_b_name,
                "team_a_resolved": None,
                "team_b_resolved": None,
                "fixtures_a_count": 0,
                "fixtures_b_count": 0,
                "form_a": None,
                "form_b": None,
                "stats_a": None,
                "stats_b": None,
                "consistency_a": None,
                "consistency_b": None,
                "errors": []
            }
            
            try:
                # Step 1: Resolve teams
                team_a = await api.resolve_team(team_a_name)
                team_b = await api.resolve_team(team_b_name)
                
                if not team_a:
                    details["errors"].append(f"Could not resolve team: {team_a_name}")
                    return False, details
                if not team_b:
                    details["errors"].append(f"Could not resolve team: {team_b_name}")
                    return False, details
                
                details["team_a_resolved"] = {"id": team_a["id"], "name": team_a["name"]}
                details["team_b_resolved"] = {"id": team_b["id"], "name": team_b["name"]}
                
                # Step 2: Get fixtures
                fixtures_a_raw = await api.get_team_fixtures(team_a["id"], 30)
                fixtures_b_raw = await api.get_team_fixtures(team_b["id"], 30)
                
                # Step 3: Validate fixtures
                validated_a = chatbot._validate_fixtures(fixtures_a_raw, team_a["id"], 10)
                validated_b = chatbot._validate_fixtures(fixtures_b_raw, team_b["id"], 10)
                
                details["fixtures_a_count"] = len(validated_a.get("fixtures", []))
                details["fixtures_b_count"] = len(validated_b.get("fixtures", []))
                
                if not validated_a["valid"]:
                    details["errors"].append(f"Team A fixtures invalid: {validated_a.get('errors', [])}")
                if not validated_b["valid"]:
                    details["errors"].append(f"Team B fixtures invalid: {validated_b.get('errors', [])}")
                
                if not validated_a["valid"] or not validated_b["valid"]:
                    return False, details
                
                filtered_a = validated_a["fixtures"]
                filtered_b = validated_b["fixtures"]
                
                # Step 4: Calculate stats
                stats_a = chatbot._calculate_team_stats(filtered_a, team_a["id"])
                stats_b = chatbot._calculate_team_stats(filtered_b, team_b["id"])
                
                details["stats_a"] = {
                    "over_2_5": stats_a.get("over_2_5"),
                    "btts": stats_a.get("btts"),
                    "avg_total_goals": stats_a.get("avg_total_goals"),
                    "avg_goals_for": stats_a.get("avg_goals_for")
                }
                details["stats_b"] = {
                    "over_2_5": stats_b.get("over_2_5"),
                    "btts": stats_b.get("btts"),
                    "avg_total_goals": stats_b.get("avg_total_goals"),
                    "avg_goals_for": stats_b.get("avg_goals_for")
                }
                
                # Step 5: Get form strings
                form_a = chatbot._get_form_string(filtered_a[:5], team_a["id"])
                form_b = chatbot._get_form_string(filtered_b[:5], team_b["id"])
                
                details["form_a"] = form_a
                details["form_b"] = form_b
                
                # Step 6: Validate consistency (CRITICAL)
                consistency_a = analysis_logger.validate_consistency(
                    filtered_a, stats_a, form_a, team_a["id"]
                )
                consistency_b = analysis_logger.validate_consistency(
                    filtered_b, stats_b, form_b, team_b["id"]
                )
                
                details["consistency_a"] = consistency_a
                details["consistency_b"] = consistency_b
                
                if not consistency_a["valid"]:
                    details["errors"].extend(consistency_a.get("issues", []))
                if not consistency_b["valid"]:
                    details["errors"].extend(consistency_b.get("issues", []))
                
                # Final validation
                if consistency_a["valid"] and consistency_b["valid"]:
                    return True, details
                else:
                    return False, details
                    
            except Exception as e:
                details["errors"].append(f"Exception: {str(e)}")
                return False, details
        
        return asyncio.get_event_loop().run_until_complete(_validate())
    
    @pytest.mark.skipif(not APISPORTS_KEY, reason="APISPORTS_KEY not configured")
    def test_brazil_matches(self, chatbot, api, analysis_logger):
        """Test 10 Brazilian matches"""
        results = IntegrationTestResult()
        
        for team_a, team_b in BRAZIL_TEAMS[:10]:
            match_name = f"{team_a} vs {team_b}"
            logger.info(f"Testing: {match_name}")
            
            success, details = self.validate_match_data(
                chatbot, api, analysis_logger, team_a, team_b
            )
            
            status = "PASSED" if success else "FAILED"
            results.add_result(match_name, "Brazil", status, details)
            
            if not success:
                logger.warning(f"FAILED: {match_name} - {details.get('errors', [])}")
        
        # Assert at least 70% pass rate
        pass_rate = results.passed / results.total if results.total > 0 else 0
        assert pass_rate >= 0.7, f"Brazil tests pass rate too low: {pass_rate:.0%}"
        
        logger.info(f"Brazil tests: {results.passed}/{results.total} passed")
    
    @pytest.mark.skipif(not APISPORTS_KEY, reason="APISPORTS_KEY not configured")
    def test_europe_matches(self, chatbot, api, analysis_logger):
        """Test 10 European matches"""
        results = IntegrationTestResult()
        
        for team_a, team_b in EUROPE_TEAMS[:10]:
            match_name = f"{team_a} vs {team_b}"
            logger.info(f"Testing: {match_name}")
            
            success, details = self.validate_match_data(
                chatbot, api, analysis_logger, team_a, team_b
            )
            
            status = "PASSED" if success else "FAILED"
            results.add_result(match_name, "Europe", status, details)
            
            if not success:
                logger.warning(f"FAILED: {match_name} - {details.get('errors', [])}")
        
        pass_rate = results.passed / results.total if results.total > 0 else 0
        assert pass_rate >= 0.7, f"Europe tests pass rate too low: {pass_rate:.0%}"
        
        logger.info(f"Europe tests: {results.passed}/{results.total} passed")
    
    @pytest.mark.skipif(not APISPORTS_KEY, reason="APISPORTS_KEY not configured")
    def test_asia_matches(self, chatbot, api, analysis_logger):
        """Test 10 Asian/Saudi matches"""
        results = IntegrationTestResult()
        
        for team_a, team_b in ASIA_TEAMS[:10]:
            match_name = f"{team_a} vs {team_b}"
            logger.info(f"Testing: {match_name}")
            
            success, details = self.validate_match_data(
                chatbot, api, analysis_logger, team_a, team_b
            )
            
            status = "PASSED" if success else "FAILED"
            results.add_result(match_name, "Asia", status, details)
            
            if not success:
                logger.warning(f"FAILED: {match_name} - {details.get('errors', [])}")
        
        pass_rate = results.passed / results.total if results.total > 0 else 0
        # Asia might have lower pass rate due to less data availability
        assert pass_rate >= 0.5, f"Asia tests pass rate too low: {pass_rate:.0%}"
        
        logger.info(f"Asia tests: {results.passed}/{results.total} passed")


class TestCrossUserConsistency:
    """Test that same input produces same output for different users"""
    
    @pytest.fixture
    def chatbot(self):
        from chatbot import ChatBot
        return ChatBot()
    
    @pytest.fixture
    def api(self):
        from football_api import FootballAPI
        return FootballAPI()
    
    @pytest.mark.skipif(not APISPORTS_KEY, reason="APISPORTS_KEY not configured")
    def test_same_input_different_users(self, chatbot, api):
        """
        Simulate same input for two different users.
        Results should be IDENTICAL except for user_id and quota.
        """
        import asyncio
        
        async def _test():
            # Test with a well-known match
            test_matches = [
                ("Arsenal", "Chelsea"),
                ("Real Madrid", "Barcelona"),
                ("Flamengo", "Palmeiras"),
            ]
            
            for team_a_name, team_b_name in test_matches:
                logger.info(f"Testing cross-user consistency: {team_a_name} vs {team_b_name}")
                
                # Resolve teams (should be same for both users)
                team_a = await api.resolve_team(team_a_name)
                team_b = await api.resolve_team(team_b_name)
                
                if not team_a or not team_b:
                    logger.warning(f"Could not resolve teams: {team_a_name}, {team_b_name}")
                    continue
                
                # Simulate User 1
                fixtures_a_1 = await api.get_team_fixtures(team_a["id"], 30)
                fixtures_b_1 = await api.get_team_fixtures(team_b["id"], 30)
                
                validated_a_1 = chatbot._validate_fixtures(fixtures_a_1, team_a["id"], 10)
                validated_b_1 = chatbot._validate_fixtures(fixtures_b_1, team_b["id"], 10)
                
                if not validated_a_1["valid"] or not validated_b_1["valid"]:
                    logger.warning(f"Insufficient data for: {team_a_name} vs {team_b_name}")
                    continue
                
                stats_a_1 = chatbot._calculate_team_stats(validated_a_1["fixtures"], team_a["id"])
                stats_b_1 = chatbot._calculate_team_stats(validated_b_1["fixtures"], team_b["id"])
                form_a_1 = chatbot._get_form_string(validated_a_1["fixtures"][:5], team_a["id"])
                form_b_1 = chatbot._get_form_string(validated_b_1["fixtures"][:5], team_b["id"])
                
                # Simulate User 2 (same exact process)
                fixtures_a_2 = await api.get_team_fixtures(team_a["id"], 30)
                fixtures_b_2 = await api.get_team_fixtures(team_b["id"], 30)
                
                validated_a_2 = chatbot._validate_fixtures(fixtures_a_2, team_a["id"], 10)
                validated_b_2 = chatbot._validate_fixtures(fixtures_b_2, team_b["id"], 10)
                
                stats_a_2 = chatbot._calculate_team_stats(validated_a_2["fixtures"], team_a["id"])
                stats_b_2 = chatbot._calculate_team_stats(validated_b_2["fixtures"], team_b["id"])
                form_a_2 = chatbot._get_form_string(validated_a_2["fixtures"][:5], team_a["id"])
                form_b_2 = chatbot._get_form_string(validated_b_2["fixtures"][:5], team_b["id"])
                
                # ASSERTIONS: Everything should be IDENTICAL
                assert validated_a_1["fixture_ids"] == validated_a_2["fixture_ids"], \
                    f"Fixture IDs differ for {team_a_name}: {validated_a_1['fixture_ids']} vs {validated_a_2['fixture_ids']}"
                
                assert validated_b_1["fixture_ids"] == validated_b_2["fixture_ids"], \
                    f"Fixture IDs differ for {team_b_name}: {validated_b_1['fixture_ids']} vs {validated_b_2['fixture_ids']}"
                
                assert stats_a_1 == stats_a_2, f"Stats differ for {team_a_name}"
                assert stats_b_1 == stats_b_2, f"Stats differ for {team_b_name}"
                
                assert form_a_1 == form_a_2, f"Form differs for {team_a_name}: {form_a_1} vs {form_a_2}"
                assert form_b_1 == form_b_2, f"Form differs for {team_b_name}: {form_b_1} vs {form_b_2}"
                
                logger.info(f"✅ Cross-user consistency PASSED for {team_a_name} vs {team_b_name}")
        
        asyncio.get_event_loop().run_until_complete(_test())


def run_full_integration_test():
    """
    Run full integration test suite and generate report.
    Can be called directly for manual testing.
    """
    import asyncio
    
    if not APISPORTS_KEY:
        print("❌ APISPORTS_KEY not configured. Cannot run integration tests.")
        return None
    
    from chatbot import ChatBot
    from football_api import FootballAPI
    from analysis_logger import AnalysisLogger
    
    chatbot = ChatBot()
    api = FootballAPI()
    analysis_logger = AnalysisLogger()
    
    all_results = IntegrationTestResult()
    
    async def _run():
        # Brazil
        print("\n" + "="*60)
        print("🇧🇷 TESTING BRAZIL MATCHES")
        print("="*60)
        
        for team_a, team_b in BRAZIL_TEAMS[:10]:
            match_name = f"{team_a} vs {team_b}"
            print(f"  Testing: {match_name}...", end=" ")
            
            try:
                team_a_obj = await api.resolve_team(team_a)
                team_b_obj = await api.resolve_team(team_b)
                
                if not team_a_obj or not team_b_obj:
                    print("❌ SKIPPED (team not found)")
                    all_results.add_result(match_name, "Brazil", "SKIPPED", {"error": "Team not found"})
                    continue
                
                fixtures_a = await api.get_team_fixtures(team_a_obj["id"], 30)
                fixtures_b = await api.get_team_fixtures(team_b_obj["id"], 30)
                
                validated_a = chatbot._validate_fixtures(fixtures_a, team_a_obj["id"], 10)
                validated_b = chatbot._validate_fixtures(fixtures_b, team_b_obj["id"], 10)
                
                if not validated_a["valid"] or not validated_b["valid"]:
                    print("❌ FAILED (insufficient data)")
                    all_results.add_result(match_name, "Brazil", "FAILED", {"error": "Insufficient data"})
                    continue
                
                stats_a = chatbot._calculate_team_stats(validated_a["fixtures"], team_a_obj["id"])
                stats_b = chatbot._calculate_team_stats(validated_b["fixtures"], team_b_obj["id"])
                form_a = chatbot._get_form_string(validated_a["fixtures"][:5], team_a_obj["id"])
                form_b = chatbot._get_form_string(validated_b["fixtures"][:5], team_b_obj["id"])
                
                consistency_a = analysis_logger.validate_consistency(
                    validated_a["fixtures"], stats_a, form_a, team_a_obj["id"]
                )
                consistency_b = analysis_logger.validate_consistency(
                    validated_b["fixtures"], stats_b, form_b, team_b_obj["id"]
                )
                
                if consistency_a["valid"] and consistency_b["valid"]:
                    print("✅ PASSED")
                    all_results.add_result(match_name, "Brazil", "PASSED", {
                        "form_a": form_a, "form_b": form_b,
                        "over_2_5_a": stats_a["over_2_5"], "over_2_5_b": stats_b["over_2_5"]
                    })
                else:
                    issues = consistency_a.get("issues", []) + consistency_b.get("issues", [])
                    print(f"❌ FAILED (consistency: {issues[:2]})")
                    all_results.add_result(match_name, "Brazil", "FAILED", {"issues": issues})
                    
            except Exception as e:
                print(f"❌ ERROR ({str(e)[:50]})")
                all_results.add_result(match_name, "Brazil", "FAILED", {"error": str(e)})
        
        # Europe
        print("\n" + "="*60)
        print("🇪🇺 TESTING EUROPE MATCHES")
        print("="*60)
        
        for team_a, team_b in EUROPE_TEAMS[:10]:
            match_name = f"{team_a} vs {team_b}"
            print(f"  Testing: {match_name}...", end=" ")
            
            try:
                team_a_obj = await api.resolve_team(team_a)
                team_b_obj = await api.resolve_team(team_b)
                
                if not team_a_obj or not team_b_obj:
                    print("❌ SKIPPED (team not found)")
                    all_results.add_result(match_name, "Europe", "SKIPPED", {"error": "Team not found"})
                    continue
                
                fixtures_a = await api.get_team_fixtures(team_a_obj["id"], 30)
                fixtures_b = await api.get_team_fixtures(team_b_obj["id"], 30)
                
                validated_a = chatbot._validate_fixtures(fixtures_a, team_a_obj["id"], 10)
                validated_b = chatbot._validate_fixtures(fixtures_b, team_b_obj["id"], 10)
                
                if not validated_a["valid"] or not validated_b["valid"]:
                    print("❌ FAILED (insufficient data)")
                    all_results.add_result(match_name, "Europe", "FAILED", {"error": "Insufficient data"})
                    continue
                
                stats_a = chatbot._calculate_team_stats(validated_a["fixtures"], team_a_obj["id"])
                stats_b = chatbot._calculate_team_stats(validated_b["fixtures"], team_b_obj["id"])
                form_a = chatbot._get_form_string(validated_a["fixtures"][:5], team_a_obj["id"])
                form_b = chatbot._get_form_string(validated_b["fixtures"][:5], team_b_obj["id"])
                
                consistency_a = analysis_logger.validate_consistency(
                    validated_a["fixtures"], stats_a, form_a, team_a_obj["id"]
                )
                consistency_b = analysis_logger.validate_consistency(
                    validated_b["fixtures"], stats_b, form_b, team_b_obj["id"]
                )
                
                if consistency_a["valid"] and consistency_b["valid"]:
                    print("✅ PASSED")
                    all_results.add_result(match_name, "Europe", "PASSED", {
                        "form_a": form_a, "form_b": form_b,
                        "over_2_5_a": stats_a["over_2_5"], "over_2_5_b": stats_b["over_2_5"]
                    })
                else:
                    issues = consistency_a.get("issues", []) + consistency_b.get("issues", [])
                    print(f"❌ FAILED (consistency: {issues[:2]})")
                    all_results.add_result(match_name, "Europe", "FAILED", {"issues": issues})
                    
            except Exception as e:
                print(f"❌ ERROR ({str(e)[:50]})")
                all_results.add_result(match_name, "Europe", "FAILED", {"error": str(e)})
        
        # Asia
        print("\n" + "="*60)
        print("🌏 TESTING ASIA/SAUDI MATCHES")
        print("="*60)
        
        for team_a, team_b in ASIA_TEAMS[:10]:
            match_name = f"{team_a} vs {team_b}"
            print(f"  Testing: {match_name}...", end=" ")
            
            try:
                team_a_obj = await api.resolve_team(team_a)
                team_b_obj = await api.resolve_team(team_b)
                
                if not team_a_obj or not team_b_obj:
                    print("❌ SKIPPED (team not found)")
                    all_results.add_result(match_name, "Asia", "SKIPPED", {"error": "Team not found"})
                    continue
                
                fixtures_a = await api.get_team_fixtures(team_a_obj["id"], 30)
                fixtures_b = await api.get_team_fixtures(team_b_obj["id"], 30)
                
                validated_a = chatbot._validate_fixtures(fixtures_a, team_a_obj["id"], 10)
                validated_b = chatbot._validate_fixtures(fixtures_b, team_b_obj["id"], 10)
                
                if not validated_a["valid"] or not validated_b["valid"]:
                    print("❌ FAILED (insufficient data)")
                    all_results.add_result(match_name, "Asia", "FAILED", {"error": "Insufficient data"})
                    continue
                
                stats_a = chatbot._calculate_team_stats(validated_a["fixtures"], team_a_obj["id"])
                stats_b = chatbot._calculate_team_stats(validated_b["fixtures"], team_b_obj["id"])
                form_a = chatbot._get_form_string(validated_a["fixtures"][:5], team_a_obj["id"])
                form_b = chatbot._get_form_string(validated_b["fixtures"][:5], team_b_obj["id"])
                
                consistency_a = analysis_logger.validate_consistency(
                    validated_a["fixtures"], stats_a, form_a, team_a_obj["id"]
                )
                consistency_b = analysis_logger.validate_consistency(
                    validated_b["fixtures"], stats_b, form_b, team_b_obj["id"]
                )
                
                if consistency_a["valid"] and consistency_b["valid"]:
                    print("✅ PASSED")
                    all_results.add_result(match_name, "Asia", "PASSED", {
                        "form_a": form_a, "form_b": form_b,
                        "over_2_5_a": stats_a["over_2_5"], "over_2_5_b": stats_b["over_2_5"]
                    })
                else:
                    issues = consistency_a.get("issues", []) + consistency_b.get("issues", [])
                    print(f"❌ FAILED (consistency: {issues[:2]})")
                    all_results.add_result(match_name, "Asia", "FAILED", {"issues": issues})
                    
            except Exception as e:
                print(f"❌ ERROR ({str(e)[:50]})")
                all_results.add_result(match_name, "Asia", "FAILED", {"error": str(e)})
    
    asyncio.get_event_loop().run_until_complete(_run())
    
    # Print summary
    print("\n" + "="*60)
    print("📊 INTEGRATION TEST SUMMARY")
    print("="*60)
    print(f"  Total: {all_results.total}")
    print(f"  Passed: {all_results.passed}")
    print(f"  Failed: {all_results.failed}")
    print(f"  Skipped: {all_results.skipped}")
    print(f"  Pass Rate: {all_results.to_dict()['pass_rate']}")
    print("="*60)
    
    return all_results


if __name__ == "__main__":
    results = run_full_integration_test()
    if results:
        # Save results to file
        with open("integration_test_results.json", "w") as f:
            json.dump(results.to_dict(), f, indent=2)
        print(f"\nResults saved to integration_test_results.json")
