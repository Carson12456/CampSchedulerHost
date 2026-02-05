import json

data = json.load(open('schedules/tc_week5_troops_schedule.json'))
troops = {t['name']: t for t in data['troops']}
scheduled = {}
for e in data['entries']:
    if e['troop_name'] not in scheduled:
        scheduled[e['troop_name']] = set()
    scheduled[e['troop_name']].add(e['activity_name'])

print('Top 5 Status:')
for name in sorted(troops.keys()):
    top5 = troops[name]['preferences'][:5]
    scheduled_top5 = [p for p in top5 if p in scheduled.get(name, set())]
    missing = [p for p in top5 if p not in scheduled.get(name, set())]
    print(f"  {name}: {len(scheduled_top5)}/5 - Missing: {missing}")

print('\nTop 10 Status:')
for name in sorted(troops.keys()):
    top10 = troops[name]['preferences'][:10]
    scheduled_top10 = [p for p in top10 if p in scheduled.get(name, set())]
    print(f"  {name}: {len(scheduled_top10)}/10")
