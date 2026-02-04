"""Check ODS double-booking issue."""
from constrained_scheduler import ConstrainedScheduler
from io_handler import load_troops_from_json
from models import Day
from collections import defaultdict

troops = load_troops_from_json('sample_troops.json')
s = ConstrainedScheduler(troops)
schedule = s.schedule_all()

# Check ODS activities
ods_activities = ['Knots and Lashings', 'Orienteering', 'GPS & Geocaching', 'Ultimate Survivor', 
                  'Leave No Trace', "What's Cooking", 'Chopped!', "Firem'n Chit/Totin' Chip"]

print('\n=== ODS Schedule by Slot ===')
by_slot = defaultdict(list)
for entry in schedule.entries:
    if entry.activity.name in ods_activities:
        key = f'{entry.time_slot.day.value[:3]}-{entry.time_slot.slot_number}'
        by_slot[key].append(f'{entry.troop.name}: {entry.activity.name}')

for slot in sorted(by_slot.keys()):
    troops_list = by_slot[slot]
    print(f'{slot}: {len(troops_list)} troops')
    for t in troops_list:
        print(f'  - {t}')
    if len(troops_list) > 1:
        print('  ^^^ DOUBLE BOOKING!')
