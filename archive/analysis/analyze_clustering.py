"""Analyze staff area clustering efficiency."""
from constrained_scheduler import ConstrainedScheduler
from io_handler import load_troops_from_json
from pathlib import Path
from models import Day
from collections import defaultdict

troops = load_troops_from_json(Path('tc_week5_troops.json'))
scheduler = ConstrainedScheduler(troops)
schedule = scheduler.schedule_all()

# Measure staff area clustering
STAFF_AREAS = {
    'Tower': ['Climbing Tower'],
    'ODS': ['Knots and Lashings', 'Orienteering', 'GPS & Geocaching', 'Ultimate Survivor', 
            'Leave No Trace', "What's Cooking", 'Chopped!', "Firem'n Chit/Totin' Chip"],
    'Rifle': ['Troop Rifle', 'Troop Shotgun'],
    'Archery': ['Archery/Tomahawks/Slingshots']
}

print('\n=== CURRENT STAFF CLUSTERING ANALYSIS ===')
for area_name, activities in STAFF_AREAS.items():
    # Count activities per day
    by_day = defaultdict(list)
    for entry in schedule.entries:
        if entry.activity.name in activities:
            by_day[entry.time_slot.day.name].append(f'{entry.troop.name} S{entry.time_slot.slot_number}')
    
    days_used = len([d for d in by_day if len(by_day[d]) > 0])
    total_activities = sum(len(v) for v in by_day.values())
    
    print(f'\n{area_name}: {total_activities} activities across {days_used} days')
    for day in ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY']:
        if by_day[day]:
            print(f'  {day}: {len(by_day[day])} - {by_day[day]}')

# Calculate clustering score: fewer days = better
print('\n=== CLUSTERING EFFICIENCY ===')
for area_name, activities in STAFF_AREAS.items():
    by_day = defaultdict(int)
    for entry in schedule.entries:
        if entry.activity.name in activities:
            by_day[entry.time_slot.day.name] += 1
    
    total = sum(by_day.values())
    days_used = len([d for d in by_day if by_day[d] > 0])
    if total > 0:
        efficiency = total / days_used if days_used > 0 else 0
        print(f'{area_name}: {total} activities / {days_used} days = {efficiency:.1f} per day')
