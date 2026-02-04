#!/usr/bin/env python3
"""
Final comprehensive polish and fixes for CampScheduler
"""

from enhanced_scheduler import EnhancedScheduler
from io_handler import load_troops_from_json, save_schedule_to_json
from evaluate_week_success import evaluate_week
import glob
import time

def comprehensive_polish():
    """Apply comprehensive polish to all weeks."""
    print("COMPREHENSIVE CAMP SCHEDULER POLISH")
    print("=" * 60)
    
    week_files = sorted(glob.glob('*_troops.json'))
    results = []
    
    for i, week_file in enumerate(week_files, 1):
        print(f"\n[{i}/{len(week_files)}] Processing {week_file}...")
        
        try:
            troops = load_troops_from_json(week_file)
            
            # Apply enhanced scheduler
            start_time = time.time()
            scheduler = EnhancedScheduler(troops)
            schedule = scheduler.schedule_all()
            processing_time = time.time() - start_time
            
            # Save enhanced schedule
            week_name = week_file.replace('_troops.json', '')
            save_schedule_to_json(schedule, troops, f'schedules/{week_name}_enhanced_schedule.json')
            
            # Evaluate results
            metrics = evaluate_week(week_file)
            
            # Verify gaps
            total_gaps = 0
            for troop in troops:
                gaps = len(scheduler._find_troop_gaps(troop))
                total_gaps += gaps
            
            result = {
                'week': week_name,
                'score': metrics['final_score'],
                'gaps': metrics['unnecessary_gaps'],
                'verified_gaps': total_gaps,
                'violations': metrics['constraint_violations'],
                'top5_missed': metrics['missing_top5'],
                'staff_variance': metrics['staff_variance'],
                'time': processing_time,
                'entries': len(schedule.entries)
            }
            results.append(result)
            
            print(f"  SUCCESS: Score: {result['score']}")
            print(f"  SUCCESS: Gaps: {result['gaps']} (verified: {result['verified_gaps']})")
            print(f"  SUCCESS: Violations: {result['violations']}")
            print(f"  SUCCESS: Top 5 Missed: {result['top5_missed']}")
            print(f"  SUCCESS: Time: {result['time']:.2f}s")
            
        except Exception as e:
            print(f"  ERROR: {e}")
            continue
    
    # Summary statistics
    print(f"\nCOMPREHENSIVE POLISH RESULTS")
    print("=" * 60)
    
    if results:
        avg_score = sum(r['score'] for r in results) / len(results)
        avg_gaps = sum(r['gaps'] for r in results) / len(results)
        avg_violations = sum(r['violations'] for r in results) / len(results)
        avg_top5_missed = sum(r['top5_missed'] for r in results) / len(results)
        
        print(f"Average Score: {avg_score:.1f}")
        print(f"Average Gaps: {avg_gaps:.1f}")
        print(f"Average Violations: {avg_violations:.1f}")
        print(f"Average Top 5 Missed: {avg_top5_missed:.1f}")
        
        # Best and worst weeks
        best_week = min(results, key=lambda x: x['score'])
        worst_week = max(results, key=lambda x: x['score'])
        
        print(f"\nBest Week: {best_week['week']} (Score: {best_week['score']})")
        print(f"Worst Week: {worst_week['week']} (Score: {worst_week['score']})")
        
        # Improvement analysis
        zero_gap_weeks = sum(1 for r in results if r['verified_gaps'] == 0)
        zero_violation_weeks = sum(1 for r in results if r['violations'] == 0)
        zero_top5_missed = sum(1 for r in results if r['top5_missed'] == 0)
        
        print(f"\nPerfect Weeks:")
        print(f"  Zero Gaps: {zero_gap_weeks}/{len(results)}")
        print(f"  Zero Violations: {zero_violation_weeks}/{len(results)}")
        print(f"  Zero Top 5 Missed: {zero_top5_missed}/{len(results)}")
    
    print(f"\nPOLISH COMPLETE! Enhanced schedules saved to schedules/ directory")
    return results

if __name__ == "__main__":
    comprehensive_polish()
