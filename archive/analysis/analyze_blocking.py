"""
Analyze the effectiveness of area pair day blocking.
"""
from constrained_scheduler import ConstrainedScheduler
from io_handler import load_troops_from_json
from models import Day

def analyze_day_blocking():
    """Analyze how well area pair day blocking works."""
    troops = load_troops_from_json("sample_troops.json")
    scheduler = ConstrainedScheduler(troops)
    schedule = scheduler.schedule_all()
    
    print("\n" + "="*70)
    print("AREA PAIR DAY BLOCKING ANALYSIS")
    print("="*70)
    
    # Define activity pairs
    pairs = {
        "Delta+Boats": {
            "activities": ["Delta"],
            "expected_days": scheduler.COMMISSIONER_DELTA_DAYS
        },
        "Super Troop+Rifle": {
            "activities": ["Super Troop", "Troop Rifle", "Troop Shotgun"],
            "expected_days": scheduler.COMMISSIONER_SUPER_TROOP_DAYS
        },
        "Archery+Sailing": {
            "activities": ["Archery/Tomahawks/Slingshots", "Sailing"],
            "expected_days": scheduler.COMMISSIONER_ARCHERY_DAYS
        },
        "Tower+ODS": {
            "activities": ["Climbing Tower", "Knots and Lashings", "Orienteering", 
                          "GPS & Geocaching", "Ultimate Survivor", "Leave No Trace",
                          "What's Cooking", "Chopped!", "Firem'n Chit/Totin' Chip"],
            "expected_days": scheduler.COMMISSIONER_TOWER_ODS_DAYS
        }
    }
    
    # Analyze each pair
    for pair_name, pair_info in pairs.items():
        print(f"\n--- {pair_name} ---")
        print(f"Expected days: A={pair_info['expected_days']['Commissioner A'].value}, "
              f"B={pair_info['expected_days']['Commissioner B'].value}, "
              f"C={pair_info['expected_days']['Commissioner C'].value}")
        
        on_day = 0  # Activities scheduled on expected commissioner day
        off_day = 0  # Activities that had to spill to other days
        
        details = {"on_day": [], "off_day": []}
        
        for entry in schedule.entries:
            if entry.activity.name not in pair_info["activities"]:
                continue
            
            troop_name = entry.troop.name
            commissioner = scheduler.troop_commissioner.get(troop_name, "")
            expected_day = pair_info["expected_days"].get(commissioner)
            actual_day = entry.time_slot.day
            
            if expected_day and actual_day == expected_day:
                on_day += 1
                details["on_day"].append(f"{troop_name}: {entry.activity.name} on {actual_day.value}")
            else:
                off_day += 1
                expected_str = expected_day.value if expected_day else "N/A"
                details["off_day"].append(f"{troop_name}: {entry.activity.name} on {actual_day.value} (expected {expected_str})")
        
        total = on_day + off_day
        if total > 0:
            percentage = (on_day / total) * 100
            print(f"On commissioner day: {on_day}/{total} ({percentage:.1f}%)")
            print(f"Spilled to other days: {off_day}/{total}")
            
            if details["off_day"]:
                print("\nSpillover details:")
                for detail in details["off_day"][:5]:  # Show first 5
                    print(f"  - {detail}")
                if len(details["off_day"]) > 5:
                    print(f"  ... and {len(details['off_day'])-5} more")
        else:
            print("No activities in this pair were scheduled.")
    
    # Overall summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    total_on = 0
    total_off = 0
    
    for pair_name, pair_info in pairs.items():
        for entry in schedule.entries:
            if entry.activity.name not in pair_info["activities"]:
                continue
            
            commissioner = scheduler.troop_commissioner.get(entry.troop.name, "")
            expected_day = pair_info["expected_days"].get(commissioner)
            actual_day = entry.time_slot.day
            
            if expected_day and actual_day == expected_day:
                total_on += 1
            else:
                total_off += 1
    
    total = total_on + total_off
    if total > 0:
        print(f"\nOverall area pair blocking effectiveness: {total_on}/{total} ({(total_on/total)*100:.1f}%)")
        print(f"Activities that needed to spill: {total_off}/{total}")
        
    # Check Top 5/10 preservation
    print("\n--- Top 5/10 Preservation Check ---")
    for troop in troops:
        troop_schedule = schedule.get_troop_schedule(troop)
        top5_count = sum(1 for e in troop_schedule if troop.get_priority(e.activity.name) < 5)
        top10_count = sum(1 for e in troop_schedule if troop.get_priority(e.activity.name) < 10)
        print(f"{troop.name}: Top 5 = {top5_count}/5, Top 10 = {top10_count}/10")

if __name__ == "__main__":
    analyze_day_blocking()
