"""
Test Experiment 1: ODS Pre-clustering
Compare with baseline metrics.
"""
from io_handler import load_troops_from_json
from constrained_scheduler import ConstrainedScheduler
from collections import defaultdict

def analyze_schedule(schedule, scheduler):
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
    
    reflection_count = sum(1 for e in schedule.entries if e.activity.name == "Reflection")
    
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
        'reflection_count': reflection_count,
        'top5': top5,
        'top10': top10,
        'total_troops': total_troops
    }

print("="*70)
print("EXPERIMENT 1: ODS Pre-clustering")
print("="*70)

# Test Week 7
troops = load_troops_from_json('tc_week7_troops.json')
scheduler = ConstrainedScheduler(troops)
schedule = scheduler.schedule_all()

metrics = analyze_schedule(schedule, scheduler)

print(f"\nWeek 7 Results:")
print(f"  Clustering:")
for area, data in metrics['clustering'].items():
    if data['total'] > 0:
        print(f"    {area}: {data['days']} days ({data['total']} activities)")

print(f"\n  Reflections Scheduled: {metrics['reflection_count']}/{metrics['total_troops']}")

print(f"\n  Preference Satisfaction:")
print(f"    Top 5: {metrics['top5']}/{metrics['total_troops']*5} ({metrics['top5']/(metrics['total_troops']*5)*100:.1f}%)")
print(f"    Top 10: {metrics['top10']}/{metrics['total_troops']*10} ({metrics['top10']/(metrics['total_troops']*10)*100:.1f}%)")

# COMPARISON
print("\n" + "="*70)
print("COMPARISON WITH BASELINE")
print("="*70)
print("                    | Baseline | Experiment 1")
print("-"*55)
print(f"  ODS Days          |    3     |    {metrics['clustering']['Outdoor Skills']['days']}")
print(f"  Tower Days        |    4     |    {metrics['clustering']['Tower']['days']}")
print(f"  Rifle Days        |    4     |    {metrics['clustering']['Rifle Range']['days']}")
print(f"  Archery Days      |    4     |    {metrics['clustering']['Archery']['days']}")
print(f"  Top 5             |  98.2%   | {metrics['top5']/(metrics['total_troops']*5)*100:.1f}%")
print(f"  Top 10            |  87.3%   | {metrics['top10']/(metrics['total_troops']*10)*100:.1f}%")
print(f"  Reflections       |  11/11   |  {metrics['reflection_count']}/{metrics['total_troops']}")
