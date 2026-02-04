from io_handler import load_troops_from_json
from constrained_scheduler import ConstrainedScheduler
from models import Day

troops = load_troops_from_json('tc_week7_troops.json')
scheduler = ConstrainedScheduler(troops)
schedule = scheduler.schedule_all()

print('\n=== COMMISSIONER A TROOPS ===')
comm_a = ['Red Cloud', 'Massasoit', 'Joseph', 'Tecumseh']
for name in comm_a:
    delta = next((e for e in schedule.entries if e.troop.name == name and e.activity.name == 'Delta'), None)
    super_t = next((e for e in schedule.entries if e.troop.name == name and e.activity.name == 'Super Troop'), None)
    
    delta_str = str(delta.time_slot) if delta else 'N/A'
    super_str = str(super_t.time_slot) if super_t else 'N/A'
    same = delta and super_t and delta.time_slot.day == super_t.time_slot.day
    
    print(f'{name:12} Delta: {delta_str:8}  Super: {super_str:8}  {"[SAME DAY]" if same else ""}')

print(f'\nFriday Super Troops: {len([e for e in schedule.entries if e.activity.name == "Super Troop" and e.time_slot.day == Day.FRIDAY])}')
