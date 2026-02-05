"""
BetFaro QA Mass Runner
=======================
Script para validar o sistema com jogos reais em massa.

Executa análises em 50+ jogos e valida:
1. Retornou 10 fixtures por time
2. Percentuais e médias batem com recomputação
3. Nenhuma inconsistência

USAGE:
    python run_qa_mass.py [--limit N] [--region REGION]

OPTIONS:
    --limit N       Número máximo de jogos a testar (default: 50)
    --region REGION Região: brazil, europe, asia, all (default: all)
"""

import asyncio
import argparse
import json
import sys
import os
from datetime import datetime, timezone
from typing import Dict, List, Tuple
import logging

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fixture_processor import FixtureProcessor
from football_api import FootballAPI

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Test teams by region
BRAZIL_TEAMS = [
    "Flamengo", "Palmeiras", "Corinthians", "São Paulo",
    "Atlético-MG", "Cruzeiro", "Internacional", "Grêmio",
    "Fluminense", "Botafogo", "Santos", "Bahia",
    "Fortaleza", "Ceará", "Athletico-PR", "Vasco"
]

EUROPE_TEAMS = [
    "Arsenal", "Chelsea", "Liverpool", "Manchester City",
    "Manchester United", "Tottenham", "Newcastle", "West Ham",
    "Real Madrid", "Barcelona", "Atletico Madrid", "Sevilla",
    "Bayern Munich", "Borussia Dortmund", "Bayer Leverkusen", "RB Leipzig",
    "PSG", "Marseille", "Lyon", "Monaco",
    "Juventus", "Inter", "AC Milan", "Napoli",
    "Benfica", "Porto", "Sporting CP", "Braga"
]

ASIA_TEAMS = [
    "Al-Hilal", "Al-Nassr", "Al-Ittihad", "Al-Ahli",
    "Al-Shabab", "Al-Fateh", "Al-Taawoun", "Damac",
    "Urawa Red Diamonds", "Yokohama F. Marinos",
    "Kawasaki Frontale", "Vissel Kobe"
]


class QAResult:
    """Stores QA test results"""
    
    def __init__(self):
        self.total = 0
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.errors = []
        self.details = []
    
    def add_pass(self, team: str, details: Dict):
        self.total += 1
        self.passed += 1
        self.details.append({"team": team, "status": "PASSED", "details": details})
    
    def add_fail(self, team: str, reason: str, details: Dict):
        self.total += 1
        self.failed += 1
        self.errors.append({"team": team, "reason": reason})
        self.details.append({"team": team, "status": "FAILED", "reason": reason, "details": details})
    
    def add_skip(self, team: str, reason: str):
        self.total += 1
        self.skipped += 1
        self.details.append({"team": team, "status": "SKIPPED", "reason": reason})
    
    def get_summary(self) -> Dict:
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "pass_rate": f"{(self.passed/self.total)*100:.1f}%" if self.total > 0 else "0%",
            "errors": self.errors
        }


async def validate_team(
    api: FootballAPI,
    processor: FixtureProcessor,
    team_name: str
) -> Tuple[bool, str, Dict]:
    """
    Validate a single team's data.
    
    Returns:
        (success, error_message, details)
    """
    details = {
        "team_name": team_name,
        "team_id": None,
        "fixtures_count": 0,
        "form": None,
        "stats": None,
        "consistency_valid": None
    }
    
    try:
        # Step 1: Resolve team
        team = await api.resolve_team(team_name)
        if not team:
            return False, f"Could not resolve team: {team_name}", details
        
        details["team_id"] = team["id"]
        details["team_resolved_name"] = team.get("name", team_name)
        
        # Step 2: Get fixtures from API
        raw_fixtures = await api.get_team_fixtures(team["id"], 30)
        if not raw_fixtures:
            return False, f"No fixtures returned from API", details
        
        # Step 3: Process fixtures using canonical function
        result = processor.get_last_team_fixtures(raw_fixtures, team["id"], 10)
        
        if not result["valid"]:
            return False, f"Fixture validation failed: {result['errors']}", details
        
        details["fixtures_count"] = len(result["fixtures"])
        details["fixture_ids"] = result["fixture_ids"]
        
        # Step 4: Calculate stats
        stats = processor.calculate_stats(result["fixtures"], team["id"])
        details["stats"] = {
            "over_2_5_pct": round(stats["over_2_5_pct"], 1),
            "btts_pct": round(stats["btts_pct"], 1),
            "avg_goals_for": round(stats["avg_goals_for"], 2),
            "avg_goals_against": round(stats["avg_goals_against"], 2),
            "avg_total_goals": round(stats["avg_total_goals_per_match"], 2),
            "win_rate_pct": round(stats["win_rate_pct"], 1)
        }
        
        # Step 5: Get form
        form = processor.get_form_string(result["fixtures"], team["id"], 5)
        details["form"] = form
        
        # Step 6: CRITICAL - Validate consistency (self-check)
        consistency = processor.validate_stats_consistency(
            result["fixtures"], stats, form, team["id"]
        )
        
        details["consistency_valid"] = consistency["valid"]
        
        if not consistency["valid"]:
            return False, f"Consistency check failed: {consistency['issues']}", details
        
        # All checks passed
        return True, None, details
        
    except Exception as e:
        return False, f"Exception: {str(e)}", details


async def run_qa_mass(teams: List[str], limit: int = 50) -> QAResult:
    """
    Run QA validation on multiple teams.
    """
    api = FootballAPI()
    processor = FixtureProcessor()
    result = QAResult()
    
    teams_to_test = teams[:limit]
    
    print(f"\n{'='*60}")
    print(f"🔍 BetFaro QA Mass Runner")
    print(f"{'='*60}")
    print(f"Teams to test: {len(teams_to_test)}")
    print(f"{'='*60}\n")
    
    for i, team_name in enumerate(teams_to_test):
        print(f"[{i+1}/{len(teams_to_test)}] Testing: {team_name}...", end=" ", flush=True)
        
        success, error, details = await validate_team(api, processor, team_name)
        
        if success:
            print("✅ PASSED")
            result.add_pass(team_name, details)
        elif error and "Could not resolve" in error:
            print(f"⏭️ SKIPPED ({error[:40]})")
            result.add_skip(team_name, error)
        else:
            print(f"❌ FAILED ({error[:50] if error else 'Unknown'})")
            result.add_fail(team_name, error, details)
        
        # Small delay to avoid rate limiting
        await asyncio.sleep(0.5)
    
    return result


def print_report(result: QAResult, output_file: str = None):
    """Print and optionally save the QA report"""
    
    summary = result.get_summary()
    
    report = []
    report.append("\n" + "="*60)
    report.append("📊 QA MASS TEST REPORT")
    report.append("="*60)
    report.append(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    report.append(f"Total Teams Tested: {summary['total']}")
    report.append(f"Passed: {summary['passed']}")
    report.append(f"Failed: {summary['failed']}")
    report.append(f"Skipped: {summary['skipped']}")
    report.append(f"Pass Rate: {summary['pass_rate']}")
    report.append("="*60)
    
    if summary['failed'] > 0:
        report.append("\n❌ FAILED TESTS:")
        report.append("-"*60)
        for error in summary['errors']:
            report.append(f"  • {error['team']}: {error['reason'][:60]}")
    
    # Determine status
    if summary['failed'] == 0:
        report.append("\n" + "="*60)
        report.append("✅ STATUS: READY FOR PRODUCTION")
        report.append("   All tests passed. System is mathematically consistent.")
        report.append("="*60)
        status = "READY"
    else:
        report.append("\n" + "="*60)
        report.append("❌ STATUS: BLOCKED")
        report.append(f"   {summary['failed']} test(s) failed. Fix issues before deploy.")
        report.append("="*60)
        status = "BLOCKED"
    
    # Print to console
    for line in report:
        print(line)
    
    # Save to file if requested
    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(report))
            f.write("\n\n# Detailed Results\n")
            f.write(json.dumps(result.details, indent=2, ensure_ascii=False))
        print(f"\n📄 Report saved to: {output_file}")
    
    return status


def main():
    parser = argparse.ArgumentParser(description="BetFaro QA Mass Runner")
    parser.add_argument("--limit", type=int, default=50, help="Max teams to test")
    parser.add_argument("--region", choices=["brazil", "europe", "asia", "all"], default="all")
    parser.add_argument("--output", type=str, help="Output file for report")
    args = parser.parse_args()
    
    # Check for API key
    if not os.getenv("APISPORTS_KEY"):
        print("❌ ERROR: APISPORTS_KEY environment variable not set")
        print("   Please set your API-Football key to run QA tests.")
        sys.exit(1)
    
    # Select teams based on region
    if args.region == "brazil":
        teams = BRAZIL_TEAMS
    elif args.region == "europe":
        teams = EUROPE_TEAMS
    elif args.region == "asia":
        teams = ASIA_TEAMS
    else:
        teams = BRAZIL_TEAMS + EUROPE_TEAMS + ASIA_TEAMS
    
    # Run QA
    result = asyncio.run(run_qa_mass(teams, args.limit))
    
    # Print report
    output_file = args.output or f"qa_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    status = print_report(result, output_file)
    
    # Exit with appropriate code
    sys.exit(0 if status == "READY" else 1)


if __name__ == "__main__":
    main()
