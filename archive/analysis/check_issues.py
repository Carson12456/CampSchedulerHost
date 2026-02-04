"""Check for scheduling issues: boats activities and ODS conflicts."""
from io_handler import load_troops_from_json
from activities import get_all_activities
from constrained_scheduler import ConstrainedScheduler
from models import Day

# Load and schedule
troops = load_troops_from_json('sample_troops.json')
scheduler = ConstrainedScheduler(troops, get_all_activities())
schedule = scheduler.schedule_all()
time_slots = scheduler.time_slots

# Define activity lists
ods_activities = [
    'Knots and Lashings', 'Orienteering', 'GPS & Geocaching', 'Ultimate Survivor',
    'Leave No Trace', "What's Cooking", 'Chopped!', "Firem'n Chit/Totin' Chip"
]
boats_activities = ['Canoe/Kayak/Rowing', 'Canoe Snorkel', 'Nature Canoe', 'Float for Floats']

print("\n" + "="*60)
print("ISSUE INVESTIGATION")
print("="*60)

# Check Tuesday Slot 2 for ODS conflicts
print("\n=== TUESDAY SLOT 2 SCHEDULE ===")
tue_slot2 = [s for s in time_slots if s.day == Day.TUESDAY and s.slot_number == 2][0]
tue_slot2_entries = [e for e in schedule.entries if e.time_slot == tue_slot2]
print(f'Total troops in Tuesday Slot 2: {len(tue_slot2_entries)}')
for e in tue_slot2_entries:
    print(f'  {e.troop.name}: {e.activity.name}')

ods_at_tue_slot2 = [e for e in tue_slot2_entries if e.activity.name in ods_activities]
print(f'\nODS activities at Tue Slot 2: {len(ods_at_tue_slot2)}')
for e in ods_at_tue_slot2:
    print(f'  {e.troop.name}: {e.activity.name}')

# Check Boats activities
print(f'\n=== BOATS ACTIVITIES SCHEDULED ===')
boats_entries = [e for e in schedule.entries if e.activity.name in boats_activities]
print(f'Total boats entries: {len(boats_entries)}')
for boat_act in boats_activities:
    act_entries = [e for e in boats_entries if e.activity.name == boat_act]
    print(f'\n{boat_act}: {len(act_entries)} troops')
    for e in act_entries:
        print(f'  {e.troop.name}: {e.time_slot}')

# Check Massasoit's Tower and ODS schedule
print(f'\n=== MASSASOIT SCHEDULE (Tower + ODS) ===')
massasoit = [t for t in troops if t.name == "Massasoit"][0]
massasoit_entries = [e for e in schedule.entries if e.troop == massasoit]
tower_ods_all = ['Climbing Tower'] + ods_activities
massasoit_tower_ods = [e for e in massasoit_entries if e.activity.name in tower_ods_all]
print(f'Massasoit Tower/ODS activities:')
for e in sorted(massasoit_tower_ods, key=lambda x: (x.time_slot.day.value, x.time_slot.slot_number)):
    print(f'  {e.time_slot}: {e.activity.name}')

