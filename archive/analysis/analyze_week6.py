from io_handler import load_troops_from_json
from constrained_scheduler import ConstrainedScheduler
from models import Day

print("\n" + "="*70)
print("WEEK 6 COMPREHENSIVE SCHEDULE ANALYSIS")
print("="*70)

troops = load_troops_from_json('tc_week6_troops.json')
scheduler = ConstrainedScheduler(troops)
schedule = scheduler.schedule_all()

# ============================================================
# 1. PREFERENCE SATISFACTION ANALYSIS
# ============================================================
print("\n" + "="*70)
print("1. PREFERENCE SATISFACTION")
print("="*70)

for troop in troops:
    entries = [e for e in schedule.entries if e.troop == troop]
    
    top5_count = sum(1 for e in entries if troop.get_priority(e.activity.name) <= 5)
    top10_count = sum(1 for e in entries if troop.get_priority(e.activity.name) <= 10)
    total_scheduled = len(entries)
    
    print(f"\n{troop.name} ({troop.scouts}/{troop.adults}):")
    print(f"  Top 5 achieved: {top5_count}/5")
    print(f"  Top 10 achieved: {top10_count}/10")
    print(f"  Total activities: {total_scheduled}")

# ============================================================
# 2. AREA BLOCKING & CLUSTERING ANALYSIS
# ============================================================
print("\n" + "="*70)
print("2. AREA BLOCKING & CLUSTERING")
print("="*70)

# Count activities per area per day
area_map = {
    'Beach': ['Aqua Trampoline', 'Troop Canoe', 'Troop Kayak', 'Canoe Snorkel',
              'Float for Floats', 'Greased Watermelon', 'Underwater Obstacle Course',
              'Troop Swim', 'Water Polo', 'Sauna', 'Fishing'],
    'Sailing': ['Sailing'],
    'Rifle Range': ['Troop Rifle', 'Troop Shotgun'],
    'Archery': ['Archery/Tomahawks/Slingshots'],
    'Tower/Climbing': ['Climbing Tower'],
    'Outdoor Skills': ['Orienteering', 'GPS & Geocaching', 'Knots and Lashings',
                       'Ultimate Survivor', 'Back of the Moon'],
    'Handicrafts': ['Tie Dye', 'Hemp Craft', 'Woggle Neckerchief Slide', "Monkey's Fist"],
    'Nature': ['Loon Lore', 'Dr. DNA', 'Nature Canoe'],
}

for area, activities in area_map.items():
    print(f"\n{area} Area:")
    for day in [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.THURSDAY, Day.FRIDAY]:
        day_activities = [e for e in schedule.entries 
                         if e.activity.name in activities and e.time_slot.day == day]
        if day_activities:
            troops_with_activity = set(e.troop.name for e in day_activities)
            print(f"  {day.name[:3]}: {len(troops_with_activity)} troops")

# ============================================================
# 3. STAFF UTILIZATION ANALYSIS
# ============================================================
print("\n" + "="*70)
print("3. STAFF UTILIZATION PER SLOT")
print("="*70)

BEACH_STAFFED = ['Aqua Trampoline', 'Troop Canoe', 'Troop Kayak', 'Canoe Snorkel',
                 'Float for Floats', 'Greased Watermelon', 'Underwater Obstacle Course',
                 'Troop Swim', 'Water Polo']
ALL_STAFFED = (BEACH_STAFFED + 
               ['Sailing', 'Troop Rifle', 'Troop Shotgun', 'Archery/Tomahawks/Slingshots',
                'Climbing Tower', 'Orienteering', 'GPS & Geocaching', 'Knots and Lashings',
                'Ultimate Survivor', 'Back of the Moon', 'Loon Lore', 'Dr. DNA', 'Nature Canoe',
                'Tie Dye', 'Hemp Craft', 'Woggle Neckerchief Slide', "Monkey's Fist",
                'Reflection', 'Delta', 'Super Troop'])

max_staff = 0
staff_distribution = {}

for day in [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.THURSDAY, Day.FRIDAY]:
    for slot_num in [1, 2, 3]:
        if day == Day.THURSDAY and slot_num == 3:
            continue
        
        staff_count = 0
        for e in schedule.entries:
            if e.time_slot.day == day and e.time_slot.slot_number == slot_num and e.activity.name in ALL_STAFFED:
                if e.activity.name in BEACH_STAFFED:
                    staff_count += 2
                elif e.activity.name == 'Climbing Tower':
                    staff_count += 2
                else:
                    staff_count += 1
        
        if staff_count > max_staff:
            max_staff = staff_count
        
        staff_distribution[staff_count] = staff_distribution.get(staff_count, 0) + 1
        
        if staff_count >= 10:
            status = 'HIGH' if staff_count > 12 else 'OK'
            print(f"{day.name[:3]}-{slot_num}: {staff_count:2d} staff  [{status}]")

print(f"\nMax staff in any slot: {max_staff}")
print(f"Staff distribution: {dict(sorted(staff_distribution.items()))}")

# ============================================================
# 4. COMMISSIONER WORKLOAD BALANCE
# ============================================================
print("\n" + "="*70)
print("4. COMMISSIONER WORKLOAD BALANCE")
print("="*70)

COMMISSIONER_TROOPS = {
    "Commissioner A": ["Tecumseh", "Red Cloud", "Massasoit", "Joseph"],
    "Commissioner B": ["Tamanend", "Samoset", "Black Hawk"],
    "Commissioner C": ["Taskalusa", "Powhatan", "Cochise"]
}

comm_activities = ['Reflection', 'Delta', 'Super Troop']

for comm, troop_list in COMMISSIONER_TROOPS.items():
    print(f"\n{comm}:")
    # Count how many commissioner activities per day
    for day in [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.THURSDAY, Day.FRIDAY]:
        day_count = len([e for e in schedule.entries 
                        if e.activity.name in comm_activities 
                        and e.troop.name in troop_list
                        and e.time_slot.day == day])
        if day_count > 0:
            print(f"  {day.name[:3]}: {day_count} activities")

print("\n" + "="*70)
print("ANALYSIS COMPLETE")
print("="*70)
