from io_handler import load_troops_from_json
from constrained_scheduler import ConstrainedScheduler
from models import Day
import json

print("="*70)
print("WEEK 5 COMPREHENSIVE ANALYSIS")
print("="*70)

troops = load_troops_from_json('tc_week5_troops.json')
scheduler = ConstrainedScheduler(troops)
schedule = scheduler.schedule_all()

# ============================================================
# 1. TROOP INFO
# ============================================================
print("\n" + "="*70)
print("1. TROOPS OVERVIEW")
print("="*70)
total_scouts = sum(t.scouts for t in troops)
total_adults = sum(t.adults for t in troops)
print(f"Total troops: {len(troops)}")
print(f"Total scouts: {total_scouts}")
print(f"Total adults: {total_adults}")
print(f"Total people: {total_scouts + total_adults}")

for t in troops:
    print(f"  {t.name}: {t.scouts}/{t.adults}")

# ============================================================
# 2. PREFERENCE SATISFACTION
# ============================================================
print("\n" + "="*70)
print("2. PREFERENCE SATISFACTION")
print("="*70)

all_top5 = 0
all_top10 = 0
for troop in troops:
    entries = [e for e in schedule.entries if e.troop == troop]
    top5 = sum(1 for e in entries if troop.get_priority(e.activity.name) <= 5)
    top10 = sum(1 for e in entries if troop.get_priority(e.activity.name) <= 10)
    all_top5 += top5
    all_top10 += top10
    print(f"{troop.name}: Top5={top5}/5, Top10={top10}/10")

print(f"\nAVERAGE: Top5={all_top5/len(troops):.1f}/5, Top10={all_top10/len(troops):.1f}/10")

# ============================================================
# 3. STAFF UTILIZATION
# ============================================================
print("\n" + "="*70)
print("3. STAFF UTILIZATION")
print("="*70)

BEACH_STAFFED = ['Aqua Trampoline', 'Troop Canoe', 'Troop Kayak', 'Canoe Snorkel',
                 'Float for Floats', 'Greased Watermelon', 'Underwater Obstacle Course',
                 'Troop Swim', 'Water Polo']

staff_by_slot = {}
extra_needed = {}

for day in [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.THURSDAY, Day.FRIDAY]:
    for slot_num in [1, 2, 3]:
        if day == Day.THURSDAY and slot_num == 3:
            continue
        
        staff = 0
        beach_troops = []
        tower_troops = []
        
        for e in schedule.entries:
            if e.time_slot.day == day and e.time_slot.slot_number == slot_num:
                people = e.troop.scouts + e.troop.adults
                if e.activity.name in BEACH_STAFFED:
                    staff += 2
                    beach_troops.append(people)
                elif e.activity.name == 'Climbing Tower':
                    staff += 2
                    tower_troops.append(people)
                elif e.activity.name in ['Sailing', 'Troop Rifle', 'Troop Shotgun', 
                                         'Archery/Tomahawks/Slingshots', 'Reflection', 
                                         'Delta', 'Super Troop']:
                    staff += 1
        
        # Calculate extra needed
        extra = 0
        for p in beach_troops:
            if p > 20:
                extra += (p - 20 + 9) // 10
        for p in tower_troops:
            if p > 12:
                extra += (p - 12 + 5) // 6
        
        key = f"{day.name[:3]}-{slot_num}"
        staff_by_slot[key] = staff
        extra_needed[key] = extra
        
        if staff >= 10 or extra > 0:
            extra_str = f" (+{extra} extra)" if extra > 0 else ""
            print(f"{key}: {staff} staff{extra_str}")

max_staff = max(staff_by_slot.values())
total_extra = sum(extra_needed.values())
print(f"\nMax staff in any slot: {max_staff}")
print(f"Total extra staff recommended: {total_extra}")

# ============================================================
# 4. AREA CLUSTERING
# ============================================================
print("\n" + "="*70)
print("4. AREA CLUSTERING")
print("="*70)

areas = {
    'Archery': ['Archery/Tomahawks/Slingshots'],
    'Rifle Range': ['Troop Rifle', 'Troop Shotgun'],
    'Tower': ['Climbing Tower'],
    'ODS': ['Orienteering', 'GPS & Geocaching', 'Knots and Lashings', 'Ultimate Survivor'],
}

for area, activities in areas.items():
    days_used = {}
    for day in [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.THURSDAY, Day.FRIDAY]:
        count = len([e for e in schedule.entries 
                    if e.activity.name in activities and e.time_slot.day == day])
        if count > 0:
            days_used[day.name[:3]] = count
    
    days_active = len(days_used)
    total = sum(days_used.values())
    clustering_score = "GOOD" if days_active <= 2 else "FAIR" if days_active <= 3 else "SPREAD"
    print(f"{area}: {total} activities across {days_active} days [{clustering_score}]")
    print(f"  {days_used}")

# ============================================================
# 5. COMMISSIONER BALANCE
# ============================================================
print("\n" + "="*70)
print("5. COMMISSIONER BALANCE")
print("="*70)

COMMISSIONER_TROOPS = {
    "A": ["Tecumseh", "Red Cloud", "Massasoit", "Joseph"],
    "B": ["Tamanend", "Samoset", "Black Hawk"],
    "C": ["Taskalusa", "Powhatan", "Cochise"]
}

for comm, troop_list in COMMISSIONER_TROOPS.items():
    comm_troops_present = [t for t in troop_list if any(tr.name == t for tr in troops)]
    activities = len([e for e in schedule.entries 
                     if e.troop.name in comm_troops_present 
                     and e.activity.name in ['Delta', 'Super Troop', 'Reflection']])
    print(f"Commissioner {comm}: {len(comm_troops_present)} troops, {activities} commissioner activities")

print("\n" + "="*70)
print("ANALYSIS COMPLETE")
print("="*70)
