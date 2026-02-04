#!/usr/bin/env python3
"""
Test Regression Checker Components - Comprehensive testing of each major grouping

This script tests each component of the enhanced regression checker to ensure
all Top 5 tracking and quality metrics are working properly.
"""

import json
import tempfile
import shutil
from pathlib import Path
from regression_checker import EnhancedRegressionChecker


class RegressionCheckerTester:
    """
    Comprehensive tester for regression checker components.
    """
    
    def __init__(self):
        self.test_results = {}
        self.backup_dir = None
        
    def setup_test_environment(self):
        """Create backup of current schedules for testing."""
        schedules_dir = Path("schedules")
        self.backup_dir = Path("test_backup_schedules")
        
        if self.backup_dir.exists():
            shutil.rmtree(self.backup_dir)
        
        shutil.copytree(schedules_dir, self.backup_dir)
        print(f"✅ Created backup of schedules in {self.backup_dir}")
    
    def restore_test_environment(self):
        """Restore original schedules after testing."""
        schedules_dir = Path("schedules")
        if self.backup_dir and self.backup_dir.exists():
            if schedules_dir.exists():
                shutil.rmtree(schedules_dir)
            shutil.copytree(self.backup_dir, schedules_dir)
            print(f"✅ Restored schedules from backup")
    
    def test_top5_tracking(self):
        """Test Top 5 satisfaction tracking."""
        print("\nTESTING: Top 5 Satisfaction Tracking")
        print("-" * 50)
        
        checker = EnhancedRegressionChecker()
        
        # Test 1: Normal Top 5 analysis
        try:
            checker._analyze_target_weeks("schedules")
            results = checker.analyzer.get_season_summary()
            
            success_rate = results.get("season_success_rate", 0)
            total_misses = results.get("total_counted_misses", 0)
            
            print(f"✅ Top 5 Success Rate: {success_rate:.1f}%")
            print(f"✅ Total Top 5 Misses: {total_misses}")
            print(f"✅ Weeks Analyzed: {len(checker.analyzer.week_analyses)}")
            
            # Verify we have data for all target weeks
            expected_weeks = len(checker.target_weeks)
            actual_weeks = len(checker.analyzer.week_analyses)
            
            if actual_weeks == expected_weeks:
                print(f"✅ All {expected_weeks} target weeks analyzed successfully")
                self.test_results["top5_tracking"] = "PASS"
            else:
                print(f"❌ Only {actual_weeks}/{expected_weeks} weeks analyzed")
                self.test_results["top5_tracking"] = "FAIL"
                
        except Exception as e:
            print(f"❌ Top 5 tracking failed: {e}")
            self.test_results["top5_tracking"] = "FAIL"
    
    def test_top5_regression_detection(self):
        """Test Top 5 regression detection."""
        print("\n🔍 TESTING: Top 5 Regression Detection")
        print("-" * 50)
        
        # Create a regression by adding a missed Top 5 activity
        schedule_file = Path("schedules/tc_week1_troops_schedule.json")
        
        try:
            # Load current schedule
            with open(schedule_file, 'r') as f:
                schedule_data = json.load(f)
            
            # Add a missed Top 5 activity to trigger regression
            original_top5 = schedule_data.get("unscheduled", {}).get("Tamanend", {}).get("top5", [])
            schedule_data["unscheduled"]["Tamanend"]["top5"] = ["Fishing"]  # Tamanend's #2 preference
            
            # Save modified schedule
            with open(schedule_file, 'w') as f:
                json.dump(schedule_data, f, indent=2)
            
            # Run regression check
            checker = EnhancedRegressionChecker()
            checker._analyze_target_weeks("schedules")
            checker.current_results = checker.analyzer.get_season_summary()
            
            # Load baseline for comparison
            if Path("baseline_metrics_10weeks.json").exists():
                with open("baseline_metrics_10weeks.json", 'r') as f:
                    checker.baseline_results = json.load(f)
            
            # Check for regression
            checker._check_top5_regressions()
            
            if checker.regressions_detected:
                top5_regressions = [r for r in checker.regressions_detected if "Top 5" in r["type"]]
                if top5_regressions:
                    print(f"✅ Detected {len(top5_regressions)} Top 5 regressions:")
                    for regression in top5_regressions:
                        print(f"   - {regression['description']}")
                    self.test_results["top5_regression_detection"] = "PASS"
                else:
                    print("❌ No Top 5 regressions detected (should have found one)")
                    self.test_results["top5_regression_detection"] = "FAIL"
            else:
                print("❌ No regressions detected at all")
                self.test_results["top5_regression_detection"] = "FAIL"
                
        except Exception as e:
            print(f"❌ Top 5 regression detection failed: {e}")
            self.test_results["top5_regression_detection"] = "FAIL"
        
        finally:
            # Restore original schedule
            self.restore_test_environment()
    
    def test_quality_metrics_calculation(self):
        """Test comprehensive quality metrics calculation."""
        print("\n🔍 TESTING: Quality Metrics Calculation")
        print("-" * 50)
        
        try:
            checker = EnhancedRegressionChecker()
            checker._analyze_target_weeks("schedules")
            checker.current_results = checker.analyzer.get_season_summary()
            
            # Add quality metrics
            checker._add_quality_metrics("schedules")
            
            if "quality_metrics" in checker.current_results:
                quality = checker.current_results["quality_metrics"]
                
                print(f"✅ Average Week Score: {quality.get('average_week_score', 0):.1f}")
                print(f"✅ Average Constraint Violations: {quality.get('average_constraint_violations', 0):.1f}")
                print(f"✅ Average Staff Variance: {quality.get('average_staff_variance', 0):.2f}")
                print(f"✅ Average Clustering Efficiency: {quality.get('average_clustering_efficiency', 0):.2f}")
                print(f"✅ Average Beach Slot Violations: {quality.get('average_beach_slot_violations', 0):.1f}")
                print(f"✅ Week Details Available: {len(quality.get('week_details', []))}")
                
                # Verify we have data for all weeks
                week_details = quality.get('week_details', [])
                if len(week_details) > 0:
                    print(f"✅ Quality metrics calculated for {len(week_details)} weeks")
                    self.test_results["quality_metrics"] = "PASS"
                else:
                    print("❌ No week details in quality metrics")
                    self.test_results["quality_metrics"] = "FAIL"
            else:
                print("❌ No quality_metrics found in results")
                self.test_results["quality_metrics"] = "FAIL"
                
        except Exception as e:
            print(f"❌ Quality metrics calculation failed: {e}")
            self.test_results["quality_metrics"] = "FAIL"
    
    def test_quality_regression_detection(self):
        """Test quality regression detection."""
        print("\n🔍 TESTING: Quality Regression Detection")
        print("-" * 50)
        
        try:
            checker = EnhancedRegressionChecker()
            checker._analyze_target_weeks("schedules")
            checker.current_results = checker.analyzer.get_season_summary()
            checker._add_quality_metrics("schedules")
            
            # Create a fake baseline with better metrics
            fake_baseline = {
                "quality_metrics": {
                    "average_week_score": 100.0,  # Much higher than current
                    "average_constraint_violations": 5.0,  # Lower than current
                    "average_staff_variance": 1.0,  # Lower than current
                    "average_beach_slot_violations": 0.0
                }
            }
            checker.baseline_results = fake_baseline
            
            # Check for regressions
            checker._check_quality_regressions()
            
            quality_regressions = [r for r in checker.regressions_detected 
                                 if r["type"] in ["Average Week Score", "Constraint Violations", 
                                               "Staff Balance", "Beach Slot Compliance"]]
            
            if len(quality_regressions) >= 2:  # Should detect multiple regressions
                print(f"✅ Detected {len(quality_regressions)} quality regressions:")
                for regression in quality_regressions:
                    print(f"   - {regression['severity']} {regression['type']}: {regression['description']}")
                self.test_results["quality_regression_detection"] = "PASS"
            else:
                print(f"❌ Only detected {len(quality_regressions)} quality regressions (expected >=2)")
                self.test_results["quality_regression_detection"] = "FAIL"
                
        except Exception as e:
            print(f"❌ Quality regression detection failed: {e}")
            self.test_results["quality_regression_detection"] = "FAIL"
    
    def test_detailed_analysis(self):
        """Test detailed Top 5 analysis reporting."""
        print("\n🔍 TESTING: Detailed Analysis Reporting")
        print("-" * 50)
        
        try:
            checker = EnhancedRegressionChecker()
            checker._analyze_target_weeks("schedules")
            
            detailed_report = checker.get_top5_detailed_report()
            
            if detailed_report:
                total_weeks = len(detailed_report)
                weeks_with_misses = len([w for w in detailed_report.values() if w.get('counted_misses', 0) > 0])
                total_misses = sum(w.get('counted_misses', 0) for w in detailed_report.values())
                
                print(f"✅ Detailed report generated for {total_weeks} weeks")
                print(f"✅ Weeks with misses: {weeks_with_misses}")
                print(f"✅ Total missed activities: {total_misses}")
                
                # Show sample of detailed analysis
                sample_week = list(detailed_report.keys())[0]
                sample_data = detailed_report[sample_week]
                print(f"✅ Sample analysis for {sample_week}:")
                print(f"   Success Rate: {sample_data.get('week_success_rate', 0):.1f}%")
                print(f"   Counted Misses: {sample_data.get('counted_misses', 0)}")
                
                self.test_results["detailed_analysis"] = "PASS"
            else:
                print("❌ No detailed report generated")
                self.test_results["detailed_analysis"] = "FAIL"
                
        except Exception as e:
            print(f"❌ Detailed analysis failed: {e}")
            self.test_results["detailed_analysis"] = "FAIL"
    
    def test_baseline_management(self):
        """Test baseline save/load functionality."""
        print("\n🔍 TESTING: Baseline Management")
        print("-" * 50)
        
        try:
            checker = EnhancedRegressionChecker()
            checker._analyze_target_weeks("schedules")
            checker.current_results = checker.analyzer.get_season_summary()
            
            # Test baseline saving
            test_baseline_file = Path("test_baseline.json")
            checker.baseline_file = test_baseline_file
            
            checker._save_baseline()
            
            if test_baseline_file.exists():
                print("✅ Baseline saved successfully")
                
                # Test baseline loading
                with open(test_baseline_file, 'r') as f:
                    saved_data = json.load(f)
                
                if "season_success_rate" in saved_data and "quality_metrics" in saved_data:
                    print("✅ Baseline contains required data")
                    print(f"   Top 5 Success Rate: {saved_data['season_success_rate']:.1f}%")
                    if saved_data['quality_metrics']:
                        print(f"   Quality Metrics: {len(saved_data['quality_metrics'])} fields")
                    
                    self.test_results["baseline_management"] = "PASS"
                else:
                    print("❌ Baseline missing required data")
                    self.test_results["baseline_management"] = "FAIL"
                
                # Cleanup
                test_baseline_file.unlink()
            else:
                print("❌ Baseline file not created")
                self.test_results["baseline_management"] = "FAIL"
                
        except Exception as e:
            print(f"❌ Baseline management failed: {e}")
            self.test_results["baseline_management"] = "FAIL"
    
    def run_all_tests(self):
        """Run all regression checker component tests."""
        print("COMPREHENSIVE REGRESSION CHECKER TESTING")
        print("=" * 60)
        
        # Setup test environment
        self.setup_test_environment()
        
        try:
            # Run all tests
            self.test_top5_tracking()
            self.test_top5_regression_detection()
            self.test_quality_metrics_calculation()
            self.test_quality_regression_detection()
            self.test_detailed_analysis()
            self.test_baseline_management()
            
            # Summary
            print("\n" + "=" * 60)
            print("🏁 TEST RESULTS SUMMARY")
            print("=" * 60)
            
            total_tests = len(self.test_results)
            passed_tests = len([r for r in self.test_results.values() if r == "PASS"])
            
            for test_name, result in self.test_results.items():
                status = "✅ PASS" if result == "PASS" else "❌ FAIL"
                print(f"{status} {test_name}")
            
            print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
            
            if passed_tests == total_tests:
                print("🎉 ALL TESTS PASSED - Regression Checker is working perfectly!")
            else:
                print("⚠️  Some tests failed - review the issues above")
                
        finally:
            # Cleanup
            self.restore_test_environment()
            if self.backup_dir and self.backup_dir.exists():
                shutil.rmtree(self.backup_dir)


def main():
    """Main entry point for regression checker testing."""
    tester = RegressionCheckerTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()
