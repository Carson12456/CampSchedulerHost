"""Debug Samoset GPS scheduling."""
from io_handler import load_troops_from_json
from constrained_scheduler import ConstrainedScheduler
from models import Day

troops = load_troops_from_json('tc_week6_troops.json')
scheduler = ConstrainedScheduler(troops)
schedule = scheduler.schedule_all()

# Find Samoset's schedule
samoset = [t for t in troops if t.name == 'Samoset'][0]
print('\n=== SAMOSET SCHEDULE ===')
samoset_entries = sorted([e for e in schedule.entries if e.troop.name == 'Samoset'], 
                         key=lambda x: (x.time_slot.day.value, x.time_slot.slot_number))
for e in samoset_entries:
    prio = samoset.preferences.index(e.activity.name) + 1 if e.activity.name in samoset.preferences else 'N/A'
    print(f'{e.time_slot}: {e.activity.name} (Pref #{prio})')

# Check what's at Wed Slot 2
print('\n=== WEDNESDAY SLOT 2 SCHEDULE ===')
wed_s2 = [s for s in scheduler.time_slots if s.day == Day.WEDNESDAY and s.slot_number == 2][0]
wed_s2_entries = [e for e in schedule.entries if e.time_slot == wed_s2]
for e in wed_s2_entries:
    print(f'{e.troop.name}: {e.activity.name}')

# Check Super Troop placement for Commissioner B
print('\n=== COMMISSIONER B SUPER TROOP ===')
comm_b_troops = ['Tamanend', 'Samoset', 'Black Hawk']
for name in comm_b_troops:
    st = next((e for e in schedule.entries if e.troop.name == name and e.activity.name == 'Super Troop'), None)
    delta = next((e for e in schedule.entries if e.troop.name == name and e.activity.name == 'Delta'), None)
    st_slot = st.time_slot if st else 'N/A'
    delta_slot = delta.time_slot if delta else 'N/A'
    print(f'{name}: Super Troop at {st_slot}, Delta at {delta_slot}')

# Check ODS clustering
print('\n=== ODS CLUSTERING ===')
ods_activities = ['Knots and Lashings', 'Orienteering', 'GPS & Geocaching', 'Ultimate Survivor']
ods_entries = [e for e in schedule.entries if e.activity.name in ods_activities]
by_day = {}
for e in ods_entries:
    day = e.time_slot.day.name
    if day not in by_day:
        by_day[day] = []
    by_day[day].append(f'{e.troop.name}: {e.activity.name} (S{e.time_slot.slot_number})')

for day in ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY']:
    if day in by_day:
        print(f'{day}: {len(by_day[day])} activities')
        for item in by_day[day]:
            print(f'  - {item}')

# Check if Samoset has any ODS activities and what slot they're in
print('\n=== SAMOSET ODS ACTIVITIES ===')
samoset_ods = [e for e in schedule.entries if e.troop.name == 'Samoset' and e.activity.name in ods_activities]
for e in samoset_ods:
    print(f'{e.time_slot}: {e.activity.name}')

# Check what ODS activities Samoset has in their preferences
print('\n=== SAMOSET ODS PREFERENCES ===')
for i, pref in enumerate(samoset.preferences):
    if pref in ods_activities:
        print(f'Pref #{i+1}: {pref}')
