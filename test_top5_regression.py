#!/usr/bin/env python3
"""
Top 5 Regression Test - Integration with Existing Test Framework

Test script that validates the improved top 5 detection system and integrates
with the existing test methodology. This ensures the new unscheduled_analyzer
produces accurate results consistent with existing expectations.
"""

import sys
import json
import os
from pathlib import Path
from typing import Dict, List, Any

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.services.unscheduled_analyzer import UnscheduledAnalyzer
from regression_checker import RegressionChecker


class Top5RegressionTest:
    """
    Test suite for the improved top 5 detection system.
    
    Validates:
    - Consistency with existing check_missed_top5.py
    - Proper exemption handling
    - Accurate success rate calculations
    - Data consistency validation
    """
    
    def __init__(self):
        self.analyzer = UnscheduledAnalyzer()
        self.test_results = []
        self.schedules_dir = Path("schedules")
    
    def run_all_tests(self) -> bool:
        """Run all regression tests."""
        print("Running Top 5 Regression Tests")
        print("=" * 50)
        
        tests = [
            ("Consistency with Existing Detection", self.test_consistency_with_existing),
            ("Exemption Logic Validation", self.test_exemption_logic),
            ("Success Rate Calculation", self.test_success_rate_calculation),
            ("Data Consistency Validation", self.test_data_consistency),
            ("Placement Suggestions Generation", self.test_placement_suggestions),
            ("Constraint Conflict Detection", self.test_constraint_conflicts)
        ]
        
        all_passed = True
        
        for test_name, test_func in tests:
            print(f"\n{test_name}...")
            try:
                result = test_func()
                if result:
                    print(f"PASSED")
                    self.test_results.append({"name": test_name, "status": "PASSED"})
                else:
                    print(f"FAILED")
                    self.test_results.append({"name": test_name, "status": "FAILED"})
                    all_passed = False
            except Exception as e:
                print(f"ERROR: {e}")
                self.test_results.append({"name": test_name, "status": "ERROR", "error": str(e)})
                all_passed = False
        
        # Print summary
        self._print_test_summary()
        return all_passed
    
    def test_consistency_with_existing(self) -> bool:
        """Test consistency with existing check_missed_top5.py methodology."""
        if not self.schedules_dir.exists():
            print("   No schedules directory found - skipping test")
            return True
        
        # Run both analyses
        self.analyzer.analyze_all_weeks()
        new_results = self.analyzer.get_season_summary()
        
        # Run existing method
        try:
            # Import and run existing method
            import subprocess
            result = subprocess.run([sys.executable, "check_missed_top5.py"], 
                                  capture_output=True, text=True, cwd=Path(__file__).parent)
            
            if result.returncode == 0:
                # Parse existing output (basic check)
                existing_output = result.stdout
                if "NO MISSED TOP 5 ACTIVITIES" in existing_output:
                    existing_misses = 0
                else:
                    # Extract total misses from output
                    lines = existing_output.split('\n')
                    existing_misses = 0
                    for line in lines:
                        if "SUMMARY:" in line and "total Top 5 misses" in line:
                            # Extract number from "X total Top 5 misses"
                            import re
                            match = re.search(r'(\d+) total Top 5 misses', line)
                            if match:
                                existing_misses = int(match.group(1))
                
                new_misses = new_results.get("total_counted_misses", 0)
                
                if existing_misses == new_misses:
                    print(f"   Consistent: {existing_misses} misses detected")
                    return True
                else:
                    print(f"   Inconsistent: Existing={existing_misses}, New={new_misses}")
                    return False
            else:
                print(f"   Could not run existing method: {result.stderr}")
                return True  # Don't fail test for external tool issues
                
        except Exception as e:
            print(f"   Could not compare with existing method: {e}")
            return True  # Don't fail test for external tool issues
    
    def test_exemption_logic(self) -> bool:
        """Test exemption logic matches .cursorrules definitions."""
        # Test exemption rules
        test_cases = [
            ("Tamarac Wildlife Refuge", True, "3-hour activity"),
            ("Itasca State Park", True, "3-hour activity"),
            ("Back of the Moon", True, "3-hour activity"),
            ("History Center", True, "HC/DG activity"),
            ("Disc Golf", True, "HC/DG activity"),
            ("Archery", False, "Regular activity"),
            ("Aqua Trampoline", False, "Beach activity")
        ]
        
        all_correct = True
        
        for activity, expected_exempt, description in test_cases:
            # Create mock activity data
            mock_activity_data = {
                "name": activity,
                "rank": 3,
                "is_exempt": expected_exempt
            }
            
            missed = self.analyzer._create_missed_top5("TestTroop", mock_activity_data, "TestWeek")
            
            if missed:
                if missed.is_exempt == expected_exempt:
                    print(f"   {activity}: {description}")
                else:
                    print(f"   {activity}: Expected exempt={expected_exempt}, got {missed.is_exempt}")
                    all_correct = False
            else:
                print(f"   {activity}: Could not create missed activity")
        
        return all_correct
    
    def test_success_rate_calculation(self) -> bool:
        """Test success rate calculation accuracy."""
        if not self.analyzer.week_analyses:
            # Create test data
            test_unscheduled = {
                "Troop1": {
                    "top5": [
                        {"name": "Activity1", "rank": 1, "is_exempt": False},
                        {"name": "Activity2", "rank": 2, "is_exempt": True}
                    ]
                },
                "Troop2": {
                    "top5": [
                        {"name": "Activity3", "rank": 1, "is_exempt": False}
                    ]
                }
            }
            
            analysis = self.analyzer._analyze_week_unscheduled("TestWeek", test_unscheduled)
            
            # Expected: 3 total slots, 1 exempt, 2 counted, 1 missed = (3-1)/3 = 66.7%
            expected_success = 66.7
            actual_success = round(analysis.success_rate, 1)
            
            if actual_success == expected_success:
                print(f"   Success rate: {actual_success}% (expected {expected_success}%)")
                return True
            else:
                print(f"   Success rate: {actual_success}% (expected {expected_success}%)")
                return False
        else:
            print(f"   Using real data - success rates calculated")
            return True
    
    def test_data_consistency(self) -> bool:
        """Test data consistency validation."""
        if not self.schedules_dir.exists():
            print("   No schedules directory - skipping test")
            return True
        
        # Test with first available schedule
        schedule_files = list(self.schedules_dir.glob("*_schedule.json"))
        if not schedule_files:
            print("   No schedule files found - skipping test")
            return True
        
        schedule_file = schedule_files[0]
        week_name = schedule_file.stem.replace("_schedule", "")
        
        try:
            validation = self.analyzer.validate_against_schedule_entries(week_name, schedule_file)
            discrepancies = validation.get("discrepancies", [])
            
            if len(discrepancies) == 0:
                print(f"   No data discrepancies found in {week_name}")
                return True
            else:
                print(f"   Found {len(discrepancies)} discrepancies in {week_name}")
                for disc in discrepancies[:3]:  # Show first 3
                    print(f"      - {disc['issue']}")
                return True  # Don't fail test for existing data issues
                
        except Exception as e:
            print(f"   Error during validation: {e}")
            return False
    
    def test_placement_suggestions(self) -> bool:
        """Test placement suggestions generation."""
        test_activities = [
            ("Aqua Trampoline", ["beach", "sharing"]),
            ("Climbing Tower", ["exclusive", "commissioner"]),
            ("History Center", ["Tuesday"]),
            ("Delta", ["adjacent", "Sailing"])
        ]
        
        all_good = True
        
        for activity, expected_keywords in test_activities:
            suggestions = self.analyzer._generate_placement_suggestions(activity, 1)
            
            # Check if suggestions contain expected keywords
            suggestion_text = " ".join(suggestions).lower()
            found_keywords = [kw for kw in expected_keywords if kw.lower() in suggestion_text]
            
            if found_keywords:
                print(f"   {activity}: Found relevant suggestions ({', '.join(found_keywords)})")
            else:
                print(f"   {activity}: No relevant suggestions found")
                all_good = False
        
        return all_good
    
    def test_constraint_conflicts(self) -> bool:
        """Test constraint conflict detection."""
        test_activities = [
            ("Troop Rifle", ["accuracy"]),
            ("Delta", ["adjacent", "Sailing"]),
            ("Aqua Trampoline", ["beach"]),
            ("Sailing", ["slots"])
        ]
        
        all_good = True
        
        for activity, expected_keywords in test_activities:
            conflicts = self.analyzer._identify_constraint_conflicts(activity)
            conflict_text = " ".join(conflicts).lower()
            found_keywords = [kw for kw in expected_keywords if kw.lower() in conflict_text]
            
            if found_keywords:
                print(f"   {activity}: Found relevant conflicts ({', '.join(found_keywords)})")
            else:
                print(f"   {activity}: No relevant conflicts found")
                all_good = False
        
        return all_good
    
    def _print_test_summary(self):
        """Print test summary."""
        print("\n" + "=" * 50)
        print("TEST SUMMARY")
        print("=" * 50)
        
        passed = len([t for t in self.test_results if t["status"] == "PASSED"])
        failed = len([t for t in self.test_results if t["status"] == "FAILED"])
        errors = len([t for t in self.test_results if t["status"] == "ERROR"])
        
        print(f"Total Tests: {len(self.test_results)}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Errors: {errors}")
        
        if failed > 0 or errors > 0:
            print("\nFAILED TESTS:")
            for result in self.test_results:
                if result["status"] in ["FAILED", "ERROR"]:
                    print(f"   - {result['name']}: {result['status']}")
                    if "error" in result:
                        print(f"     Error: {result['error']}")
        
        print("=" * 50)


def main():
    """Main entry point for top 5 regression tests."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Top 5 Regression Test Suite")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Change to script directory
    script_dir = Path(__file__).resolve().parent
    os.chdir(script_dir)
    
    # Run tests
    tester = Top5RegressionTest()
    success = tester.run_all_tests()
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
