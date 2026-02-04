from io_handler import load_troops_from_json
from constrained_scheduler import ConstrainedScheduler
from models import Day

troops = load_troops_from_json('tc_week6_troops.json')
scheduler = ConstrainedScheduler(troops)
schedule = scheduler.schedule_all()

CANOE = ['Nature Canoe', 'Canoe Snorkel', 'Float for Floats', 'Troop Canoe']

print('\nCANOE CAPACITY CHECK (Max 26 people per slot):')
print('='*60)

max_people = 0
for day in [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.THURSDAY, Day.FRIDAY]:
    for slot_num in [1, 2, 3]:
        if day == Day.THURSDAY and slot_num == 3:
            continue
        
        people = 0
        activities = []
        for e in schedule.entries:
            if e.time_slot.day == day and e.time_slot.slot_number == slot_num and e.activity.name in CANOE:
                people += e.troop.scouts
                activities.append(f'{e.troop.name}({e.troop.scouts})')
        
        if people > max_people:
            max_people = people
        
        if people > 0:
            status = 'OVER!' if people > 26 else 'OK'
            print(f'{day.name[:3]}-{slot_num}: {people:2d} people  [{status}]')
            if people > 20:
                print(f'         {activities}')

print(f'\nMax people in canoes (any slot): {max_people}/26')
if max_people <= 26:
    print('OK - All slots within canoe capacity!')
else:
    print('ERROR - EXCEEDS canoe capacity!')
