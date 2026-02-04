#!/usr/bin/env python3
"""
FIXED Regression Checker - Automated Testing for Every Code Change

This version ONLY analyzes the 10 actual week files, not all variants.
Uses the authoritative unscheduled_analyzer.py service for top 5 detection.
"""

import sys
import json
import os
from pathlib import Path
from typing import Dict, List, Any
from core.services.unscheduled_analyzer import UnscheduledAnalyzer


class FixedRegressionChecker:
    """
    FIXED Automated regression checker for Summer Camp Scheduler.
    
    This version ONLY analyzes the 10 actual week files:
    - tc_week1_troops through tc_week8_troops
    - voyageur_week1_troops, voyageur_week3_troops
    
    NOT all 160 variant files.
    """
    
    def __init__(self):
        self.analyzer = UnscheduledAnalyzer()
        self.baseline_file = Path("baseline_metrics_10weeks.json")
        self.current_results = {}
        self.baseline_results = {}
        self.regressions_detected = []
        
        # Only the 10 actual week files
        self.target_weeks = [
            "tc_week1_troops",
            "tc_week2_troops", 
            "tc_week3_troops",
            "tc_week4_troops",
            "tc_week5_troops",
            "tc_week6_troops",
            "tc_week7_troops",
            "tc_week8_troops",
            "voyageur_week1_troops",
            "voyageur_week3_troops"
        ]
    
    def run_full_check(self, schedules_dir: str = "schedules") -> Dict[str, Any]:
        """
        Run comprehensive regression check on 10 actual weeks only.
        
        Args:
            schedules_dir: Directory containing schedule JSON files
            
        Returns:
            Complete regression report
        """
        print("FIXED Regression Checker - Analyzing 10 Actual Weeks Only")
        print("=" * 60)
        
        # Analyze current state for target weeks only
        print("Analyzing current schedules...")
        self._analyze_target_weeks(schedules_dir)
        self.current_results = self.analyzer.get_season_summary()
        
        # Load baseline if exists
        if self.baseline_file.exists():
            print("Loading baseline metrics...")
            with open(self.baseline_file, 'r') as f:
                self.baseline_results = json.load(f)
        
        # Check for regressions
        print("Checking for regressions...")
        self._check_top5_regressions()
        self._check_quality_regressions()
        self._check_data_consistency()
        
        # Generate report
        report = self._generate_regression_report()
        
        # Save current results as new baseline if no regressions
        if not self.regressions_detected:
            print("No regressions detected - updating baseline...")
            self._save_baseline()
        
        return report
    
    def _analyze_target_weeks(self, schedules_dir: str):
        """Analyze only the 10 target week files."""
        schedules_path = Path(schedules_dir)
        if not schedules_path.exists():
            raise FileNotFoundError(f"Schedules directory not found: {schedules_dir}")
        
        # Find the schedule files for target weeks
        target_schedule_files = []
        for week_name in self.target_weeks:
            # Look for the exact schedule file
            schedule_file = schedules_path / f"{week_name}_schedule.json"
            if schedule_file.exists():
                target_schedule_files.append(schedule_file)
            else:
                print(f"WARNING: Schedule file not found: {schedule_file}")
        
        print(f"Found {len(target_schedule_files)} target week files")
        
        # Analyze each target week
        for schedule_file in target_schedule_files:
            try:
                analysis = self.analyzer.analyze_week_from_schedule_json(schedule_file)
                self.analyzer.week_analyses[analysis.week_name] = analysis
            except Exception as e:
                print(f"Error analyzing {schedule_file}: {e}")
    
    def _check_top5_regressions(self):
        """Check for Top 5 satisfaction regressions."""
        if not self.baseline_results:
            print("No baseline found - will create new baseline")
            return
        
        current_success = self.current_results.get("season_success_rate", 0)
        baseline_success = self.baseline_results.get("season_success_rate", 0)
        
        # Check for significant drop in Top 5 success rate
        if current_success < baseline_success - 1.0:  # 1% tolerance
            self.regressions_detected.append({
                "type": "Top 5 Success Rate",
                "severity": "HIGH",
                "current": current_success,
                "baseline": baseline_success,
                "change": current_success - baseline_success,
                "description": f"Top 5 success rate dropped from {baseline_success:.1f}% to {current_success:.1f}%"
            })
        
        # Check for increase in counted misses
        current_misses = self.current_results.get("total_counted_misses", 0)
        baseline_misses = self.baseline_results.get("total_counted_misses", 0)
        
        if current_misses > baseline_misses:
            self.regressions_detected.append({
                "type": "Top 5 Missed Activities",
                "severity": "MEDIUM",
                "current": current_misses,
                "baseline": baseline_misses,
                "change": current_misses - baseline_misses,
                "description": f"Top 5 misses increased from {baseline_misses} to {current_misses}"
            })
        
        # Check for new problem weeks
        current_problem_weeks = self.current_results.get("weeks_with_issues", 0)
        baseline_problem_weeks = self.baseline_results.get("weeks_with_issues", 0)
        
        if current_problem_weeks > baseline_problem_weeks:
            self.regressions_detected.append({
                "type": "Problem Weeks",
                "severity": "MEDIUM",
                "current": current_problem_weeks,
                "baseline": baseline_problem_weeks,
                "change": current_problem_weeks - baseline_problem_weeks,
                "description": f"Weeks with Top 5 issues increased from {baseline_problem_weeks} to {current_problem_weeks}"
            })
    
    def _check_quality_regressions(self):
        """Check for schedule quality regressions."""
        # This would integrate with evaluate_week_success.py results
        # For now, we'll focus on Top 5 since that's the primary concern
        pass
    
    def _check_data_consistency(self):
        """Check for data consistency issues."""
        print("Checking data consistency...")
        
        # Validate unscheduled data against scheduled entries
        for week_name in self.analyzer.week_analyses.keys():
            schedule_path = Path("schedules") / f"{week_name}_schedule.json"
            if schedule_path.exists():
                validation = self.analyzer.validate_against_schedule_entries(week_name, schedule_path)
                discrepancies = validation.get("discrepancies", [])
                
                if discrepancies:
                    self.regressions_detected.append({
                        "type": "Data Consistency",
                        "severity": "HIGH",
                        "week": week_name,
                        "count": len(discrepancies),
                        "description": f"Found {len(discrepancies)} data discrepancies in {week_name}",
                        "details": discrepancies
                    })
    
    def _generate_regression_report(self) -> Dict[str, Any]:
        """Generate comprehensive regression report."""
        report = {
            "timestamp": str(Path().cwd()),
            "summary": {
                "regressions_detected": len(self.regressions_detected),
                "high_severity": len([r for r in self.regressions_detected if r.get("severity") == "HIGH"]),
                "medium_severity": len([r for r in self.regressions_detected if r.get("severity") == "MEDIUM"]),
                "status": "FAILED" if self.regressions_detected else "PASSED"
            },
            "current_metrics": self.current_results,
            "baseline_metrics": self.baseline_results,
            "regressions": self.regressions_detected,
            "detailed_analysis": self.analyzer.get_detailed_miss_report(),
            "target_weeks": self.target_weeks
        }
        
        # Print summary
        print("\n" + "=" * 60)
        print("FIXED REGRESSION CHECK SUMMARY")
        print("=" * 60)
        
        if self.regressions_detected:
            print(f"REGRESSIONS DETECTED: {len(self.regressions_detected)}")
            print(f"   High Severity: {report['summary']['high_severity']}")
            print(f"   Medium Severity: {report['summary']['medium_severity']}")
            print("\nREGRESSION DETAILS:")
            for i, regression in enumerate(self.regressions_detected, 1):
                severity_emoji = "HIGH" if regression.get("severity") == "HIGH" else "MEDIUM"
                print(f"   {i}. {severity_emoji} {regression['type']}: {regression['description']}")
        else:
            print("NO REGRESSIONS DETECTED")
            print(f"   Top 5 Success Rate: {self.current_results.get('season_success_rate', 0):.1f}%")
            print(f"   Total Top 5 Misses: {self.current_results.get('total_counted_misses', 0)}")
        
        print("=" * 60)
        
        return report
    
    def _save_baseline(self):
        """Save current results as new baseline."""
        baseline_data = {
            "timestamp": str(Path().cwd()),
            "season_success_rate": self.current_results.get("season_success_rate", 0),
            "total_top5_slots": self.current_results.get("total_top5_slots", 0),
            "total_exempt_misses": self.current_results.get("total_exempt_misses", 0),
            "total_counted_misses": self.current_results.get("total_counted_misses", 0),
            "weeks_with_issues": self.current_results.get("weeks_with_issues", 0),
            "week_details": self.current_results.get("week_details", {}),
            "target_weeks": self.target_weeks
        }
        
        with open(self.baseline_file, 'w') as f:
            json.dump(baseline_data, f, indent=2)
    
    def get_top5_detailed_report(self) -> Dict[str, Any]:
        """Get detailed Top 5 analysis report."""
        return self.analyzer.get_detailed_miss_report()
    
    def set_baseline(self, force: bool = False):
        """
        Manually set current results as baseline.
        
        Args:
            force: Force overwrite existing baseline
        """
        if self.baseline_file.exists() and not force:
            print("Baseline already exists. Use force=True to overwrite.")
            return False
        
        if not self.current_results:
            print("No current results to set as baseline. Run check first.")
            return False
        
        self._save_baseline()
        print("Baseline updated successfully.")
        return True


def main():
    """Main entry point for fixed regression checker."""
    import argparse
    
    parser = argparse.ArgumentParser(description="FIXED Summer Camp Scheduler Regression Checker")
    parser.add_argument("--schedules-dir", default="schedules", help="Schedules directory")
    parser.add_argument("--set-baseline", action="store_true", help="Set current results as baseline")
    parser.add_argument("--force-baseline", action="store_true", help="Force overwrite baseline")
    parser.add_argument("--detailed", action="store_true", help="Show detailed Top 5 analysis")
    
    args = parser.parse_args()
    
    checker = FixedRegressionChecker()
    
    # Change to script directory
    script_dir = Path(__file__).resolve().parent
    os.chdir(script_dir)
    
    if args.set_baseline or args.force_baseline:
        # Run analysis first
        checker._analyze_target_weeks(args.schedules_dir)
        checker.current_results = checker.analyzer.get_season_summary()
        checker.set_baseline(force=args.force_baseline)
        return 0
    
    # Run full regression check
    report = checker.run_full_check(args.schedules_dir)
    
    # Show detailed report if requested
    if args.detailed:
        print("\nDETAILED TOP 5 ANALYSIS:")
        detailed = checker.get_top5_detailed_report()
        for week_name, week_data in detailed.items():
            print(f"\n--- {week_name} ---")
            print(f"Success Rate: {week_data['week_success_rate']:.1f}%")
            print(f"Counted Misses: {week_data['counted_misses']}")
            if week_data['missed_activities']:
                print("Missed Activities:")
                for miss in week_data['missed_activities']:
                    print(f"  - {miss['troop']}: {miss['activity']} (Top #{miss['rank']})")
                    if miss['placement_suggestions']:
                        suggestions = ', '.join(miss['placement_suggestions'][:2])
                        # Replace unicode characters with ASCII
                        suggestions = suggestions.replace('≤', '<=').replace('≥', '>=')
                        print(f"    Suggestions: {suggestions}")
    
    # Exit with error code if regressions detected
    return 1 if report["summary"]["regressions_detected"] > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
