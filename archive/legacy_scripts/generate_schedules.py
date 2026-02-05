#!/usr/bin/env python3
"""Generate current schedules and evaluate success metrics"""

from constrained_scheduler import ConstrainedScheduler
from io_handler import load_troops_from_json
from activities import get_all_activities
import json

def main():
    # Load available week data
    weeks = []
    for i in range(1, 4):
        try:
            troops = load_troops_from_json(f'tc_week{i}_troops.json')
            weeks.append((i, troops))
            print(f'Loaded Week {i}: {len(troops)} troops')
        except FileNotFoundError:
            print(f'Week {i} data not found')

    if not weeks:
        print('No week data found, using test data')
        weeks = [(1, [
            {'name': 'Test Troop 1', 'campsite': 'Site A', 'preferences': ['Aqua Trampoline', 'Climbing Tower', 'Archery'], 'scouts': 12, 'adults': 2},
            {'name': 'Test Troop 2', 'campsite': 'Site B', 'preferences': ['Water Polo', 'Sailing', 'Delta'], 'scouts': 15, 'adults': 2}
        ])]

    # Generate schedules and collect metrics
    results = []
    activities = get_all_activities()

    for week_num, troops_data in weeks:
        print(f'\n=== Processing Week {week_num} ===')
        
        # Data is already loaded as Troop objects
        troops = troops_data
        
        # Schedule
        scheduler = ConstrainedScheduler(troops, activities)
        schedule = scheduler.schedule_all()
        
        # Get statistics
        stats = scheduler.get_stats()
        results.append({
            'week': week_num,
            'troops': len(troops),
            'stats': stats
        })
        
        print(f'Week {week_num} completed')
        print(f'Total scheduled: {stats.get("total_scheduled", "N/A")}')
        print(f'Top 5 achieved: {stats.get("top5_achieved", "N/A")}')
        print(f'Top 10 achieved: {stats.get("top10_achieved", "N/A")}')

    # Save results
    with open('current_schedules.json', 'w') as f:
        json.dump(results, f, indent=2)

    print(f'\n=== SUMMARY ===')
    print(f'Processed {len(results)} weeks')
    print('Results saved to current_schedules.json')
    
    return results

if __name__ == "__main__":
    main()
