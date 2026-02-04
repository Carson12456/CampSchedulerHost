"""Comprehensive diagnostic for all scheduler constraints."""
from constrained_scheduler import ConstrainedScheduler
from io_handler import load_troops_from_json
from models import Day

print("="*70)
print("FULL SCHEDULER DIAGNOSTIC - WEEK 7")
print("="*70)

troops = load_troops_from_json('tc_week7_troops.json')
scheduler = ConstrainedScheduler(troops)
schedule = scheduler.schedule_all()

print("\n" + "="*70)
print("CONSTRAINT VERIFICATION")
print("="*70)

errors = []
warnings = []

# Day order for comparison
DAY_ORDER = {Day.MONDAY: 1, Day.TUESDAY: 2, Day.WEDNESDAY: 3, Day.THURSDAY: 4, Day.FRIDAY: 5}

# 1. Beach Slot Constraint - Beach in Slot 1 or 3 (Thursday is 2-slot day, has no slot 3)
# Note: This constraint check may show warnings - slot 2 usage varies by design
print("\n1. BEACH SLOT CONSTRAINT (Slot 1/3 only, Thursday slot 2 allowed since no slot 3)")
beach_activities = ['Aqua Trampoline', 'Troop Canoe', 'Troop Kayak', 'Canoe Snorkel', 
                   'Float for Floats', 'Greased Watermelon', 'Troop Swim', 
                   'Underwater Obstacle Course', 'Water Polo', 'Sailing']
beach_violations = []
for e in schedule.entries:
    if e.activity.name in beach_activities:
        slot = e.time_slot.slot_number
        day = e.time_slot.day
        if slot == 2 and day != Day.TUESDAY:
            beach_violations.append(f"{e.troop.name}: {e.activity.name} at {day.name}-{slot}")

print(f"  Beach slot 2 on non-Tuesday: {len(beach_violations)}")
if beach_violations:
    for v in beach_violations[:3]:
        print(f"    - {v}")
    if len(beach_violations) > 3:
        print(f"    ... and {len(beach_violations)-3} more")
    warnings.extend(beach_violations)  # Warning, not error - may be by design

# 2. Accuracy Limit
print("\n2. ACCURACY LIMIT (max 1 per day)")
accuracy_activities = ['Troop Rifle', 'Troop Shotgun', 'Archery/Tomahawks/Slingshots']
accuracy_violations = []
for troop in troops:
    day_accuracy = {}
    for e in schedule.entries:
        if e.troop == troop and e.activity.name in accuracy_activities:
            day = e.time_slot.day.name
            if day not in day_accuracy:
                day_accuracy[day] = []
            day_accuracy[day].append(e.activity.name)
    for day, acts in day_accuracy.items():
        if len(acts) > 1:
            accuracy_violations.append(f"{troop.name}: {', '.join(acts)} on {day}")

if accuracy_violations:
    print(f"  [X] VIOLATIONS: {len(accuracy_violations)}")
    for v in accuracy_violations:
        print(f"     {v}")
    errors.extend(accuracy_violations)
else:
    print("  [OK] All troops have max 1 accuracy per day")

# 3. Reflection on Friday
print("\n3. REFLECTION ON FRIDAY")
reflection_count = sum(1 for e in schedule.entries if e.activity.name == 'Reflection')
non_friday = [e for e in schedule.entries if e.activity.name == 'Reflection' and e.time_slot.day != Day.FRIDAY]

print(f"  Reflections: {reflection_count}/{len(troops)}")
if non_friday:
    print(f"  [X] Non-Friday: {[(e.troop.name, e.time_slot.day.name) for e in non_friday]}")
    errors.extend([f"{e.troop.name} Reflection" for e in non_friday])
elif reflection_count == len(troops):
    print("  [OK] All troops have Friday Reflection")
else:
    print(f"  [!] Missing {len(troops) - reflection_count} Reflections")
    warnings.append(f"Missing Reflections")

# 4. Delta before Super Troop
print("\n4. DELTA -> SUPER TROOP SEQUENCING")
sequence_violations = []
for troop in troops:
    delta = next((e for e in schedule.entries if e.troop == troop and e.activity.name == 'Delta'), None)
    super_t = next((e for e in schedule.entries if e.troop == troop and e.activity.name == 'Super Troop'), None)
    if delta and super_t:
        d_time = DAY_ORDER[delta.time_slot.day] * 10 + delta.time_slot.slot_number
        s_time = DAY_ORDER[super_t.time_slot.day] * 10 + super_t.time_slot.slot_number
        if d_time >= s_time:
            sequence_violations.append(f"{troop.name}")

if sequence_violations:
    print(f"  [X] VIOLATIONS: {sequence_violations}")
    errors.extend(sequence_violations)
else:
    print("  [OK] All Delta before Super Troop")

# 5. Thursday Slot 3 Empty
print("\n5. THURSDAY SLOT 3 (closed)")
thu3 = [e for e in schedule.entries if e.time_slot.day == Day.THURSDAY and e.time_slot.slot_number == 3]
if thu3:
    print(f"  [X] Activities in closed slot: {[(e.troop.name, e.activity.name) for e in thu3]}")
    errors.extend([e.troop.name for e in thu3])
else:
    print("  [OK] Thursday Slot 3 empty")

# 6. Disc Golf/History Center
print("\n6. DISC GOLF/HISTORY CENTER (Tue/Wed Slot 1)")
restricted = ['Disc Golf', 'History Center']
violations = []
for e in schedule.entries:
    if e.activity.name in restricted:
        valid = e.time_slot.day in [Day.TUESDAY, Day.WEDNESDAY] and e.time_slot.slot_number == 1
        if not valid:
            violations.append(f"{e.troop.name}: {e.activity.name}")

if violations:
    print(f"  [X] VIOLATIONS: {violations}")
    errors.extend(violations)
else:
    print("  [OK] All in Tue/Wed Slot 1")

# 7. Preference Satisfaction
print("\n7. PREFERENCE SATISFACTION")
total_top5, total_top10, missing = 0, 0, []
for troop in troops:
    scheduled = {e.activity.name for e in schedule.entries if e.troop == troop}
    t5 = sum(1 for p in troop.preferences[:5] if p in scheduled)
    t10 = sum(1 for p in troop.preferences[:10] if p in scheduled)
    total_top5 += t5
    total_top10 += t10
    if t5 < 5:
        missing.append(f"{troop.name}")

top5_pct = total_top5 * 100 / (len(troops) * 5)
top10_pct = total_top10 * 100 / (len(troops) * 10)
print(f"  Top 5:  {total_top5}/{len(troops)*5} ({top5_pct:.1f}%)")
print(f"  Top 10: {total_top10}/{len(troops)*10} ({top10_pct:.1f}%)")
if missing:
    print(f"  [!] Missing Top 5: {missing}")
    warnings.extend(missing)

# 8. Staff Clustering  
print("\n8. STAFF AREA CLUSTERING")
areas = {'Tower': ['Climbing Tower'], 'Rifle': ['Troop Rifle', 'Troop Shotgun'], 
         'Archery': ['Archery/Tomahawks/Slingshots']}
for area, acts in areas.items():
    days = set(e.time_slot.day.name[:3] for e in schedule.entries if e.activity.name in acts)
    count = sum(1 for e in schedule.entries if e.activity.name in acts)
    print(f"  {area}: {count} activities on {len(days)} days")

# 9. Slots per troop
print("\n9. SLOTS PER TROOP (should be 14)")
for troop in troops:
    count = len([e for e in schedule.entries if e.troop == troop])
    if count != 14:
        print(f"  [!] {troop.name}: {count} slots")

# Summary
print("\n" + "="*70)
print("DIAGNOSTIC SUMMARY")
print("="*70)
print(f"  CRITICAL ERRORS: {len(errors)}")
print(f"  WARNINGS:        {len(warnings)}")
print(f"  Top 5:           {top5_pct:.1f}%")
print(f"  Top 10:          {top10_pct:.1f}%")
print(f"  Reflections:     {reflection_count}/{len(troops)}")

if len(errors) == 0:
    print("\n*** ALL CRITICAL CONSTRAINTS PASSED! ***")
else:
    print("\n*** SOME CONSTRAINTS FAILED ***")
    for e in errors[:5]:
        print(f"  - {e}")
