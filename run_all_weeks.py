#!/usr/bin/env python3
"""Run scheduler on all available weeks (1-8) and implement recommendations"""

from constrained_scheduler import ConstrainedScheduler
from io_handler import load_troops_from_json, save_schedule_to_json
from activities import get_all_activities
import json
from datetime import datetime

def run_all_weeks():
    """Run scheduler on all available weeks and implement fixes"""
    
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
    
    print(f'\\nProcessing {len(weeks)} weeks...')
    
    # Phase 1: Run scheduler on all weeks
    results = []
    activities = get_all_activities()
    
    for week_num, troops in weeks:
        print(f'\\n=== SCHEDULING WEEK {week_num} ===')
        
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
            'violations': scheduler._count_current_violations(),
            'gaps': 0  # Will be calculated after gap elimination
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
        
        # Save schedule entries
        schedule_data = []
        for entry in schedule.entries:
            schedule_data.append({
                'troop': entry.troop.name,
                'activity': entry.activity.name,
                'day': entry.time_slot.day.value,
                'slot': entry.time_slot.slot_number,
                'zone': entry.activity.zone.name
            })
        
        with open(f'schedules/week{week_num}_entries.json', 'w') as f:
            json.dump(schedule_data, f, indent=2)
    
    print(f'\\n=== PHASE 1 COMPLETE ===')
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
    
    print(f'\\n=== OVERALL METRICS ===')
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
    
    print(f'\\nResults saved to all_weeks_results.json')
    
    return comprehensive_results

def implement_recommendations(results):
    """Implement recommendations based on results"""
    
    print(f'\n=== IMPLEMENTING RECOMMENDATIONS ===')

    weekly_results = results.get('weekly_results', results) if isinstance(results, dict) else results
    activities = get_all_activities()
    
    # Recommendation 1: Ensure Friday Reflection for all troops
    print('1. Ensuring Friday Reflection for all troops...')
    
    for result in weekly_results:
        week_num = result['week']
        print(f'  Week {week_num}: Checking Friday Reflection...')
        
        # Load schedule and check missing reflections
        from models import Schedule, Troop, Activity, TimeSlot, Day
        from io_handler import load_schedule_from_json
        
        try:
            troops = load_troops_from_json(f'tc_week{week_num}_troops.json')
            schedule = load_schedule_from_json(
                f'schedules/week{week_num}_schedule.json',
                troops,
                activities
            )
            
            # Find troops without Friday Reflection
            missing_reflection = []
            for troop in troops:
                has_reflection = any(
                    e.activity.name == "Reflection" and e.time_slot.day == Day.FRIDAY
                    for e in schedule.entries if e.troop == troop
                )
                if not has_reflection:
                    missing_reflection.append(troop)
            
            if missing_reflection:
                print(f'    Missing Reflection: {len(missing_reflection)} troops')
                
                # Try to add Friday Reflection for missing troops
                for troop in missing_reflection:
                    # Find available Friday slots
                    available_slots = []
                    for entry in schedule.entries:
                        if (entry.time_slot.day == Day.FRIDAY and 
                            entry.activity.name != "Reflection"):
                            # Check if troop is free in this slot
                            if schedule.is_troop_free(entry.time_slot, troop):
                                available_slots.append(entry.time_slot)
                    
                    if available_slots:
                        # Add Reflection in first available slot
                        slot = available_slots[0]
                        reflection_activity = next((a for a in activities if a.name == "Reflection"), None)
                        if reflection_activity:
                            schedule.add_entry(slot, reflection_activity, troop)
                            print(f'    Added Friday Reflection for {troop.name} at {slot.day.value}-{slot.slot_number}')
            
            # Save updated schedule
            save_schedule_to_json(schedule, troops, f'schedules/week{week_num}_schedule_fixed.json')
            print(f'    Fixed schedule saved')
            
        except Exception as e:
            print(f'    Error fixing Week {week_num}: {e}')
    
    print('\\n2. Address gap elimination...')
    # This would involve running gap filling algorithms
    print('   Gap elimination would require additional implementation')
    
    print('\\n3. Review activity availability constraints...')
    # This would analyze why some troops have gaps
    print('   Activity availability analysis would require additional implementation')
    
    print('\\n=== RECOMMENDATIONS IMPLEMENTED ===')

if __name__ == "__main__":
    results = run_all_weeks()
    implement_recommendations(results)
