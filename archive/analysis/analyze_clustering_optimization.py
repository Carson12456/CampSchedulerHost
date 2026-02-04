"""
Analyze the impact of cross-schedule clustering optimization.
Compare before/after metrics for all weeks.
"""
from io_handler import load_troops_from_json
from constrained_scheduler import ConstrainedScheduler
from collections import defaultdict

def analyze_clustering(schedule, scheduler, week_name):
    """Analyze clustering metrics for a schedule."""
    CLUSTERING_AREAS = {
        "Outdoor Skills": ["Knots and Lashings", "Orienteering", "GPS & Geocaching", 
                          "Ultimate Survivor", "What's Cooking", "Chopped!"],
        "Tower": ["Climbing Tower"],
        "Rifle Range": ["Troop Rifle", "Troop Shotgun"],
        "Archery": ["Archery/Tomahawks/Slingshots"]
    }
    
    print(f"\n{'='*70}")
    print(f"CLUSTERING ANALYSIS - {week_name}")
    print(f"{'='*70}")
    
    for area_name, area_activities in CLUSTERING_AREAS.items():
        by_day = defaultdict(list)
        for entry in schedule.entries:
            if entry.activity.name in area_activities:
                day = entry.time_slot.day.name
                slot = entry.time_slot.slot_number
                by_day[day].append(f"{entry.troop.name}(S{slot})")
        
        total = sum(len(v) for v in by_day.values())
        days_used = len(by_day)
        
        if total > 0:
            print(f"\n{area_name}: {total} activities across {days_used} days")
            for day in ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY']:
                if day in by_day:
                    count = len(by_day[day])
                    print(f"  {day[:3]}: {count} activities - {', '.join(by_day[day][:5])}" + 
                          (f"... +{count-5} more" if count > 5 else ""))

def check_samoset_case(schedule, week_name):
    """Check specific Samoset GPS case from Week 7."""
    print(f"\n{'='*70}")
    print(f"SAMOSET GPS CHECK - {week_name}")
    print(f"{'='*70}")
    
    samoset_entries = [e for e in schedule.entries if e.troop.name == 'Samoset']
    if not samoset_entries:
        print("  Samoset not in this week")
        return
    
    # Find Wednesday activities
    wed_activities = {}
    for entry in samoset_entries:
        if entry.time_slot.day.name == 'WEDNESDAY':
            wed_activities[entry.time_slot.slot_number] = entry.activity.name
    
    print(f"\nSamoset Wednesday Schedule:")
    for slot in [1, 2, 3]:
        activity = wed_activities.get(slot, "---")
        print(f"  Slot {slot}: {activity}")
    
    # Check if GPS is scheduled
    gps_entry = next((e for e in samoset_entries if e.activity.name == "GPS & Geocaching"), None)
    if gps_entry:
        print(f"\nGPS & Geocaching: {gps_entry.time_slot.day.name[:3]}-{gps_entry.time_slot.slot_number}")
    
    # Check ODS clustering
    ods_acts = ["GPS & Geocaching", "Ultimate Survivor", "Orienteering", "Knots and Lashings"]
    samoset_ods = [e for e in samoset_entries if e.activity.name in ods_acts]
    if samoset_ods:
        print(f"\nSamoset ODS Activities:")
        for entry in samoset_ods:
            print(f"  {entry.time_slot.day.name[:3]}-{entry.time_slot.slot_number}: {entry.activity.name}")

def count_preference_satisfaction(schedule, troops):
    """Count Top 5/10 satisfaction."""
    top5 = 0
    top10 = 0
    
    for troop in troops:
        entries = [e for e in schedule.entries if e.troop.name == troop.name]
        scheduled_names = {e.activity.name for e in entries}
        
        for i, pref in enumerate(troop.preferences[:5]):
            if pref in scheduled_names:
                top5 += 1
        
        for i, pref in enumerate(troop.preferences[:10]):
            if pref in scheduled_names:
                top10 += 1
    
    total_troops = len(troops)
    return top5, top10, total_troops

# Test all weeks
weeks = [
    ('tc_week5_troops.json', 'Week 5'),
    ('tc_week6_troops.json', 'Week 6'),
    ('tc_week7_troops.json', 'Week 7')
]

print("="*70)
print("CROSS-SCHEDULE CLUSTERING OPTIMIZATION ANALYSIS")
print("="*70)

for troops_file, week_name in weeks:
    print(f"\n\n{'#'*70}")
    print(f"# {week_name}")
    print(f"{'#'*70}")
    
    try:
        troops = load_troops_from_json(troops_file)
        scheduler = ConstrainedScheduler(troops)
        schedule = scheduler.schedule_all()
        
        # Analyze clustering
        analyze_clustering(schedule, scheduler, week_name)
        
        # Check specific cases
        if week_name == 'Week 7':
            check_samoset_case(schedule, week_name)
        
        # Preference satisfaction
        top5, top10, total_troops = count_preference_satisfaction(schedule, troops)
        print(f"\n{'='*70}")
        print(f"PREFERENCE SATISFACTION - {week_name}")
        print(f"{'='*70}")
        print(f"  Top 5: {top5}/{total_troops*5} ({top5/(total_troops*5)*100:.1f}%)")
        print(f"  Top 10: {top10}/{total_troops*10} ({top10/(total_troops*10)*100:.1f}%)")
        
    except FileNotFoundError:
        print(f"  {troops_file} not found - skipping")
    except Exception as e:
        print(f"  Error analyzing {week_name}: {e}")

print(f"\n\n{'='*70}")
print("ANALYSIS COMPLETE")
print(f"{'='*70}")
