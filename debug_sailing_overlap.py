
from models import Schedule, Troop, TimeSlot, Day, Activity, Zone, EXCLUSIVE_AREAS
from constrained_scheduler import ConstrainedScheduler
import sys

def test_sailing_overlap():
    print("Testing Sailing Overlap Logic...")
    
    # Setup
    scheduler = ConstrainedScheduler([], [])
    schedule = scheduler.schedule
    
    # Create troops
    troop_a = Troop("Troop A", "Camp A", [])
    troop_b = Troop("Troop B", "Camp B", [])
    
    # Create Sailing activity (1.5 slots)
    sailing = Activity("Sailing", 1.5, Zone.BEACH)
    
    # Slots
    mon_1 = TimeSlot(Day.MONDAY, 1)
    mon_2 = TimeSlot(Day.MONDAY, 2)
    mon_3 = TimeSlot(Day.MONDAY, 3)
    
    # Add Sailing for Troop A at Mon-1
    print(f"\nAdding Sailing for Troop A at {mon_1}...")
    success = schedule.add_entry(mon_1, sailing, troop_a)
    print(f"Success: {success}")
    
    if not success:
        print("Failed to add first sailing! Exiting.")
        return
        
    # Check entries - expect Mon-1 and Mon-2
    entries = schedule.get_troop_schedule(troop_a)
    print(f"Troop A entries: {[(e.time_slot, e.activity.name) for e in entries]}")
    
    # Verify Mon-2 is occupied by Troop A
    occupied = not schedule.is_troop_free(mon_2, troop_a)
    print(f"Is Troop A busy at {mon_2}? {occupied} (Expect True)")
    
    # Now try to add Sailing for Troop B at Mon-2
    print(f"\nTrying to add Sailing for Troop B at {mon_2}...")
    
    # First check availability
    available = schedule.is_activity_available(mon_2, sailing, troop_b)
    print(f"Is Sailing available for Troop B at {mon_2}? {available} (Expect True with fix)")
    
    if available:
        success = schedule.add_entry(mon_2, sailing, troop_b)
        print(f"Add Success: {success}")
        
        # Check entries - expect Mon-2 and Mon-3 for Troop B
        entries = schedule.get_troop_schedule(troop_b)
        print(f"Troop B entries: {[(e.time_slot, e.activity.name) for e in entries]}")
        
        # Verify Mon-2 has both troops
        slot2_entries = schedule.get_slot_activities(mon_2)
        print(f"Slot {mon_2} activities: {[(e.troop.name, e.activity.name) for e in slot2_entries]}")
    else:
        print("Sailing NOT available at Mon-2 (Fix not working or blocked by another constraint)")

if __name__ == "__main__":
    test_sailing_overlap()
