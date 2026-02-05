#!/usr/bin/env python3
"""
Test Multi-Slot Activity Scheduling
Tests if multi-slot activities can be scheduled properly.
"""

from models import Day, TimeSlot, generate_time_slots, ScheduleEntry, Troop, Schedule
from activities import get_all_activities, get_activity_by_name
from io_handler import load_troops_from_json
from constrained_scheduler import ConstrainedScheduler

def test_multislot_scheduling():
    """Test if multi-slot activities can be scheduled."""
    print("=== TESTING MULTI-SLOT ACTIVITY SCHEDULING ===")
    
    # Load a test troop
    troops = load_troops_from_json("tc_week1_troops.json")
    if not troops:
        print("No troops found!")
        return
    
    troop = troops[0]  # Use first troop
    activities = get_all_activities()
    
    # Test multi-slot activities
    multislot_activities = [
        ("Sailing", 1.5),
        ("Canoe Snorkel", 2.0),
        ("Float for Floats", 2.0),
        ("Back of the Moon", 3.0),
        ("Itasca State Park", 3.0),
        ("Tamarac Wildlife Refuge", 3.0)
    ]
    
    scheduler = ConstrainedScheduler(troops, activities, voyageur_mode=False)
    
    for activity_name, expected_slots in multislot_activities:
        activity = get_activity_by_name(activity_name)
        if not activity:
            print(f"Activity {activity_name} not found!")
            continue
            
        print(f"\n--- Testing {activity_name} ({expected_slots} slots) ---")
        
        # Test each possible slot
        for day in [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY]:  # Skip Thursday (2 slots) and Friday
            max_slot = 3
            for slot_num in range(1, max_slot + 1):
                slot = next((s for s in scheduler.time_slots 
                           if s.day == day and s.slot_number == slot_num), None)
                
                if not slot:
                    continue
                
                # Check if can be scheduled
                can_schedule = scheduler._can_schedule(troop, activity, slot, day)
                
                # Check boundary logic
                effective_slots = scheduler.schedule._get_effective_slots(activity, troop)
                slots_needed = int(effective_slots + 0.5)
                max_day_slot = 2 if day == Day.THURSDAY else 3
                boundary_ok = slot.slot_number + slots_needed - 1 <= max_day_slot
                
                print(f"  {day.name[:3]}-{slot_num}: can_schedule={can_schedule}, "
                      f"boundary_ok={boundary_ok}, slots_needed={slots_needed}")
                
                if not boundary_ok:
                    print(f"    ❌ BOUNDARY VIOLATION: {activity_name} needs {slots_needed} slots, "
                          f"starting at {slot.slot_number} would extend to slot {slot.slot_number + slots_needed - 1}")
                
                # Test if we can actually add it
                if can_schedule:
                    # Create a test schedule
                    test_schedule = Schedule()
                    success = test_schedule.add_entry(slot, activity, troop)
                    print(f"    add_entry result: {success}")
                    
                    if success:
                        # Check if continuation entries were added
                        entries = test_schedule.get_troop_schedule(troop)
                        print(f"    Total entries for {activity_name}: {len(entries)}")
                        for entry in entries:
                            if entry.activity.name == activity_name:
                                print(f"      {entry.time_slot.day.name}-{entry.time_slot.slot_number}")
                    else:
                        print(f"    ❌ FAILED to add {activity_name} to {day.name}-{slot_num}")

def test_sailing_specifically():
    """Test Sailing specifically since it's the most common multi-slot activity."""
    print("\n=== TESTING SAILING SPECIFICALLY ===")
    
    troops = load_troops_from_json("tc_week1_troops.json")
    if not troops:
        return
    
    troop = troops[0]
    sailing = get_activity_by_name("Sailing")
    if not sailing:
        print("Sailing activity not found!")
        return
    
    scheduler = ConstrainedScheduler(troops, get_all_activities(), voyageur_mode=False)
    
    # Test Sailing in different slots
    for day in [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY]:
        print(f"\n--- Sailing on {day.name} ---")
        
        for slot_num in [1, 2]:  # Sailing can only start in slots 1 or 2
            slot = next((s for s in scheduler.time_slots 
                       if s.day == day and s.slot_number == slot_num), None)
            
            if not slot:
                continue
            
            # Check Sailing-specific constraints
            sailing_ok = scheduler._can_schedule_sailing(troop, slot, day)
            general_ok = scheduler._can_schedule(troop, sailing, slot, day)
            
            print(f"  Slot {slot_num}: _can_schedule_sailing={sailing_ok}, _can_schedule={general_ok}")
            
            if sailing_ok and general_ok:
                # Try to actually schedule it
                test_schedule = Schedule()
                success = test_schedule.add_entry(slot, sailing, troop)
                print(f"    add_entry result: {success}")
                
                if success:
                    entries = [e for e in test_schedule.entries if e.activity.name == "Sailing"]
                    print(f"    Sailing entries: {len(entries)}")
                    for entry in entries:
                        print(f"      {entry.time_slot.day.name}-{entry.time_slot.slot_number}")

if __name__ == "__main__":
    test_multislot_scheduling()
    test_sailing_specifically()
