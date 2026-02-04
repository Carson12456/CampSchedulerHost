#!/usr/bin/env python3
"""
Check if troops actually want multi-slot activities in their preferences.
"""

from io_handler import load_troops_from_json
from activities import get_all_activities

def check_multislot_preferences():
    """Check if troops have multi-slot activities in their preferences."""
    print("=== CHECKING MULTI-SLOT ACTIVITY PREFERENCES ===")
    
    # Multi-slot activities from activities.py
    multislot_activities = {
        "Sailing": 1.5,
        "Canoe Snorkel": 2.0,
        "Float for Floats": 2.0,
        "Back of the Moon": 3.0,
        "Itasca State Park": 3.0,
        "Tamarac Wildlife Refuge": 3.0
    }
    
    # Find all troop files
    import glob
    troop_files = sorted(glob.glob("*troops.json"))
    
    total_requests = {}
    for activity in multislot_activities:
        total_requests[activity] = 0
    
    for troop_file in troop_files:
        print(f"\n--- {troop_file} ---")
        troops = load_troops_from_json(troop_file)
        
        for troop in troops:
            troop_multislot = []
            for activity_name, slots in multislot_activities.items():
                if activity_name in troop.preferences:
                    rank = troop.preferences.index(activity_name) + 1
                    troop_multislot.append(f"{activity_name} (#{rank}, {slots} slots)")
                    total_requests[activity_name] += 1
                    print(f"    DEBUG: {troop.name} wants {activity_name}, total now {total_requests[activity_name]}")
            
            if troop_multislot:
                print(f"  {troop.name}: {', '.join(troop_multislot)}")
            else:
                print(f"  {troop.name}: No multi-slot activities in preferences")
    
    print(f"\n=== SUMMARY OF MULTI-SLOT ACTIVITY REQUESTS ===")
    for activity, count in total_requests.items():
        slots = multislot_activities[activity]
        print(f"{activity}: {count} troops requested ({slots} slots each)")
    
    print(f"\nTotal multi-slot activity requests: {sum(total_requests.values())}")
    
    # Show which activities are most popular
    print(f"\n=== MOST POPULAR MULTI-SLOT ACTIVITIES ===")
    sorted_activities = sorted(total_requests.items(), key=lambda x: x[1], reverse=True)
    for activity, count in sorted_activities:
        if count > 0:
            print(f"{count:3d} troops: {activity} ({multislot_activities[activity]} slots)")

if __name__ == "__main__":
    check_multislot_preferences()
