"""Full analysis of Week 7 schedule quality and troop size handling."""
from constrained_scheduler import ConstrainedScheduler
from io_handler import load_troops_from_json
from activities import get_all_activities
from models import Day

def analyze_week7():
    troops = load_troops_from_json('tc_week7_troops.json')
    
    print("=" * 70)
    print("WEEK 7 FULL SCHEDULE ANALYSIS")
    print("=" * 70)
    
    # 1. Troop Size Summary
    print("\n1. TROOP SIZE SUMMARY")
    print("-" * 40)
    sizes = {'Small': [], 'Medium': [], 'Large': [], 'Split': []}
    for t in sorted(troops, key=lambda x: x.scouts, reverse=True):
        cat = t.size_category
        if cat == 'Extra Small':
            cat = 'Small'
        sizes.get(cat, sizes['Small']).append(t)
        print(f"  {t.name:12} {t.scouts:2}s/{t.adults}a ({t.size_category})")
    
    print(f"\n  Distribution: Small={len(sizes['Small'])}, Medium={len(sizes['Medium'])}, Large={len(sizes['Large'])}, Split={len(sizes['Split'])}")
    
    # 2. Run Scheduler
    print("\n2. RUNNING SCHEDULER...")
    print("-" * 40)
    scheduler = ConstrainedScheduler(troops)
    schedule = scheduler.schedule_all()
    
    # 3. Preference Satisfaction
    print("\n3. PREFERENCE SATISFACTION")
    print("-" * 40)
    total_top5 = 0
    total_top10 = 0
    
    for troop in troops:
        entries = [e for e in schedule.entries if e.troop == troop]
        top5 = sum(1 for e in entries if troop.get_priority(e.activity.name) < 5)
        top10 = sum(1 for e in entries if troop.get_priority(e.activity.name) < 10)
        total_top5 += min(top5, 5)
        total_top10 += min(top10, 10)
        
        missing = [p for i, p in enumerate(troop.preferences[:5]) 
                   if not any(e.activity.name == p for e in entries)]
        
        status = "OK" if top5 >= 5 else "!!"
        print(f"  {status} {troop.name:12} ({troop.size_category:6}): Top5={top5}/5, Top10={top10}/10" + 
              (f" Missing: {missing}" if missing else ""))
    
    print(f"\n  Overall: Top5={total_top5}/{len(troops)*5} ({total_top5*100//(len(troops)*5)}%), " +
          f"Top10={total_top10}/{len(troops)*10} ({total_top10*100//(len(troops)*10)}%)")
    
    # 4. Activity Capacity Check (same time slot conflicts)
    print("\n4. ACTIVITY SLOT CONFLICTS (Multiple troops same slot)")
    print("-" * 40)
    slot_usage = {}
    for entry in schedule.entries:
        key = (entry.time_slot.day.name, entry.time_slot.slot_number, entry.activity.name)
        if key not in slot_usage:
            slot_usage[key] = []
        slot_usage[key].append((entry.troop.name, entry.troop.scouts))
    
    conflicts = []
    for key, troops_list in slot_usage.items():
        if len(troops_list) > 1:
            day, slot, activity = key
            total_scouts = sum(t[1] for t in troops_list)
            conflicts.append((day, slot, activity, troops_list, total_scouts))
    
    if conflicts:
        for day, slot, activity, troops_list, total in sorted(conflicts):
            troop_names = ", ".join(f"{t[0]}({t[1]}s)" for t in troops_list)
            print(f"  {day[:3]}-{slot} {activity}: {troop_names} = {total} scouts")
    else:
        print("  No multi-troop slots found")
    
    # 5. Large Troop Handling
    print("\n5. LARGE TROOP SCHEDULING")
    print("-" * 40)
    large_troops = [t for t in troops if t.scouts >= 16]
    for troop in large_troops:
        entries = [e for e in schedule.entries if e.troop == troop]
        print(f"  {troop.name} ({troop.scouts} scouts):")
        
        # Check for exclusive activities
        exclusive = ['Climbing Tower', 'Troop Rifle', 'Troop Shotgun', 'Sailing']
        for activity in exclusive:
            has_it = any(e.activity.name == activity for e in entries)
            if has_it:
                entry = next(e for e in entries if e.activity.name == activity)
                # Check if sharing slot
                same_slot = [e for e in schedule.entries 
                            if e.time_slot == entry.time_slot 
                            and e.activity.name == activity 
                            and e.troop != troop]
                if same_slot:
                    other = same_slot[0].troop
                    print(f"    !! {activity}: Sharing with {other.name} ({other.scouts}s)")
                else:
                    print(f"    OK {activity}: Exclusive slot")
    
    # 6. Staff Day Clustering
    print("\n6. STAFF AREA CLUSTERING")
    print("-" * 40)
    staff_areas = {
        'Tower': ['Climbing Tower'],
        'Rifle Range': ['Troop Rifle', 'Troop Shotgun'],
        'Archery': ['Archery/Tomahawks/Slingshots']
    }
    
    for area, activities in staff_areas.items():
        days_used = set()
        for entry in schedule.entries:
            if entry.activity.name in activities:
                days_used.add(entry.time_slot.day.name)
        print(f"  {area}: {len(days_used)} days - {', '.join(sorted(days_used))}")
    
    # 7. Commissioner Day Compliance
    print("\n7. COMMISSIONER DAY COMPLIANCE")
    print("-" * 40)
    commissioner_days = {
        'Commissioner A': Day.TUESDAY,
        'Commissioner B': Day.WEDNESDAY,
        'Commissioner C': Day.THURSDAY
    }
    
    for comm, expected_day in commissioner_days.items():
        comm_troops = [t for t in troops if t.commissioner == comm]
        print(f"  {comm} (expected: {expected_day.name}):")
        
        for troop in comm_troops:
            entries = [e for e in schedule.entries if e.troop == troop]
            super_troop = next((e for e in entries if e.activity.name == 'Super Troop'), None)
            if super_troop:
                day = super_troop.time_slot.day.name
                status = "OK" if super_troop.time_slot.day == expected_day else "!! SPILLOVER"
                print(f"    {troop.name}: Super Troop on {day} {status}")
    
    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    analyze_week7()
