"""
Create baseline metrics with current Reflection-first approach.
"""
from io_handler import load_troops_from_json
from constrained_scheduler import ConstrainedScheduler
from collections import defaultdict

def analyze_schedule(schedule, scheduler, week_name):
    """Analyze clustering and Reflection slot distribution."""
    
    # Clustering metrics
    CLUSTERING_AREAS = {
        "Outdoor Skills": ["Knots and Lashings", "Orienteering", "GPS & Geocaching", 
                          "Ultimate Survivor", "What's Cooking", "Chopped!"],
        "Tower": ["Climbing Tower"],
        "Rifle Range": ["Troop Rifle", "Troop Shotgun"],
        "Archery": ["Archery/Tomahawks/Slingshots"]
    }
    
    clustering_metrics = {}
    for area_name, area_activities in CLUSTERING_AREAS.items():
        by_day = defaultdict(int)
        for entry in schedule.entries:
            if entry.activity.name in area_activities:
                by_day[entry.time_slot.day] += 1
        
        days_used = len([d for d in by_day if by_day[d] > 0])
        total = sum(by_day.values())
        clustering_metrics[area_name] = {
            'days': days_used,
            'total': total
        }
    
    # Reflection slot distribution
    reflection_slots = defaultdict(int)
    for entry in schedule.entries:
        if entry.activity.name == "Reflection":
            slot_num = entry.time_slot.slot_number
            reflection_slots[slot_num] += 1
    
    # Preference satisfaction
    top5 = 0
    top10 = 0
    for troop in scheduler.troops:
        entries = [e for e in schedule.entries if e.troop.name == troop.name]
        scheduled_names = {e.activity.name for e in entries}
        
        for i, pref in enumerate(troop.preferences[:5]):
            if pref in scheduled_names:
                top5 += 1
        
        for i, pref in enumerate(troop.preferences[:10]):
            if pref in scheduled_names:
                top10 += 1
    
    total_troops = len(scheduler.troops)
    
    return {
        'clustering': clustering_metrics,
        'reflection_slots': dict(reflection_slots),
        'top5': top5,
        'top10': top10,
        'total_troops': total_troops
    }

print("="*70)
print("BASELINE: Current Reflection-First Approach")
print("="*70)

weeks = [
    ('tc_week5_troops.json', 'Week 5'),
    ('tc_week6_troops.json', 'Week 6'),
    ('tc_week7_troops.json', 'Week 7')
]

baseline_results = {}

for troops_file, week_name in weeks:
    try:
        print(f"\n\n### {week_name} ###")
        troops = load_troops_from_json(troops_file)
        scheduler = ConstrainedScheduler(troops)
        schedule = scheduler.schedule_all()
        
        metrics = analyze_schedule(schedule, scheduler, week_name)
        baseline_results[week_name] = metrics
        
        print(f"\n{week_name} Results:")
        print(f"  Clustering:")
        for area, data in metrics['clustering'].items():
            if data['total'] > 0:
                print(f"    {area}: {data['days']} days ({data['total']} activities)")
        
        print(f"\n  Reflection Slot Distribution:")
        for slot, count in sorted(metrics['reflection_slots'].items()):
            print(f"    Slot {slot}: {count} troops")
        
        print(f"\n  Preference Satisfaction:")
        print(f"    Top 5: {metrics['top5']}/{metrics['total_troops']*5} ({metrics['top5']/(metrics['total_troops']*5)*100:.1f}%)")
        print(f"    Top 10: {metrics['top10']}/{metrics['total_troops']*10} ({metrics['top10']/(metrics['total_troops']*10)*100:.1f}%)")
        
    except Exception as e:
        print(f"  Error: {e}")

print("\n" + "="*70)
print("BASELINE COMPLETE")
print("="*70)

# Save for comparison
import json
with open('baseline_metrics.json', 'w') as f:
    json.dump(baseline_results, f, indent=2, default=str)
    print("\nBaseline saved to baseline_metrics.json")
