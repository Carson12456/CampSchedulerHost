#!/usr/bin/env python3
"""
ENHANCED Regression Checker - Automated Testing for Every Code Change

This version ONLY analyzes the 10 actual week files, not all variants.
Uses the authoritative unscheduled_analyzer.py service for top 5 detection.
Now includes comprehensive schedule quality metrics from evaluate_week_success.py.
"""

import sys
import json
import os
from pathlib import Path
from typing import Dict, List, Any
# Add parent directory to path to allow importing from core and utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.services.unscheduled_analyzer import UnscheduledAnalyzer

# Import comprehensive evaluation
try:
    from utils.evaluate_week_success import evaluate_week, DEFAULT_WEIGHTS
except ImportError:
    print("Warning: evaluate_week_success not available, using limited metrics")
    evaluate_week = None
    DEFAULT_WEIGHTS = None


class EnhancedRegressionChecker:
    """
    ENHANCED Automated regression checker for Summer Camp Scheduler.
    
    This version analyzes the 10 actual week files with comprehensive metrics:
    - Top 5 satisfaction (original)
    - Average week quality scores (NEW)
    - Constraint violations (NEW)
    - Staff efficiency (NEW)
    - Clustering quality (NEW)
    - Beach slot compliance (NEW)
    
    Target files:
    - tc_week1_troops through tc_week8_troops
    - voyageur_week1_troops, voyageur_week3_troops
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
    
    def run_full_check(self, schedules_dir: str = "data/schedules") -> Dict[str, Any]:
        """
        Run comprehensive regression check on 10 actual weeks only.
        
        Args:
            schedules_dir: Directory containing schedule JSON files
            
        Returns:
            Complete regression report with comprehensive metrics
        """
        print("ENHANCED Regression Checker - Analyzing 10 Actual Weeks")
        print("=" * 60)
        
        # Analyze current state for target weeks only
        print("Analyzing current schedules...")
        self._analyze_target_weeks(schedules_dir)
        self.current_results = self.analyzer.get_season_summary()
        
        # Add comprehensive quality metrics
        if evaluate_week:
            print("Calculating comprehensive quality metrics...")
            self._add_quality_metrics(schedules_dir)
        
        # Load baseline if exists
        if self.baseline_file.exists():
            print("Loading baseline metrics...")
            with open(self.baseline_file, 'r') as f:
                self.baseline_results = json.load(f)
        
        # Check for regressions
        print("Checking for regressions...")
        self._check_top5_regressions()
        self._check_quality_regressions()
        self._check_multislot_activities(schedules_dir)
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
    
    def _add_quality_metrics(self, schedules_dir: str):
        """Add comprehensive quality metrics using evaluate_week_success."""
        schedules_path = Path(schedules_dir)
        quality_metrics = []
        
        for week_name in self.target_weeks:
            # Find the corresponding troop file
            troop_file = schedules_path.parent / f"{week_name}.json"
            if troop_file.exists():
                try:
                    # Evaluate the week
                    week_result = evaluate_week(str(troop_file))
                    
                    if week_result:
                        quality_metrics.append({
                            "week_name": week_name,
                            "total_score": week_result.get("total_score", 0),
                            "preference_score": week_result.get("preference_score", 0),
                            "constraint_violations": week_result.get("constraint_violations", 0),
                            "staff_variance": week_result.get("staff_variance", 0),
                            "clustering_efficiency": week_result.get("clustering_efficiency", 0),
                            "beach_slot_2_violations": week_result.get("beach_slot_2_violations", 0),
                            "unnecessary_gaps": week_result.get("unnecessary_gaps", 0),
                            "grade": week_result.get("grade", "Unknown")
                        })
                except Exception as e:
                    print(f"  Warning: Could not evaluate {week_name}: {e}")
        
        # Calculate averages
        if quality_metrics:
            avg_score = sum(m["total_score"] for m in quality_metrics) / len(quality_metrics)
            avg_violations = sum(m["constraint_violations"] for m in quality_metrics) / len(quality_metrics)
            avg_staff_variance = sum(m["staff_variance"] for m in quality_metrics) / len(quality_metrics)
            avg_clustering = sum(m["clustering_efficiency"] for m in quality_metrics) / len(quality_metrics)
            avg_beach_violations = sum(m["beach_slot_2_violations"] for m in quality_metrics) / len(quality_metrics)
            
            self.current_results.update({
                "quality_metrics": {
                    "average_week_score": avg_score,
                    "average_constraint_violations": avg_violations,
                    "average_staff_variance": avg_staff_variance,
                    "average_clustering_efficiency": avg_clustering,
                    "average_beach_slot_violations": avg_beach_violations,
                    "week_details": quality_metrics
                }
            })
            
            print(f"  Average Week Score: {avg_score:.1f}")
            print(f"  Average Constraint Violations: {avg_violations:.1f}")
            print(f"  Average Staff Variance: {avg_staff_variance:.2f}")
            print(f"  Average Clustering Efficiency: {avg_clustering:.2f}")
            print(f"  Average Beach Slot Violations: {avg_beach_violations:.1f}")
    
    def _check_quality_regressions(self):
        """Check for schedule quality regressions."""
        if not self.baseline_results or "quality_metrics" not in self.current_results:
            print("No quality baseline found - will create new baseline")
            return
        
        current_quality = self.current_results["quality_metrics"]
        baseline_quality = self.baseline_results.get("quality_metrics", {})
        
        # Check for significant drop in average week score
        current_score = current_quality.get("average_week_score", 0)
        baseline_score = baseline_quality.get("average_week_score", 0)
        
        if current_score < baseline_score - 5.0:  # 5 point tolerance
            self.regressions_detected.append({
                "type": "Average Week Score",
                "severity": "HIGH",
                "current": current_score,
                "baseline": baseline_score,
                "change": current_score - baseline_score,
                "description": f"Average week score dropped from {baseline_score:.1f} to {current_score:.1f}"
            })
        
        # Check for increase in constraint violations
        current_violations = current_quality.get("average_constraint_violations", 0)
        baseline_violations = baseline_quality.get("average_constraint_violations", 0)
        
        if current_violations > baseline_violations + 0.5:  # 0.5 violation tolerance
            self.regressions_detected.append({
                "type": "Constraint Violations",
                "severity": "HIGH",
                "current": current_violations,
                "baseline": baseline_violations,
                "change": current_violations - baseline_violations,
                "description": f"Constraint violations increased from {baseline_violations:.1f} to {current_violations:.1f}"
            })
        
        # Check for beach slot compliance regression
        current_beach = current_quality.get("average_beach_slot_violations", 0)
        baseline_beach = baseline_quality.get("average_beach_slot_violations", 0)
        
        if current_beach > baseline_beach + 0.5:  # 0.5 violation tolerance
            self.regressions_detected.append({
                "type": "Beach Slot Compliance",
                "severity": "MEDIUM",
                "current": current_beach,
                "baseline": baseline_beach,
                "change": current_beach - baseline_beach,
                "description": f"Beach slot violations increased from {baseline_beach:.1f} to {current_beach:.1f}"
            })
        
        # Check for staff efficiency regression
        current_staff = current_quality.get("average_staff_variance", 0)
        baseline_staff = baseline_quality.get("average_staff_variance", 0)
        
        if current_staff > baseline_staff + 0.2:  # 0.2 variance tolerance
            self.regressions_detected.append({
                "type": "Staff Balance",
                "severity": "MEDIUM",
                "current": current_staff,
                "baseline": baseline_staff,
                "change": current_staff - baseline_staff,
                "description": f"Staff variance increased from {baseline_staff:.2f} to {current_staff:.2f}"
            })
    
    def _check_multislot_activities(self, schedules_dir: str):
        """Check that multi-slot activities have the correct number of slots scheduled."""
        print("Checking multi-slot activities...")
        
        # Activities that should span multiple slots
        # 3 slots: Tamarac Wildlife Refuge, Itasca State Park, Back of the Moon
        # 2 slots: Sailing, Canoe Snorkel, Float for Floats
        THREE_HR = ['Tamarac Wildlife Refuge', 'Itasca State Park', 'Back of the Moon']
        TWO_HR = ['Sailing', 'Canoe Snorkel', 'Float for Floats']
        
        schedules_path = Path(schedules_dir)
        total_issues = 0
        weeks_with_issues = []
        
        for week_name in self.target_weeks:
            schedule_file = schedules_path / f"{week_name}_schedule.json"
            if not schedule_file.exists():
                continue
            
            try:
                with open(schedule_file) as f:
                    data = json.load(f)
            except Exception:
                continue
            
            # Group entries by troop and activity
            troop_activities = {}
            for entry in data.get('entries', []):
                key = (entry['troop_name'], entry['activity_name'])
                if key not in troop_activities:
                    troop_activities[key] = []
                troop_activities[key].append((entry['day'], entry['slot']))
            
            # Check multi-slot activities
            week_issues = 0
            for (troop, activity), slots in troop_activities.items():
                if activity in THREE_HR:
                    expected_slots = 3
                elif activity in TWO_HR:
                    expected_slots = 2
                else:
                    continue
                
                if len(slots) != expected_slots:
                    week_issues += 1
                    total_issues += 1
            
            if week_issues > 0:
                weeks_with_issues.append(week_name)
        
        if total_issues > 0:
            self.regressions_detected.append({
                "type": "Multi-Slot Activities",
                "severity": "HIGH",
                "current": total_issues,
                "baseline": 0,
                "change": total_issues,
                "description": f"Found {total_issues} multi-slot activity issues across {len(weeks_with_issues)} weeks",
                "details": weeks_with_issues
            })
    
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
        print("ENHANCED REGRESSION CHECK SUMMARY")
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
            
            # Show quality metrics if available
            if "quality_metrics" in self.current_results:
                quality = self.current_results["quality_metrics"]
                print(f"   Average Week Score: {quality.get('average_week_score', 0):.1f}")
                print(f"   Average Constraint Violations: {quality.get('average_constraint_violations', 0):.1f}")
                print(f"   Average Beach Slot Violations: {quality.get('average_beach_slot_violations', 0):.1f}")
                print(f"   Average Staff Variance: {quality.get('average_staff_variance', 0):.2f}")
        
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
    """Main entry point for enhanced regression checker."""
    import argparse
    
    parser = argparse.ArgumentParser(description="ENHANCED Summer Camp Scheduler Regression Checker")
    parser.add_argument("--schedules-dir", default="data/schedules", help="Schedules directory")
    parser.add_argument("--set-baseline", action="store_true", help="Set current results as baseline")
    parser.add_argument("--force-baseline", action="store_true", help="Force overwrite baseline")
    parser.add_argument("--detailed", action="store_true", help="Show detailed Top 5 analysis")
    
    args = parser.parse_args()
    
    checker = EnhancedRegressionChecker()
    
    # Use absolute path from script directory parent
    project_root = Path(__file__).resolve().parent.parent
    schedules_dir = project_root / args.schedules_dir
    
    if args.set_baseline or args.force_baseline:
        # Run analysis first
        checker._analyze_target_weeks(str(schedules_dir))
        checker.current_results = checker.analyzer.get_season_summary()
        if evaluate_week:
            checker._add_quality_metrics(str(schedules_dir))
        checker.set_baseline(force=args.force_baseline)
        return 0
    
    # Run full regression check
    report = checker.run_full_check(str(schedules_dir))
    
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
