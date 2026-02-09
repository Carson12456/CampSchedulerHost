import json

data = json.load(open('data/schedules/tc_week3_troops_schedule.json'))
entries = data['entries']

multislot3 = ['Tamarac Wildlife Refuge', 'Itasca State Park', 'Back of the Moon']
multislot2 = ['Sailing', 'Canoe Snorkel', 'Float for Floats']

counts = {}
for e in entries:
    activity = e['activity_name']
    if activity in multislot3 + multislot2:
        key = (e['troop_name'], activity)
        if key not in counts:
            counts[key] = []
        counts[key].append((e['day'], e['slot']))

print('Multi-slot activities in tc_week3_troops:')
print('-' * 60)
for (troop, activity), slots in sorted(counts.items()):
    expected = 3 if activity in multislot3 else 2
    status = 'OK' if len(slots) == expected else 'ISSUE'
    print(f'{status:5} | {troop:15} | {activity:25} | slots: {len(slots)}/{expected}')
    if status == 'ISSUE':
        print(f'       Scheduled slots: {slots}')
