"""Test gap calculation logic."""
from io_handler import load_troops_from_json
from constrained_scheduler import ConstrainedScheduler
from models import Day

troops = load_troops_from_json('tc_week7_troops.json')
scheduler = ConstrainedScheduler(troops)
schedule = scheduler.schedule_all()

# Find Samoset entries
samoset = [t for t in troops if t.name == 'Samoset'][0]
samoset_entries = [e for e in schedule.entries if e.troop.name == 'Samoset']

# Find Wednesday ODS activities for Samoset
ods_activities = ["Knots and Lashings", "Orienteering", "GPS & Geocaching", 
                 "Ultimate Survivor", "What's Cooking", "Chopped!"]

wed_ods = [e for e in samoset_entries 
           if e.time_slot.day.name == "WEDNESDAY" and e.activity.name in ods_activities]

print(f"\n=== SAMOSET WEDNESDAY ODS ACTIVITIES ===")
for entry in wed_ods:
    print(f"  Slot {entry.time_slot.slot_number}: {entry.activity.name}")

# Check if there are OTHER ODS activities on Wednesday for gap calculation
gps_entry = next((e for e in samoset_entries if e.activity.name == "GPS & Geocaching"), None)
if gps_entry and wed_ods:
    print(f"\n=== GAP CALCULATION ===")
    print(f"GPS at slot: {gps_entry.time_slot.slot_number}")
    
    other_ods_wed = [e for e in wed_ods if e != gps_entry]
    print(f"Other ODS on Wednesday: {[f'{e.activity.name} (S{e.time_slot.slot_number})' for e in other_ods_wed]}")
    
    if not other_ods_wed:
        print("NO other ODS activities on Wednesday for Samoset - This is the issue!")
        print("The optimization needs at least 2 ODS activities on the same day to measure gaps.")
