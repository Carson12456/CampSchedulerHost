"""
Test Option 1: Reserved Friday Slot + Delayed Reflection
"""
from io_handler import load_troops_from_json
from constrained_scheduler import ConstrainedScheduler
from collections import defaultdict
import json

def analyze_schedule(schedule, scheduler):
    """Analyze clustering and Reflection slot distribution."""
    
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
        clustering_metrics[area_name] = {'days': days_used, 'total': total}
    
    reflection_slots = defaultdict(int)
    reflection_count = 0
    for entry in schedule.entries:
        if entry.activity.name == "Reflection":
            slot_num = entry.time_slot.slot_number
            reflection_slots[slot_num] += 1
            reflection_count += 1
    
    top5 = 0
    top10 = 0
    for troop in scheduler.troops:
        entries = [e for e in schedule.entries if e.troop.name == troop.name]
        scheduled_names = {e.activity.name for e in entries}
        
        for pref in troop.preferences[:5]:
            if pref in scheduled_names:
                top5 += 1
        
        for pref in troop.preferences[:10]:
            if pref in scheduled_names:
                top10 += 1
    
    total_troops = len(scheduler.troops)
    
    return {
        'clustering': clustering_metrics,
        'reflection_slots': dict(reflection_slots),
        'reflection_count': reflection_count,
        'top5': top5,
        'top10': top10,
        'total_troops': total_troops
    }

print("="*70)
print("OPTION 1: Reserved Friday Slot + Delayed Reflection")
print("="*70)

# Test Week 7 only for now
troops_file = 'tc_week7_troops.json'
troops = load_troops_from_json(troops_file)
scheduler = ConstrainedScheduler(troops)
schedule = scheduler.schedule_all()

metrics = analyze_schedule(schedule, scheduler)

print(f"\nWeek 7 Results:")
print(f"  Clustering:")
for area, data in metrics['clustering'].items():
    if data['total'] > 0:
        print(f"    {area}: {data['days']} days ({data['total']} activities)")

print(f"\n  Reflections Scheduled: {metrics['reflection_count']}/{metrics['total_troops']}")
print(f"  Reflection Slot Distribution:")
for slot, count in sorted(metrics['reflection_slots'].items()):
    print(f"    Slot {slot}: {count} troops")

print(f"\n  Preference Satisfaction:")
print(f"    Top 5: {metrics['top5']}/{metrics['total_troops']*5} ({metrics['top5']/(metrics['total_troops']*5)*100:.1f}%)")
print(f"    Top 10: {metrics['top10']}/{metrics['total_troops']*10} ({metrics['top10']/(metrics['total_troops']*10)*100:.1f}%)")
