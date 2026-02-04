"""Debug why Samoset GPS is not being swapped."""
from io_handler import load_troops_from_json
from constrained_scheduler import ConstrainedScheduler

troops = load_troops_from_json('tc_week7_troops.json')
scheduler = ConstrainedScheduler(troops)

# Manually check before scheduling
print("Testing swap logic...")

# Get a troop after scheduling
import io
import contextlib

# Suppress scheduler output
with contextlib.redirect_stdout(io.StringIO()):
    schedule = scheduler.schedule_all()

# Now check Samoset
samoset = [t for t in troops if t.name == 'Samoset'][0]
samoset_entries = [e for e in schedule.entries if e.troop.name == 'Samoset']

gps_entry = next((e for e in samoset_entries if e.activity.name == "GPS & Geocaching"), None)
nine_sq_entry = next((e for e in samoset_entries if e.activity.name == "9 Square"), None)

if gps_entry and nine_sq_entry:
    print(f"\n=== MANUAL SWAP CHECK ===")
    print(f"GPS: {gps_entry.time_slot.day.name} Slot {gps_entry.time_slot.slot_number}")
    print(f"9 Square: {nine_sq_entry.time_slot.day.name} Slot {nine_sq_entry.time_slot.slot_number}")
    
    # Check if both on Wednesday
    if gps_entry.time_slot.day == nine_sq_entry.time_slot.day:
        print(f"\nBoth on same day: {gps_entry.time_slot.day.name}")
        print(f"GPS slot: {gps_entry.time_slot.slot_number}")
        print(f"9 Square slot: {nine_sq_entry.time_slot.slot_number}")
        
        # Check the swap improvement logic
        area_slot_num = gps_entry.time_slot.slot_number  # Should be 3
        swap_slot_num = nine_sq_entry.time_slot.slot_number  # Should be 2
        
        print(f"\nWould improve (slot 3 -> slot 2)? {area_slot_num == 3 and swap_slot_num == 2}")
        
        # Check if 9 Square is in swappable list
        SWAPPABLE = {
            "Gaga Ball", "9 Square", "Fishing", "Sauna",
            "Reserve Shower House", "Reserve Trading Post",
            "Campsite Time/Free Time"
        }
        print(f"\n9 Square is swappable? {nine_sq_entry.activity.name in SWAPPABLE}")
        
        # Check if GPS is in ODS list
        ODS = ["Knots and Lashings", "Orienteering", "GPS & Geocaching", 
              "Ultimate Survivor", "What's Cooking", "Chopped!"]
        print(f"GPS is ODS activity? {gps_entry.activity.name in ODS}")
        
        # Check other ODS on Wednesday
        ods_wed = [e for e in samoset_entries 
                   if e.activity.name in ODS 
                   and e.time_slot.day.name == "WEDNESDAY"
                   and e != gps_entry]
        print(f"\nOther ODS on Wednesday: {len(ods_wed)}")
        print(f"Should trigger isolated slot logic? {len(ods_wed) == 0}")
