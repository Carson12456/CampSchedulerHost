"""Check missed Top 5 activities from schedule JSON files."""
import json
import glob
from pathlib import Path

schedule_files = sorted(glob.glob("schedules/*_schedule.json"))

print("=" * 80)
print("MISSED TOP 5 ACTIVITIES BY WEEK")
print("=" * 80)

total_misses = 0
weeks_with_misses = []

for schedule_file in schedule_files:
    with open(schedule_file, 'r') as f:
        data = json.load(f)
    
    week_name = Path(schedule_file).stem.replace("_schedule", "")
    unscheduled = data.get('unscheduled', {})
    
    week_misses = []
    for troop_name, troop_data in unscheduled.items():
        top5_misses = troop_data.get('top5', [])
        if top5_misses:
            for miss in top5_misses:
                week_misses.append({
                    'troop': troop_name,
                    'activity': miss['name'],
                    'rank': miss['rank'],
                    'is_exempt': miss.get('is_exempt', False)
                })
                total_misses += 1
    
    if week_misses:
        weeks_with_misses.append((week_name, week_misses))
        print(f"\n{week_name}:")
        print(f"  Total Top 5 Misses: {len(week_misses)}")
        for miss in week_misses:
            exempt_str = " (EXEMPT)" if miss['is_exempt'] else ""
            print(f"    - {miss['troop']}: {miss['activity']} (Rank #{miss['rank']}){exempt_str}")

if not weeks_with_misses:
    print("\n✓ NO MISSED TOP 5 ACTIVITIES - All weeks have 100% Top 5 satisfaction!")
else:
    print(f"\n" + "=" * 80)
    print(f"SUMMARY: {total_misses} total Top 5 misses across {len(weeks_with_misses)} week(s)")
    print("=" * 80)
