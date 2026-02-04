#!/usr/bin/env python3
"""
Comprehensive regeneration script that regenerates all schedules with enhanced optimizations.
"""

import sys
import os
import time
import json
from datetime import datetime

sys.path.append('.')

from constrained_scheduler import ConstrainedScheduler
from activities import get_all_activities
from io_handler import load_troops_from_json, save_schedule_to_json
from evaluate_week_success import evaluate_week

def regenerate_all_schedules():
    """Regenerate all schedules with enhanced optimizations."""
    
    print("="*80)
    print("COMPREHENSIVE SCHEDULE REGENERATION WITH ENHANCED OPTIMIZATIONS")
    print("="*80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Find all troop files
    import glob
    troop_files = sorted(glob.glob("*_troops.json"))
    
    if not troop_files:
        print("No troop files found!")
        return
    
    print(f"Found {len(troop_files)} troop files to regenerate:")
    for file in troop_files:
        print(f"  - {file}")
    
    # Store results
    results = []
    total_start_time = time.time()
    
    for i, troop_file in enumerate(troop_files, 1):
        print(f"\n{'-'*60}")
        print(f"PROCESSING {i}/{len(troop_files)}: {troop_file}")
        print(f"{'-'*60}")
        
        week_start_time = time.time()
        
        try:
            # Load troops and activities
            troops = load_troops_from_json(troop_file)
            activities = get_all_activities()
            
            # Create scheduler with enhanced optimizations
            print(f"Creating scheduler for {len(troops)} troops...")
            scheduler = ConstrainedScheduler(troops, activities)
            
            # Determine if this is Voyageur mode
            voyageur_mode = "voyageur" in troop_file.lower()
            
            print(f"Regenerating schedule (Voyageur mode: {voyageur_mode})...")
            
            # Regenerate schedule
            schedule = scheduler.schedule_all()
            
            # Save schedule
            week_basename = os.path.splitext(os.path.basename(troop_file))[0]
            schedule_file = os.path.join("schedules", f"{week_basename}_schedule.json")
            save_schedule_to_json(schedule, troops, schedule_file)
            
            # Evaluate the regenerated schedule
            print("Evaluating regenerated schedule...")
            metrics = evaluate_week(troop_file)
            
            week_time = time.time() - week_start_time
            
            # Store results
            result = {
                'file': troop_file,
                'week_name': week_basename,
                'score': metrics['final_score'],
                'excess_cluster_days': metrics['excess_cluster_days'],
                'constraint_violations': metrics['constraint_violations'],
                'missing_top5': metrics['missing_top5'],
                'staff_variance': metrics['staff_variance'],
                'top5_success': metrics.get('top5_pct', 0),
                'cluster_efficiency': metrics.get('score_components', {}).get('cluster_efficiency_points', 0),
                'generation_time': week_time,
                'troops_count': len(troops),
                'total_entries': len(schedule.entries)
            }
            results.append(result)
            
            print(f"SUCCESS: {troop_file}")
            print(f"   Score: {metrics['final_score']}")
            print(f"   Top 5 Success: {metrics.get('top5_pct', 0):.1f}%")
            print(f"   Excess Cluster Days: {metrics['excess_cluster_days']}")
            print(f"   Constraint Violations: {metrics['constraint_violations']}")
            print(f"   Generation Time: {week_time:.1f}s")
            
        except Exception as e:
            print(f"ERROR: {troop_file}")
            print(f"   Error: {e}")
            import traceback
            traceback.print_exc()
            
            # Store error result
            result = {
                'file': troop_file,
                'week_name': os.path.splitext(os.path.basename(troop_file))[0],
                'error': str(e),
                'generation_time': time.time() - week_start_time
            }
            results.append(result)
    
    total_time = time.time() - total_start_time
    
    # Generate comprehensive report
    print(f"\n{'='*80}")
    print("REGENERATION COMPLETE - COMPREHENSIVE ANALYSIS")
    print("="*80)
    print(f"Total time: {total_time:.1f} seconds")
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Calculate statistics
    successful_results = [r for r in results if 'error' not in r]
    failed_results = [r for r in results if 'error' in r]
    
    if successful_results:
        scores = [r['score'] for r in successful_results]
        avg_score = sum(scores) / len(scores)
        max_score = max(scores)
        min_score = min(scores)
        
        total_top5_success = sum(r['top5_success'] for r in successful_results)
        avg_top5_success = total_top5_success / len(successful_results)
        
        total_excess_days = sum(r['excess_cluster_days'] for r in successful_results)
        total_violations = sum(r['constraint_violations'] for r in successful_results)
        total_missing_top5 = sum(r['missing_top5'] for r in successful_results)
        avg_variance = sum(r['staff_variance'] for r in successful_results) / len(successful_results)
        
        print(f"\nOVERALL STATISTICS:")
        print(f"   Successful Regenerations: {len(successful_results)}/{len(results)}")
        print(f"   Failed Regenerations: {len(failed_results)}")
        print(f"")
        print(f"   Average Score: {avg_score:.1f}")
        print(f"   Score Range: {min_score} - {max_score}")
        print(f"   Average Top 5 Success: {avg_top5_success:.1f}%")
        print(f"   Total Excess Cluster Days: {total_excess_days}")
        print(f"   Total Constraint Violations: {total_violations}")
        print(f"   Total Missing Top 5: {total_missing_top5}")
        print(f"   Average Staff Variance: {avg_variance:.2f}")
        
        # Detailed results table
        print(f"\nDETAILED RESULTS:")
        print(f"{'Week':<20} {'Score':<8} {'Top5%':<7} {'Excess':<7} {'Viol':<6} {'Miss5':<6} {'Var':<6} {'Time':<8}")
        print("-" * 80)
        
        for result in sorted(successful_results, key=lambda x: x['score'], reverse=True):
            print(f"{result['week_name']:<20} {result['score']:<8} "
                  f"{result['top5_success']:<7.1f} {result['excess_cluster_days']:<7} "
                  f"{result['constraint_violations']:<6} {result['missing_top5']:<6} "
                  f"{result['staff_variance']:<6.2f} {result['generation_time']:<8.1f}")
        
        # Save results to file
        results_file = "regeneration_results.json"
        with open(results_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'total_time': total_time,
                'statistics': {
                    'successful': len(successful_results),
                    'failed': len(failed_results),
                    'average_score': avg_score,
                    'max_score': max_score,
                    'min_score': min_score,
                    'average_top5_success': avg_top5_success,
                    'total_excess_cluster_days': total_excess_days,
                    'total_constraint_violations': total_violations,
                    'total_missing_top5': total_missing_top5,
                    'average_staff_variance': avg_variance
                },
                'results': results
            }, f, indent=2)
        
        print(f"\nResults saved to: {results_file}")
        
        # Performance analysis
        print(f"\nPERFORMANCE ANALYSIS:")
        best_weeks = sorted(successful_results, key=lambda x: x['score'], reverse=True)[:3]
        worst_weeks = sorted(successful_results, key=lambda x: x['score'])[:3]
        
        print(f"   Top 3 Performing Weeks:")
        for i, week in enumerate(best_weeks, 1):
            print(f"     {i}. {week['week_name']}: {week['score']} (Top5: {week['top5_success']:.1f}%)")
        
        print(f"   Bottom 3 Performing Weeks:")
        for i, week in enumerate(worst_weeks, 1):
            print(f"     {i}. {week['week_name']}: {week['score']} (Top5: {week['top5_success']:.1f}%)")
    
    if failed_results:
        print(f"\nFAILED REGENERATIONS:")
        for result in failed_results:
            print(f"   {result['file']}: {result['error']}")
    
    print(f"\nREGENERATION ANALYSIS COMPLETE")
    
    return results

if __name__ == "__main__":
    regenerate_all_schedules()
