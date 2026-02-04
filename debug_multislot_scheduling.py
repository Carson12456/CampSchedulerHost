#!/usr/bin/env python3
"""
Debug why multi-slot activities aren't being scheduled in the main scheduler.
"""

from io_handler import load_troops_from_json
from activities import get_all_activities, get_activity_by_name
from constrained_scheduler import ConstrainedScheduler

def debug_multislot_scheduling():
    """Debug why multi-slot activities aren't being scheduled."""
    print("=== DEBUGGING MULTI-SLOT SCHEDULING ===")
    
    # Load a test week
    troops = load_troops_from_json("tc_week3_troops.json")  # Has lots of multi-slot requests
    activities = get_all_activities()
    
    # Find a troop that wants Sailing (most popular multi-slot)
    target_troop = None
    for troop in troops:
        if "Sailing" in troop.preferences:
            target_troop = troop
            sailing_rank = troop.preferences.index("Sailing") + 1
            print(f"Found troop {troop.name} wants Sailing as #{sailing_rank}")
            break
    
    if not target_troop:
        print("No troop wants Sailing!")
        return
    
    # Create scheduler
    scheduler = ConstrainedScheduler(troops, activities, voyageur_mode=False)
    
    # Test Sailing scheduling specifically
    sailing = get_activity_by_name("Sailing")
    print(f"\n--- TESTING SAILING SCHEDULING FOR {target_troop.name} ---")
    
    # Check each possible slot
    from models import Day
    for day in [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY]:
        print(f"\n{day.name}:")
        
        for slot_num in [1, 2]:  # Sailing can only start in slots 1 or 2
            slot = next((s for s in scheduler.time_slots 
                       if s.day == day and s.slot_number == slot_num), None)
            
            if not slot:
                continue
            
            # Test all the scheduling checks
            print(f"  Slot {slot_num}:")
            
            # Basic can_schedule check
            can_schedule = scheduler._can_schedule(target_troop, sailing, slot, day)
            print(f"    _can_schedule: {can_schedule}")
            
            # Sailing-specific check
            sailing_ok = scheduler._can_schedule_sailing(target_troop, slot, day)
            print(f"    _can_schedule_sailing: {sailing_ok}")
            
            # Troop free check
            troop_free = scheduler.schedule.is_troop_free(slot, target_troop)
            print(f"    is_troop_free: {troop_free}")
            
            # If can schedule, try to actually add it
            if can_schedule and sailing_ok and troop_free:
                print(f"    [OK] Should be able to schedule Sailing here!")
                
                # Try adding to a test schedule
                test_schedule = scheduler.schedule.__class__()
                success = test_schedule.add_entry(slot, sailing, target_troop)
                print(f"    Test add_entry result: {success}")
                
                if success:
                    entries = [e for e in test_schedule.entries if e.activity.name == "Sailing"]
                    print(f"    Sailing entries created: {len(entries)}")
                    for entry in entries:
                        print(f"      {entry.time_slot.day.name}-{entry.time_slot.slot_number}")
            else:
                print(f"    [FAIL] Cannot schedule Sailing here")
    
    # Now let's see what actually gets scheduled in a real run
    print(f"\n=== RUNNING ACTUAL SCHEDULER FOR {target_troop.name} ===")
    
    # Create fresh scheduler and run it
    fresh_scheduler = ConstrainedScheduler(troops, activities, voyageur_mode=False)
    schedule = fresh_scheduler.schedule_all()
    
    # Check what this troop actually got
    troop_entries = [e for e in schedule.entries if e.troop == target_troop]
    print(f"\n{target_troop.name} got {len(troop_entries)} activities:")
    
    for entry in sorted(troop_entries, key=lambda e: (e.time_slot.day.value, e.time_slot.slot_number)):
        day = entry.time_slot.day.name
        slot = entry.time_slot.slot_number
        activity = entry.activity.name
        slots = entry.activity.slots
        rank = target_troop.get_priority(activity)
        rank_str = f"#{rank+1}" if rank is not None else "N/A"
        print(f"  {day}-{slot}: {activity} ({slots} slots) {rank_str}")
    
    # Check if they got any multi-slot activities
    multislot_entries = [e for e in troop_entries if e.activity.slots > 1.0]
    print(f"\nMulti-slot activities for {target_troop.name}: {len(multislot_entries)}")
    for entry in multislot_entries:
        print(f"  {entry.activity.name} ({entry.activity.slots} slots)")

if __name__ == "__main__":
    debug_multislot_scheduling()
