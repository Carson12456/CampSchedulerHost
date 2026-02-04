#!/usr/bin/env python3
"""
Test script to apply advanced optimizations to existing schedules and measure score improvements.
"""

import sys
import os
sys.path.append('.')

from evaluate_week_success import evaluate_week
from constrained_scheduler import ConstrainedScheduler
from activities import get_all_activities
from io_handler import load_troops_from_json, load_schedule_from_json, save_schedule_to_json

def test_optimizations(week_file):
    """Test optimizations on a specific week."""
    print(f"\n{'='*60}")
    print(f"TESTING OPTIMIZATIONS FOR {week_file}")
    print(f"{'='*60}")
    
    # Load baseline
    print("Loading baseline schedule...")
    troops = load_troops_from_json(week_file)
    activities = get_all_activities()
    
    week_basename = os.path.splitext(os.path.basename(week_file))[0]
    schedule_file = os.path.join("schedules", f"{week_basename}_schedule.json")
    
    # Load existing schedule
    schedule = load_schedule_from_json(schedule_file, troops, activities)
    scheduler = ConstrainedScheduler(troops, activities)
    scheduler.schedule = schedule
    
    # Evaluate baseline
    baseline_metrics = evaluate_week(week_file)
    print(f"BASELINE: Score={baseline_metrics['final_score']}")
    print(f"  Excess Days: {baseline_metrics['excess_cluster_days']}")
    print(f"  Violations: {baseline_metrics['constraint_violations']}")
    print(f"  Missing Top 5: {baseline_metrics['missing_top5']}")
    print(f"  Staff Variance: {baseline_metrics['staff_variance']:.2f}")
    
    # Apply optimizations
    print(f"\n--- APPLYING ADVANCED OPTIMIZATIONS ---")
    
    # 1. Constraint violation reduction
    print("\n1. Reducing constraint violations...")
    violations_fixed = scheduler._reduce_constraint_violations()
    
    # 2. Staff variance optimization  
    print("\n2. Optimizing staff variance...")
    staff_optimizations = scheduler._optimize_staff_variance()
    
    # 3. Clustering consolidation
    print("\n3. Force clustering consolidation...")
    clustering_moves = scheduler._force_clustering_consolidation()
    
    # 4. Ultra-aggressive clustering
    print("\n4. Ultra-aggressive clustering...")
    ultra_moves = scheduler._ultra_aggressive_clustering()
    
    # 5. Final Top 5 recovery
    print("\n5. Final Top 5 recovery...")
    top5_recoveries = scheduler._recover_missing_top5()
    
    print(f"\n--- OPTIMIZATION SUMMARY ---")
    print(f"  Constraint violations fixed: {violations_fixed}")
    print(f"  Staff variance optimizations: {staff_optimizations}")
    print(f"  Clustering moves: {clustering_moves}")
    print(f"  Ultra-aggressive moves: {ultra_moves}")
    print(f"  Top 5 recoveries: {top5_recoveries}")
    
    # Save optimized schedule
    optimized_schedule_file = os.path.join("schedules", f"{week_basename}_optimized_schedule.json")
    save_schedule_to_json(schedule, troops, optimized_schedule_file)
    
    # Evaluate optimized version
    print(f"\n--- EVALUATING OPTIMIZED SCHEDULE ---")
    
    # Temporarily replace the schedule file for evaluation
    original_file = schedule_file
    backup_file = schedule_file + ".backup"
    
    # Backup original and use optimized
    if os.path.exists(original_file):
        os.rename(original_file, backup_file)
    os.rename(optimized_schedule_file, original_file)
    
    try:
        optimized_metrics = evaluate_week(week_file)
        print(f"OPTIMIZED: Score={optimized_metrics['final_score']}")
        print(f"  Excess Days: {optimized_metrics['excess_cluster_days']}")
        print(f"  Violations: {optimized_metrics['constraint_violations']}")
        print(f"  Missing Top 5: {optimized_metrics['missing_top5']}")
        print(f"  Staff Variance: {optimized_metrics['staff_variance']:.2f}")
        
        # Calculate improvement
        score_improvement = optimized_metrics['final_score'] - baseline_metrics['final_score']
        excess_improvement = baseline_metrics['excess_cluster_days'] - optimized_metrics['excess_cluster_days']
        violation_improvement = baseline_metrics['constraint_violations'] - optimized_metrics['constraint_violations']
        top5_improvement = baseline_metrics['missing_top5'] - optimized_metrics['missing_top5']
        variance_improvement = baseline_metrics['staff_variance'] - optimized_metrics['staff_variance']
        
        print(f"\n--- IMPROVEMENT SUMMARY ---")
        print(f"  Score Improvement: +{score_improvement}")
        print(f"  Excess Days Reduced: -{excess_improvement}")
        print(f"  Violations Fixed: -{violation_improvement}")
        print(f"  Top 5 Recovered: -{top5_improvement}")
        print(f"  Variance Improvement: {variance_improvement:.2f}")
        
        return {
            'week': week_file,
            'baseline_score': baseline_metrics['final_score'],
            'optimized_score': optimized_metrics['final_score'],
            'improvement': score_improvement,
            'excess_improvement': excess_improvement,
            'violation_improvement': violation_improvement,
            'top5_improvement': top5_improvement,
            'variance_improvement': variance_improvement
        }
        
    finally:
        # Restore original file
        if os.path.exists(original_file):
            os.remove(original_file)
        if os.path.exists(backup_file):
            os.rename(backup_file, original_file)

def main():
    """Test optimizations on low-scoring weeks."""
    low_scoring_weeks = [
        'tc_week3_troops.json',
        'tc_week5_troops.json', 
        'tc_week6_troops.json'
    ]
    
    results = []
    
    for week_file in low_scoring_weeks:
        try:
            result = test_optimizations(week_file)
            results.append(result)
        except Exception as e:
            print(f"ERROR processing {week_file}: {e}")
            import traceback
            traceback.print_exc()
    
    # Summary
    print(f"\n{'='*80}")
    print("OPTIMIZATION RESULTS SUMMARY")
    print(f"{'='*80}")
    
    total_improvement = 0
    for result in results:
        print(f"{result['week']}: {result['baseline_score']} -> {result['optimized_score']} (+{result['improvement']})")
        total_improvement += result['improvement']
    
    if results:
        avg_improvement = total_improvement / len(results)
        print(f"\nAverage improvement per week: +{avg_improvement:.1f}")
        print(f"Total improvement across all weeks: +{total_improvement}")

if __name__ == "__main__":
    main()
