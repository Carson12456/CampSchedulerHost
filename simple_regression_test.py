#!/usr/bin/env python3
"""
Simple Regression Checker Test - Test each major component
"""

import json
from pathlib import Path
from regression_checker import EnhancedRegressionChecker


def test_top5_tracking():
    """Test Top 5 satisfaction tracking."""
    print("\n=== TESTING: Top 5 Satisfaction Tracking ===")
    
    checker = EnhancedRegressionChecker()
    
    try:
        checker._analyze_target_weeks("schedules")
        results = checker.analyzer.get_season_summary()
        
        success_rate = results.get("season_success_rate", 0)
        total_misses = results.get("total_counted_misses", 0)
        
        print(f"Top 5 Success Rate: {success_rate:.1f}%")
        print(f"Total Top 5 Misses: {total_misses}")
        print(f"Weeks Analyzed: {len(checker.analyzer.week_analyses)}")
        
        # Verify we have data for all target weeks
        expected_weeks = len(checker.target_weeks)
        actual_weeks = len(checker.analyzer.week_analyses)
        
        if actual_weeks == expected_weeks:
            print(f"PASS: All {expected_weeks} target weeks analyzed successfully")
            return True
        else:
            print(f"FAIL: Only {actual_weeks}/{expected_weeks} weeks analyzed")
            return False
            
    except Exception as e:
        print(f"FAIL: Top 5 tracking failed: {e}")
        return False


def test_quality_metrics():
    """Test comprehensive quality metrics calculation."""
    print("\n=== TESTING: Quality Metrics Calculation ===")
    
    try:
        checker = EnhancedRegressionChecker()
        checker._analyze_target_weeks("schedules")
        checker.current_results = checker.analyzer.get_season_summary()
        
        # Add quality metrics
        checker._add_quality_metrics("schedules")
        
        if "quality_metrics" in checker.current_results:
            quality = checker.current_results["quality_metrics"]
            
            print(f"Average Week Score: {quality.get('average_week_score', 0):.1f}")
            print(f"Average Constraint Violations: {quality.get('average_constraint_violations', 0):.1f}")
            print(f"Average Staff Variance: {quality.get('average_staff_variance', 0):.2f}")
            print(f"Average Clustering Efficiency: {quality.get('average_clustering_efficiency', 0):.2f}")
            print(f"Average Beach Slot Violations: {quality.get('average_beach_slot_violations', 0):.1f}")
            
            # Verify we have data for all weeks
            week_details = quality.get('week_details', [])
            if len(week_details) > 0:
                print(f"PASS: Quality metrics calculated for {len(week_details)} weeks")
                return True
            else:
                print("FAIL: No week details in quality metrics")
                return False
        else:
            print("FAIL: No quality_metrics found in results")
            return False
            
    except Exception as e:
        print(f"FAIL: Quality metrics calculation failed: {e}")
        return False


def test_detailed_analysis():
    """Test detailed Top 5 analysis reporting."""
    print("\n=== TESTING: Detailed Analysis Reporting ===")
    
    try:
        checker = EnhancedRegressionChecker()
        checker._analyze_target_weeks("schedules")
        
        detailed_report = checker.get_top5_detailed_report()
        
        if detailed_report:
            total_weeks = len(detailed_report)
            weeks_with_misses = len([w for w in detailed_report.values() if w.get('counted_misses', 0) > 0])
            total_misses = sum(w.get('counted_misses', 0) for w in detailed_report.values())
            
            print(f"Detailed report generated for {total_weeks} weeks")
            print(f"Weeks with misses: {weeks_with_misses}")
            print(f"Total missed activities: {total_misses}")
            
            # Show sample of detailed analysis
            sample_week = list(detailed_report.keys())[0]
            sample_data = detailed_report[sample_week]
            print(f"Sample analysis for {sample_week}:")
            print(f"   Success Rate: {sample_data.get('week_success_rate', 0):.1f}%")
            print(f"   Counted Misses: {sample_data.get('counted_misses', 0)}")
            
            return True
        else:
            print("FAIL: No detailed report generated")
            return False
            
    except Exception as e:
        print(f"FAIL: Detailed analysis failed: {e}")
        return False


def test_regression_detection():
    """Test regression detection capabilities."""
    print("\n=== TESTING: Regression Detection ===")
    
    try:
        checker = EnhancedRegressionChecker()
        checker._analyze_target_weeks("schedules")
        checker.current_results = checker.analyzer.get_season_summary()
        checker._add_quality_metrics("schedules")
        
        # Create a fake baseline with better metrics to trigger regressions
        fake_baseline = {
            "season_success_rate": 100.0,  # Perfect Top 5
            "total_counted_misses": 0,
            "quality_metrics": {
                "average_week_score": 100.0,  # Much higher than current
                "average_constraint_violations": 5.0,  # Lower than current
                "average_staff_variance": 1.0,  # Lower than current
                "average_beach_slot_violations": 0.0
            }
        }
        checker.baseline_results = fake_baseline
        
        # Check for regressions
        checker._check_top5_regressions()
        checker._check_quality_regressions()
        
        if checker.regressions_detected:
            print(f"Detected {len(checker.regressions_detected)} regressions:")
            for regression in checker.regressions_detected:
                print(f"   - {regression['severity']} {regression['type']}: {regression['description']}")
            return True
        else:
            print("FAIL: No regressions detected (should have found some)")
            return False
            
    except Exception as e:
        print(f"FAIL: Regression detection failed: {e}")
        return False


def main():
    """Run all regression checker tests."""
    print("REGRESSION CHECKER COMPONENT TESTING")
    print("=" * 50)
    
    tests = [
        ("Top 5 Tracking", test_top5_tracking),
        ("Quality Metrics", test_quality_metrics),
        ("Detailed Analysis", test_detailed_analysis),
        ("Regression Detection", test_regression_detection),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        results[test_name] = test_func()
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST RESULTS SUMMARY")
    print("=" * 50)
    
    total_tests = len(results)
    passed_tests = len([r for r in results.values() if r])
    
    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("ALL TESTS PASSED - Regression Checker is working perfectly!")
    else:
        print("Some tests failed - review the issues above")


if __name__ == "__main__":
    main()
