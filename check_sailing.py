"""Quick check for Sailing slot bugs."""
import json
from pathlib import Path

weeks = [
    'tc_week4_troops_schedule.json', 
    'tc_week5_troops_schedule.json', 
    'tc_week7_troops_schedule.json', 
    'voyageur_week1_troops_schedule.json', 
    'voyageur_week3_troops_schedule.json'
]

total_bugs = 0

for week_file in weeks:
    path = Path('data/schedules') / week_file
    data = json.load(open(path))
    sailing = [e for e in data['entries'] if e['activity_name'] == 'Sailing']
    
    troop_slots = {}
    for e in sailing:
        troop_slots.setdefault(e['troop_name'], []).append(e['slot'])
    
    week_bugs = 0
    print(f"\n{week_file.replace('_schedule.json', '')}:")
    for troop, slots in sorted(troop_slots.items()):
        if len(slots) < 2:
            print(f"  {troop}: {len(slots)} slots - BUG")
            week_bugs += 1
        else:
            print(f"  {troop}: {len(slots)} slots - OK")
    
    if week_bugs == 0:
        print("  No bugs!")
    total_bugs += week_bugs

print(f"\n=== TOTAL BUGS: {total_bugs} ===")
