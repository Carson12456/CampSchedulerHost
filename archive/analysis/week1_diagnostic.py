"""
Week 1 Scheduling Diagnostic
Analyzes how well the scheduler satisfied troop preferences
"""
import json
import sys
sys.path.insert(0, '.')

from models import Day
from activities import get_all_activities
from io_handler import load_troops_from_json
from constrained_scheduler import ConstrainedScheduler

# Load troops and generate schedule
troops_file = 'tc_week1_troops.json'
print("="*70)
print("WEEK 1 SCHEDULING DIAGNOSTIC")
print("="*70)

# Load troop data
with open(troops_file, 'r') as f:
    raw_data = json.load(f)

print("\n--- TROOP PREFERENCES ---")
for troop_data in raw_data['troops']:
    print(f"\n{troop_data['name']}:")
    print(f"  Commissioner: {troop_data.get('commissioner', 'N/A')}")
    print(f"  Top 10 Preferences:")
    for i, pref in enumerate(troop_data['preferences'][:10], 1):
        print(f"    {i}. {pref}")
    if troop_data.get('commissioner_assigned'):
        print(f"  Commissioner Assigned: {troop_data['commissioner_assigned']}")

# Generate schedule
print("\n" + "="*70)
print("GENERATING SCHEDULE...")
print("="*70)

troops = load_troops_from_json(troops_file)
activities = get_all_activities()
scheduler = ConstrainedScheduler(troops, activities)
schedule = scheduler.schedule_all()

# Analyze results
print("\n" + "="*70)
print("SCHEDULE ANALYSIS")
print("="*70)

for troop in troops:
    print(f"\n{'='*50}")
    print(f"TROOP: {troop.name}")
    print(f"{'='*50}")
    
    # Get scheduled activities
    entries = schedule.get_troop_schedule(troop)
    scheduled = {}
    for entry in entries:
        day = entry.time_slot.day.name
        slot = entry.time_slot.slot_number
        key = f"{day}-{slot}"
        if key not in scheduled:
            scheduled[key] = entry.activity.name
    
    scheduled_activities = set(scheduled.values())
    
    # Check preference satisfaction
    print("\nPreference Satisfaction:")
    top5_achieved = 0
    top10_achieved = 0
    unscheduled_prefs = []
    
    for i, pref in enumerate(troop.preferences[:20], 1):
        if pref in scheduled_activities:
            status = "[OK] SCHEDULED"
            if i <= 5:
                top5_achieved += 1
            if i <= 10:
                top10_achieved += 1
        else:
            status = "[X] NOT SCHEDULED"
            if i <= 10:
                unscheduled_prefs.append((i, pref))
        
        if i <= 10:
            print(f"  {i:2}. {pref:40} {status}")
    
    print(f"\n  Top 5 achieved: {top5_achieved}/5")
    print(f"  Top 10 achieved: {top10_achieved}/10")
    
    if unscheduled_prefs:
        print(f"\n  [!] Missing Top 10 preferences:")
        for rank, pref in unscheduled_prefs:
            print(f"      #{rank}: {pref}")
    
    # Show actual schedule
    print("\n  Actual Schedule:")
    for day in Day:
        day_entries = [(k, v) for k, v in scheduled.items() if k.startswith(day.name)]
        if day_entries:
            for key, act in sorted(day_entries):
                slot = key.split('-')[1]
                priority = troop.get_priority(act)
                priority_str = f"(Top {priority+1})" if priority < 20 else "(Fill)"
                print(f"    {day.name[:3]} Slot {slot}: {act} {priority_str}")

print("\n" + "="*70)
print("SUMMARY")
print("="*70)

total_top5 = 0
total_top10 = 0

for troop in troops:
    entries = schedule.get_troop_schedule(troop)
    scheduled_activities = set(e.activity.name for e in entries)
    
    t5 = sum(1 for i, p in enumerate(troop.preferences[:5]) if p in scheduled_activities)
    t10 = sum(1 for i, p in enumerate(troop.preferences[:10]) if p in scheduled_activities)
    
    total_top5 += t5
    total_top10 += t10
    
    print(f"{troop.name:20} Top 5: {t5}/5  Top 10: {t10}/10")

print(f"\nOverall: Top 5 = {total_top5}/{len(troops)*5}, Top 10 = {total_top10}/{len(troops)*10}")
