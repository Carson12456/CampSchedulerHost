from io_handler import load_troops_from_json
from constrained_scheduler import ConstrainedScheduler
from models import Day

troops = load_troops_from_json('tc_week7_troops.json')
scheduler = ConstrainedScheduler(troops)
schedule = scheduler.schedule_all()

# Check Roman Nose Tower
roman_nose = next(t for t in troops if t.name == 'Roman Nose')
roman_entries = sorted([e for e in schedule.entries if e.troop.name == 'Roman Nose'], 
                       key=lambda e: (e.time_slot.day.value, e.time_slot.slot_number))

print('ROMAN NOSE Schedule:')
for e in roman_entries:
    priority = roman_nose.get_priority(e.activity.name)
    print(f'{e.time_slot}: {e.activity.name} (Top {priority+1})')

# Count staff per slot
BEACH_STAFFED = ['Aqua Trampoline', 'Troop Canoe', 'Troop Kayak', 'Canoe Snorkel',
                 'Float for Floats', 'Greased Watermelon', 'Underwater Obstacle Course',
                 'Troop Swim', 'Water Polo']
ALL_STAFFED = (BEACH_STAFFED + 
               ['Sailing', 'Troop Rifle', 'Troop Shotgun', 'Archery/Tomahawks/Slingshots',
                'Climbing Tower', 'Orienteering', 'GPS & Geocaching', 'Knots and Lashings',
                'Ultimate Survivor', 'Back of the Moon', 'Loon Lore', 'Dr. DNA', 'Nature Canoe',
                'Tie Dye', 'Hemp Craft', 'Woggle Neckerchief Slide', "Monkey's Fist",
                'Reflection', 'Delta', 'Super Troop'])

print('\nSTAFF PER SLOT (>13 only):')
max_staff = 0
over_15 = []
for day in [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.THURSDAY, Day.FRIDAY]:
    for slot_num in [1, 2, 3]:
        if day == Day.THURSDAY and slot_num == 3:
            continue
        
        staff = 0
        for e in schedule.entries:
            if e.time_slot.day == day and e.time_slot.slot_number == slot_num and e.activity.name in ALL_STAFFED:
                if e.activity.name in BEACH_STAFFED:
                    staff += 2
                elif e.activity.name == 'Climbing Tower':
                    staff += 2
                else:
                    staff += 1
        
        if staff > max_staff:
            max_staff = staff
        
        if staff > 15:
            over_15.append(f'{day.name[:3]}-{slot_num}')
        
        if staff > 13:
            print(f'{day.name[:3]}-{slot_num}: {staff} staff')

print(f'\nMax staff: {max_staff}')
if over_15:
    print(f'Slots over 15: {", ".join(over_15)}')
else:
    print('No slots over 15!')
