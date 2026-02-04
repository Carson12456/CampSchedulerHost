
import json
import glob
import math
from collections import defaultdict

# Manual Activity Durations (Source: activities.py)
ACTIVITY_SLOTS = {
    "Canoe Snorkel": 2,
    "Float for Floats": 2,
    "Sailing": 2, # 1.5 rounds to 2
    "Back of the Moon": 3,
    "Itasca State Park": 3,
    "Tamarac Wildlife Refuge": 3,
    "Climbing Tower": 1.0 # Default, dynamic check needed? 
    # Note: Tower is dynamic logic, detected script might have trouble.
    # We will focus on the fixed ones first.
}

def check_file(filename):
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error loading {filename}: {e}")
        return
    
    # Check if this is a schedule file (has 'entries')
    schedule = data.get("entries", [])
    if not schedule:
        # Fallback/Debug
        # print(f"  Skipping {filename}: No 'entries' found (might be troop file)")
        return
    
    issues = []
    
    # Map Entries by Troop -> Day -> Slot
    troop_day_slots = defaultdict(lambda: defaultdict(dict))
    
    for entry in schedule:
        troop = entry.get("troop_name") or entry.get("troop")
        day = entry.get("day")
        slot = entry.get("slot")
        act = entry.get("activity_name") or entry.get("activity")
        
        if troop and day and slot and act:
            troop_day_slots[troop][day][int(slot)] = act
            
    # Check for Broken Multi-Slot
    for troop, days in troop_day_slots.items():
        for day, slots in days.items():
            sorted_slots = sorted(slots.keys())
            
            # Identify activities present
            activities_present = set(slots.values())
            
            for act_name in activities_present:
                if act_name in ACTIVITY_SLOTS:
                    expected = ACTIVITY_SLOTS[act_name]
                    
                    # Find all slots for this activity
                    actual_slots = [s for s, a in slots.items() if a == act_name]
                    actual_slots.sort()
                    count = len(actual_slots)
                    
                    # If this is Tower, logic is complex (skip for now)
                    if act_name == "Climbing Tower": 
                        continue
                        
                    if count != expected:
                         # Double check strict float/int (1.5 -> 2)
                         # Assuming expected is int
                         msg = f"{troop} - {act_name} at {day}: Found {count} slots {actual_slots}, expected {expected}"
                         if msg not in issues:
                             issues.append(msg)

    if issues:
        print(f"\n--- Issues in {filename} ---")
        for i in issues:
            print(i)
    else:
        # print(f"clean: {filename}")
        pass

if __name__ == "__main__":
    # Check produced schedules
    files = glob.glob("schedules/*_schedule.json")
    print(f"Found {len(files)} schedule files to check.")
    for f in files:
        check_file(f)
