import sys
import json
import os

def run():
    print("Testing 2-hour activity satisfaction...")
    for i in range(1, 11):
        test_case_name = f"tc_week{i}_troops.json" if i <= 8 else f"voyageur_week{i-8}_troops.json"
        
        filename = f"data/troops/{test_case_name}"
        if not os.path.exists(filename):
            continue
            
        with open(filename) as f:
            data = json.load(f)
            
        sched_file = f"data/schedules/{test_case_name.replace('.json', '_schedule.json')}"
        if not os.path.exists(sched_file):
            print(f"No schedule for {test_case_name}")
            continue
            
        with open(sched_file) as f:
            sched = json.load(f)
            
        print(f"\nWeek {i}:")
        
        # Build troop schedule
        troop_sched = {}
        for entry in sched.get("entries", []):
            troop = entry["troop_name"]
            act = entry["activity_name"]
            if troop not in troop_sched: troop_sched[troop] = set()
            troop_sched[troop].add(act)
            
        # Check Top 10 for 2-hr activities
        missed = 0
        total = 0
        for troop in data.get("troops", []):
            tname = troop["name"]
            prefs = troop.get("preferences", [])[:10]
            for pref_idx, pref in enumerate(prefs):
                # Check if it's 2 hr
                is_2hr = pref in ["Float for Floats", "Canoe Snorkel", "Sailing"]
                if is_2hr:
                    total += 1
                    if pref not in troop_sched.get(tname, set()):
                        print(f"  MISSED: {tname} wanted {pref} (Rank #{pref_idx+1})")
                        missed += 1
        print(f"  Result: {missed} missed out of {total} requested")
        
run()