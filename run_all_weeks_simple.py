#!/usr/bin/env python3
"""Run scheduler on all available weeks (1-8) and evaluate metrics"""

from constrained_scheduler import ConstrainedScheduler
from io_handler import load_troops_from_json, save_schedule_to_json
from activities import get_all_activities
import json
from datetime import datetime

def run_all_weeks():
    """Run scheduler on all available weeks"""
    
    print("=" * 80)
    print("SUMMER CAMP SCHEDULER - ALL WEEKS SCHEDULING")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Load all available weeks
    weeks = []
    for i in range(1, 9):
        try:
            troops = load_troops_from_json(f'tc_week{i}_troops.json')
            weeks.append((i, troops))
            print(f'Loaded Week {i}: {len(troops)} troops')
        except FileNotFoundError:
            print(f'Week {i} data not found - skipping')
    
    if not weeks:
        print('No week data found!')
        return
    
    print(f'\nProcessing {len(weeks)} weeks...')
    
    # Run scheduler on all weeks
    results = []
    activities = get_all_activities()
    
    for week_num, troops in weeks:
        print(f'\n=== SCHEDULING WEEK {week_num} ===')
        
        # Schedule
        scheduler = ConstrainedScheduler(troops, activities)
        schedule = scheduler.schedule_all()
        
        # Get statistics
        stats = scheduler.get_stats()
        
        # Save schedule
        save_schedule_to_json(schedule, troops, f'schedules/week{week_num}_schedule.json')
        
        # Collect results
        week_results = {
            'week': week_num,
            'troops': len(troops),
            'stats': stats,
            'violations': scheduler._count_current_violations()
        }
        
        results.append(week_results)
        
        # Basic metrics
        total_top5 = sum(stats['troops'][t]['top5_achieved'] for t in stats['troops'])
        total_possible = len(troops) * 5
        top5_rate = (total_top5 / total_possible * 100) if total_possible > 0 else 0
        
        total_reflection = sum(1 for t in stats['troops'] if stats['troops'][t]['has_reflection'])
        reflection_rate = (total_reflection / len(troops) * 100) if troops else 0
        
        print(f'Week {week_num}: {len(troops)} troops')
        print(f'  Top 5: {total_top5}/{total_possible} ({top5_rate:.1f}%)')
        print(f'  Friday Reflection: {total_reflection}/{len(troops)} ({reflection_rate:.1f}%)')
        print(f'  Violations: {week_results["violations"]}')
    
    print(f'\n=== ALL WEEKS COMPLETE ===')
    print(f'Scheduled {len(results)} weeks')
    
    # Calculate overall metrics
    total_troops = sum(r['troops'] for r in results)
    total_top5_achieved = 0
    total_top5_possible = 0
    total_reflection = 0
    total_violations = 0
    
    for result in results:
        for troop_name, stats in result['stats']['troops'].items():
            total_top5_possible += 5
            total_top5_achieved += stats['top5_achieved']
            if stats['has_reflection']:
                total_reflection += 1
        total_violations += result['violations']
    
    top5_satisfaction = (total_top5_achieved / total_top5_possible * 100) if total_top5_possible > 0 else 0
    reflection_compliance = (total_reflection / total_troops * 100) if total_troops > 0 else 0
    
    print(f'\n=== OVERALL METRICS ===')
    print(f'Total Troops: {total_troops}')
    print(f'Top 5 Satisfaction: {total_top5_achieved}/{total_top5_possible} ({top5_satisfaction:.1f}%)')
    print(f'Friday Reflection: {total_reflection}/{total_troops} ({reflection_compliance:.1f}%)')
    print(f'Total Violations: {total_violations}')
    
    # Save comprehensive results
    comprehensive_results = {
        'timestamp': datetime.now().isoformat(),
        'total_weeks': len(results),
        'total_troops': total_troops,
        'overall_metrics': {
            'top5_satisfaction': top5_satisfaction,
            'reflection_compliance': reflection_compliance,
            'total_violations': total_violations
        },
        'weekly_results': results
    }
    
    with open('all_weeks_results.json', 'w') as f:
        json.dump(comprehensive_results, f, indent=2)
    
    print(f'\nResults saved to all_weeks_results.json')
    
    return comprehensive_results

if __name__ == "__main__":
    results = run_all_weeks()
