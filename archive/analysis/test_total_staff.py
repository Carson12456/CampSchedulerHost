from io_handler import load_troops_from_json
from constrained_scheduler import ConstrainedScheduler
from models import Day

troops = load_troops_from_json('tc_week7_troops.json')
scheduler = ConstrainedScheduler(troops)
schedule = scheduler.schedule_all()

# All staffed activities
BEACH_STAFFED = ['Aqua Trampoline', 'Troop Canoe', 'Troop Kayak', 'Canoe Snorkel',
                 'Float for Floats', 'Greased Watermelon', 'Underwater Obstacle Course',
                 'Troop Swim', 'Water Polo']
ALL_STAFFED = (BEACH_STAFFED + 
               ['Sailing', 'Troop Rifle', 'Troop Shotgun', 'Archery/Tomahawks/Slingshots',
                'Climbing Tower', 'Orienteering', 'GPS & Geocaching', 'Knots and Lashings',
                'Ultimate Survivor', 'Back of the Moon', 'Loon Lore', 'Dr. DNA', 'Nature Canoe',
                'Tie Dye', 'Hemp Craft', 'Woggle Neckerchief Slide', "Monkey's Fist",
                'Reflection', 'Delta', 'Super Troop'])

print('\nTOTAL STAFF PER SLOT (all activities):')
max_staff = 0
for day in [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.THURSDAY, Day.FRIDAY]:
    for slot_num in [1, 2, 3]:
        if day == Day.THURSDAY and slot_num == 3:
            continue
        
        staff_count = 0
        for e in schedule.entries:
            if e.time_slot.day == day and e.time_slot.slot_number == slot_num and e.activity.name in ALL_STAFFED:
                if e.activity.name in BEACH_STAFFED:
                    staff_count += 2
                else:
                    staff_count += 1
        
        if staff_count > max_staff:
            max_staff = staff_count
        
        status = 'OK' if staff_count <= 12 else '*** OVER 12! ***'
        if staff_count >= 10:
            print(f'{day.name[:3]}-{slot_num}: {staff_count:2d} staff  {status}')

print(f'\nMAX total staff in any slot: {max_staff}')
if max_staff <= 12:
    print('✓ All slots within 12 staff limit!')
else:
    print('✗ EXCEEDS 12 staff limit!')
