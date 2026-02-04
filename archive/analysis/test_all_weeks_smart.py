"""
Test smart Reflection across all weeks with Top 5 protection
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

weeks = [
    ('tc_week5_troops.json', 'Week 5'),
    ('tc_week6_troops.json', 'Week 6'),
    ('tc_week7_troops.json', 'Week 7')
]

print("="*70)
print("SMART REFLECTION - ALL WEEKS TEST")
print("="*70)

for troops_file, week_name in weeks:
    try:
        print(f"\n{'='*70}")
        print(f"{week_name}")
        print('='*70)
        
        troops = load_troops_from_json(troops_file)
        scheduler = ConstrainedScheduler(troops)
        schedule = scheduler.schedule_all()
        
        metrics = analyze_schedule(schedule, scheduler)
        
        print(f"\n{week_name} Results:")
        print(f"  Reflections: {metrics['reflection_count']}/{metrics['total_troops']}")
        print(f"  Top 5: {metrics['top5']}/{metrics['total_troops']*5} ({metrics['top5']/(metrics['total_troops']*5)*100:.1f}%)")
        print(f"  Top 10: {metrics['top10']}/{metrics['total_troops']*10} ({metrics['top10']/(metrics['total_troops']*10)*100:.1f}%)")
        
        print(f"\n  Clustering:")
        for area, data in metrics['clustering'].items():
            if data['total'] > 0:
                print(f"    {area}: {data['days']} days")
        
    except Exception as e:
        print(f"\nError testing {week_name}: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "="*70)
print("SUMMARY")
print("="*70)
