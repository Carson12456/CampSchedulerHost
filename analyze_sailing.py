"""Analyze Sailing entries per troop."""
import json
from pathlib import Path

weeks = [
    "tc_week4_troops_schedule.json",
    "tc_week5_troops_schedule.json",
    "tc_week7_troops_schedule.json",
    "voyageur_week1_troops_schedule.json",
    "voyageur_week3_troops_schedule.json",
]

schedules_dir = Path("data/schedules")

for week_file in weeks:
    path = schedules_dir / week_file
    if not path.exists():
        print(f"Missing: {week_file}")
        continue
    
    with open(path) as f:
        data = json.load(f)
    
    sailing = [e for e in data["entries"] if e["activity_name"] == "Sailing"]
    
    # Group by troop
    troop_slots = {}
    for e in sailing:
        troop_slots.setdefault(e["troop_name"], []).append(f"{e['day'][:3]}-{e['slot']}")
    
    print(f"\n=== {week_file.replace('_schedule.json', '')} ===")
    print(f"Total Sailing entries: {len(sailing)}")
    
    if troop_slots:
        for troop, slots in sorted(troop_slots.items()):
            status = "OK (2 slots)" if len(slots) >= 2 else "BUG (1 slot only!)"
            print(f"  {troop}: {slots} - {status}")
    else:
        print("  No Sailing scheduled in this week")
    
    # Check for troops who wanted sailing but didn't get it
    troops = data.get("troops", [])
    troops_wanting_sailing = [t for t in troops if "Sailing" in t.get("preferences", [])[:10]]
    scheduled = set(troop_slots.keys())
    not_scheduled = [t["name"] for t in troops_wanting_sailing if t["name"] not in scheduled]
    
    if not_scheduled:
        print(f"  MISSED Sailing (wanted in Top 10): {not_scheduled}")
