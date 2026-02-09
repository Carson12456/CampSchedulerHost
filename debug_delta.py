
import sys
import os
sys.path.append(os.getcwd())

from core.models import Schedule, Troop, Activity, TimeSlot, Day, Zone, EXCLUSIVE_AREAS
from core.io_handler import load_schedule_from_json

from core.activities import get_all_activities

from core.activities import get_all_activities
from core.io_handler import load_troops_from_json

# Load the failing schedule data
schedule_file = "data/schedules/tc_week7_troops_schedule.json"
troop_file = "data/troops/tc_week7_troops.json"

all_activities = get_all_activities()
troops = load_troops_from_json(troop_file)
schedule = load_schedule_from_json(schedule_file, troops, all_activities)

# Find Taskalusa and its Monday activities
taskalusa = next(t for t in schedule.entries if t.troop.name == "Taskalusa").troop
entries = schedule.get_troop_schedule(taskalusa)

print(f"Taskalusa Schedule for Monday:")
monday_entries = [e for e in entries if e.time_slot.day == Day.MONDAY]
for e in monday_entries:
    print(f"  {e.time_slot}: {e.activity.name}")

# Identify the Delta slot and Tower/ODS slot
delta_entry = next((e for e in monday_entries if e.activity.name == "Delta"), None)
tower_ods_acts = set(EXCLUSIVE_AREAS.get("Tower", []) + EXCLUSIVE_AREAS.get("Outdoor Skills", []))
tower_entry = next((e for e in monday_entries if e.activity.name in tower_ods_acts), None)

if delta_entry and tower_entry:
    print(f"\nConflict found: {delta_entry.activity.name} @ {delta_entry.time_slot} vs {tower_entry.activity.name} @ {tower_entry.time_slot}")
    
    # Test is_activity_available logic manually
    print("\nTesting is_activity_available for Delta at that slot...")
    
    # Temporarily remove Delta to test if we can re-add it
    schedule.entries.remove(delta_entry)
    
    # Re-create Activity object for Delta
    delta_act = Activity("Delta", 1, Zone.DELTA) # Mock activity
    
    # Call is_activity_available
    available = schedule.is_activity_available(delta_entry.time_slot, delta_act, requesting_troop=taskalusa)
    print(f"is_activity_available returned: {available}")
    
    if available:
        print("FAIL: Validator allowed Delta despite adjacency!")
    else:
        print("SUCCESS: Validator correctly blocked Delta.")
else:
    print("Could not find both Delta and Tower/ODS on Monday for Taskalusa.")
