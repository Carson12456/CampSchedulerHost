"""Debug why Tower can't be scheduled for Skenandoa on Thursday."""
from constrained_scheduler import ConstrainedScheduler
from io_handler import load_troops_from_json
from pathlib import Path
from models import Day

troops = load_troops_from_json(Path('tc_week5_troops.json'))
skenandoa = [t for t in troops if t.name == 'Skenandoa'][0]

scheduler = ConstrainedScheduler(troops)
schedule = scheduler.schedule_all()

from activities import get_activity_by_name
tower = get_activity_by_name('Climbing Tower')

# Get Thursday slot 3 
thu_s3 = [s for s in scheduler.time_slots if s.day == Day.THURSDAY and s.slot_number == 3][0]

# Check individual constraints
print('=== Checking Tower constraints for Skenandoa Thu-3 ===')

# Is troop free?
free = schedule.is_troop_free(thu_s3, skenandoa)
print(f'1. Troop free: {free}')

# Activity available?
avail = schedule.is_activity_available(thu_s3, tower)
print(f'2. Activity available: {avail}')

# Check who has tower in Thu-3
tower_holders = [e.troop.name for e in schedule.entries if e.time_slot == thu_s3 and e.activity.name == 'Climbing Tower']
print(f'   Tower in Thu-3: {tower_holders}')

# Check wet before slot
wet_before = scheduler._has_wet_before_slot(skenandoa, thu_s3)
print(f'3. Wet before slot: {wet_before}')

# Who is in Thu-1 and Thu-2 for Skenandoa?
thu_s1 = [s for s in scheduler.time_slots if s.day == Day.THURSDAY and s.slot_number == 1][0]
thu_s2 = [s for s in scheduler.time_slots if s.day == Day.THURSDAY and s.slot_number == 2][0]

s1_activity = [e.activity.name for e in schedule.entries if e.time_slot == thu_s1 and e.troop.name == 'Skenandoa']
s2_activity = [e.activity.name for e in schedule.entries if e.time_slot == thu_s2 and e.troop.name == 'Skenandoa']
print(f'   Thu S1: {s1_activity}')
print(f'   Thu S2: {s2_activity}')

is_wet = "Aqua Trampoline" in scheduler.WET_ACTIVITIES
print(f'   Aqua Trampoline is WET: {is_wet}')

# Does troop have same area activity today?
same_area = scheduler._has_same_area_activity_today(skenandoa, tower, Day.THURSDAY)
print(f'4. Same area activity today: {same_area}')
