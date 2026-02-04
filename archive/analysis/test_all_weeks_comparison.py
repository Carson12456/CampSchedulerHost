"""
Compare baseline vs smart Reflection across all weeks
Focus on commissioner attendance and preference metrics
"""
from io_handler import load_troops_from_json
from constrained_scheduler import ConstrainedScheduler
from collections import defaultdict

def analyze_commissioner_attendance(schedule, scheduler):
    """Check how many commissioners can attend all their troops' Reflections"""
    commissioner_reflections = defaultdict(list)
    
    for entry in schedule.entries:
        if entry.activity.name == "Reflection":
            troop_name = entry.troop.name
            commissioner = scheduler.troop_commissioner.get(troop_name, "Unknown")
            slot_num = entry.time_slot.slot_number
            commissioner_reflections[commissioner].append((troop_name, slot_num))
    
    can_attend_all = 0
    total_commissioners = len(commissioner_reflections)
    
    for commissioner, reflections in commissioner_reflections.items():
        slots_used = set(slot for _, slot in reflections)
        if len(slots_used) == 1:
            can_attend_all += 1
    
    return can_attend_all, total_commissioners

def analyze_schedule(schedule, scheduler):
    reflection_count = sum(1 for e in schedule.entries if e.activity.name == "Reflection")
    
    top5 = 0
    top10 = 0
    for troop in scheduler.troops:
        entries = [e for e in schedule.entries if e.troop.name == troop.name]
        scheduled_names = {e.activity.name for e in entries}
        
        for pref in troop.preferences[:5]:
            if pref in scheduled_names:
                top5 += 1
        
        for pref in troop.preferences[:10]:
            if pref in scheduled_names:
                top10 += 1
    
    total_troops = len(scheduler.troops)
    comm_ok, comm_total = analyze_commissioner_attendance(schedule, scheduler)
    
    return {
        'reflection_count': reflection_count,
        'top5': top5,
        'top5_pct': top5/(total_troops*5)*100,
        'top10': top10,
        'top10_pct': top10/(total_troops*10)*100,
        'total_troops': total_troops,
        'comm_ok': comm_ok,
        'comm_total': comm_total,
        'comm_pct': comm_ok/comm_total*100 if comm_total > 0 else 0
    }

# First, test BASELINE (need to temporarily revert code)
print("="*70)
print("COMPARING BASELINE VS SMART REFLECTION")
print("="*70)
print("\nNOTE: Testing smart approach (baseline would require code revert)")

weeks = [
    ('tc_week5_troops.json', 'Week 5'),
    ('tc_week6_troops.json', 'Week 6'),
    ('tc_week7_troops.json', 'Week 7')
]

results = {}

for troops_file, week_name in weeks:
    print(f"\n{'='*70}")
    print(f"{week_name} - SMART REFLECTION APPROACH")
    print('='*70)
    
    troops = load_troops_from_json(troops_file)
    scheduler = ConstrainedScheduler(troops)
    schedule = scheduler.schedule_all()
    
    metrics = analyze_schedule(schedule, scheduler)
    results[week_name] = metrics
    
    print(f"\n{week_name} Results:")
    print(f"  Reflections: {metrics['reflection_count']}/{metrics['total_troops']}")
    print(f"  Top 5: {metrics['top5']}/{metrics['total_troops']*5} ({metrics['top5_pct']:.1f}%)")
    print(f"  Top 10: {metrics['top10']}/{metrics['total_troops']*10} ({metrics['top10_pct']:.1f}%)")
    print(f"  Commissioner Attendance: {metrics['comm_ok']}/{metrics['comm_total']} ({metrics['comm_pct']:.0f}%)")

print("\n" + "="*70)
print("SUMMARY - SMART REFLECTION APPROACH")
print("="*70)

print("\n{:12} {:12} {:12} {:12} {:20}".format("Week", "Reflections", "Top 5", "Top 10", "Comm Attendance"))
print("-"*70)
for week_name in ['Week 5', 'Week 6', 'Week 7']:
    m = results[week_name]
    print("{:12} {:12} {:12} {:12} {:20}".format(
        week_name,
        f"{m['reflection_count']}/{m['total_troops']}",
        f"{m['top5_pct']:.1f}%",
        f"{m['top10_pct']:.1f}%",
        f"{m['comm_ok']}/{m['comm_total']} ({m['comm_pct']:.0f}%)"
    ))

print("\n" + "="*70)
print("BASELINE COMPARISON (from previous tests)")
print("="*70)
print("\n{:12} {:12} {:12} {:12} {:20}".format("Week", "Reflections", "Top 5", "Top 10", "Comm Attendance"))
print("-"*70)
print("{:12} {:12} {:12} {:12} {:20}".format("Week 7", "11/11", "98.2%", "87.3%", "~100% (estimated)"))
print("\nNote: Baseline explicitly clusters by commissioner, so attendance is typically 100%")
