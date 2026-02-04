#!/usr/bin/env python3
"""
Debug web interface week data issue
"""

from gui_web import WEEK_METADATA, get_week_data

print('Web Interface Week Metadata:')
for week_id, meta in WEEK_METADATA.items():
    print(f'  {week_id}: {meta["week_number"]}')

print('\nChecking week data loading...')
try:
    tc_week3_data = get_week_data('tc_week3_troops')
    if tc_week3_data:
        print(f'TC Week 3 troops: {len(tc_week3_data["troops"])}')
        for troop in tc_week3_data['troops'][:3]:
            print(f'  - {troop.name} (Commissioner: {troop.commissioner})')
    else:
        print('TC Week 3 data is None')
        
    voyageur_week3_data = get_week_data('voyageur_week3_troops')
    if voyageur_week3_data:
        print(f'Voyageur Week 3 troops: {len(voyageur_week3_data["troops"])}')
        for troop in voyageur_week3_data['troops'][:3]:
            print(f'  - {troop.name} (Commissioner: {troop.commissioner})')
    else:
        print('Voyageur Week 3 data is None')
        
except Exception as e:
    print(f'Error checking week data: {e}')
    import traceback
    traceback.print_exc()

# Check schedule files
print('\nChecking schedule files:')
import os
tc_schedule = 'schedules/tc_week3_troops_schedule.json'
voyageur_schedule = 'schedules/voyageur_week3_troops_schedule.json'

if os.path.exists(tc_schedule):
    print(f'TC Week 3 schedule exists: {os.path.getsize(tc_schedule)} bytes')
else:
    print('TC Week 3 schedule missing')

if os.path.exists(voyageur_schedule):
    print(f'Voyageur Week 3 schedule exists: {os.path.getsize(voyageur_schedule)} bytes')
else:
    print('Voyageur Week 3 schedule missing')
