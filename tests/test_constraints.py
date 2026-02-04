"""
Test suite for scheduling constraints validation.
Ensures all scheduling rules are properly enforced.
"""
import sys
sys.path.insert(0, '..')

from constrained_scheduler import ConstrainedScheduler
from activities import get_all_activities
from io_handler import load_troops_from_json
from models import Day

def test_beach_slot_constraint(schedule, troops):
    """Test: Beach activities in slot 1 or 3 (slot 2 on Tuesday only)."""
    violations = []
    BEACH_ACTIVITIES = ["Water Polo", "Greased Watermelon", "Aqua Trampoline"]
    
    for entry in schedule.entries:
        if entry.activity.name in BEACH_ACTIVITIES:
            day = entry.time_slot.day
            slot = entry.time_slot.slot_number
            
            # Tuesday allows slot 2, other days only 1 or 3
            if day == Day.TUESDAY:
                if slot not in [1, 2, 3]:
                    violations.append(f"{entry.troop.name}: {entry.activity.name} on {day.value} slot {slot}")
            else:
                if slot not in [1, 3]:
                    # Check if Top 5 preference (allowed exception)
                    pref_rank = entry.troop.get_priority(entry.activity.name) if hasattr(entry.troop, 'get_priority') else None
                    is_top5 = pref_rank is not None and pref_rank < 5
                    
                    if not is_top5:
                        violations.append(f"{entry.troop.name}: {entry.activity.name} on {day.value} slot {slot} (should be 1 or 3, Top 5 exception allowed)")
    
    return violations

def test_accuracy_limit(schedule, troops):
    """Test: Max 1 accuracy activity (Rifle/Shotgun/Archery) per troop per day."""
    violations = []
    ACCURACY_ACTIVITIES = ["Troop Rifle", "Troop Shotgun", "Archery"]
    
    for troop in troops:
        # Group by day
        day_activities = {}
        for entry in schedule.entries:
            if entry.troop == troop and entry.activity.name in ACCURACY_ACTIVITIES:
                day = entry.time_slot.day
                if day not in day_activities:
                    day_activities[day] = []
                # Avoid counting continuations
                if entry.activity.name not in day_activities[day]:
                    day_activities[day].append(entry.activity.name)
        
        # Check for violations
        for day, activities in day_activities.items():
            if len(activities) > 1:
                violations.append(f"{troop.name}: {len(activities)} accuracy activities on {day.value} ({', '.join(activities)})")
    
    return violations

def test_friday_reflection(schedule, troops):
    """Test: All troops must have Reflection on Friday."""
    violations = []
    
    for troop in troops:
        has_reflection = any(
            entry.activity.name == "Reflection" and entry.time_slot.day == Day.FRIDAY
            for entry in schedule.entries if entry.troop == troop
        )
        
        if not has_reflection:
            violations.append(f"{troop.name}: Missing Friday Reflection")
    
    return violations

def test_wet_before_tower_ods(schedule, troops):
    """Test: Tower/ODS should not immediately follow wet activities."""
    violations = []
    WET_ACTIVITIES = [
        "Aqua Trampoline", "Water Polo", "Greased Watermelon", "Troop Swim",
        "Underwater Obstacle Course", "Troop Canoe", "Troop Kayak", 
        "Canoe Snorkel", "Nature Canoe", "Float for Floats", "Sailing", "Delta"
    ]
    TOWER_ODS = [
        "Climbing Tower", "Knots and Lashings", "Orienteering",
        "GPS & Geocaching", "Ultimate Survivor", "What's Cooking", "Chopped!"
    ]
    
    for troop in troops:
        troop_schedule = sorted(
            [e for e in schedule.entries if e.troop == troop],
            key=lambda e: (e.time_slot.day.value, e.time_slot.slot_number)
        )
        
        for i, entry in enumerate(troop_schedule):
            if entry.activity.name in TOWER_ODS and i > 0:
                prev_entry = troop_schedule[i-1]
                # Check if previous is wet and consecutive
                if (prev_entry.activity.name in WET_ACTIVITIES and
                    prev_entry.time_slot.day == entry.time_slot.day and
                    prev_entry.time_slot.slot_number == entry.time_slot.slot_number - 1):
                    violations.append(
f"{troop.name}: {entry.activity.name} immediately after {prev_entry.activity.name} on {entry.time_slot.day.value}"
                    )
    
    return violations

def test_delta_before_super_troop(schedule, troops):
    """Test: Delta must be scheduled before Super Troop for each troop."""
    violations = []
    
    for troop in troops:
        delta_slot = None
        super_troop_slot = None
        
        for entry in schedule.entries:
            if entry.troop == troop:
                if entry.activity.name == "Delta":
                    delta_slot = (entry.time_slot.day.value, entry.time_slot.slot_number)
                elif entry.activity.name == "Super Troop":
                    super_troop_slot = (entry.time_slot.day.value, entry.time_slot.slot_number)
        
        # If both exist, Delta must come before Super Troop
        if delta_slot and super_troop_slot:
            if delta_slot >= super_troop_slot:
                violations.append(
                    f"{troop.name}: Delta ({delta_slot[0]}-{delta_slot[1]}) not before Super Troop ({super_troop_slot[0]}-{super_troop_slot[1]})"
                )
    
    return violations

def run_constraint_tests(week_file):
    """Run all constraint tests on a week file."""
    print(f"\n{'='*60}")
    print(f"Testing Constraints: {week_file}")
    print('='*60)
    
    troops = load_troops_from_json(week_file)
    scheduler = ConstrainedScheduler(troops, get_all_activities())
    schedule = scheduler.schedule_all()
    
    all_violations = []
    
    # Test 1: Beach slot constraint
    print("\nTest 1: Beach Slot Constraint...")
    violations = test_beach_slot_constraint(schedule, troops)
    if violations:
        print(f"  [FAIL] {len(violations)} violations:")
        for v in violations:
            print(f"    - {v}")
        all_violations.extend(violations)
    else:
        print("  [OK] PASSED")
    
    # Test 2: Accuracy limit
    print("\nTest 2: Accuracy Activity Limit...")
    violations = test_accuracy_limit(schedule, troops)
    if violations:
        print(f"  [FAIL] {len(violations)} violations:")
        for v in violations:
            print(f"    - {v}")
        all_violations.extend(violations)
    else:
        print("  [OK] PASSED")
    
    # Test 3: Friday Reflection
    print("\nTest 3: Friday Reflection (All Troops)...")
    violations = test_friday_reflection(schedule, troops)
    if violations:
        print(f"  [FAIL] {len(violations)} violations:")
        for v in violations:
            print(f"    - {v}")
        all_violations.extend(violations)
    else:
        print("  [OK] PASSED")
    
    # Test 4: Wet before Tower/ODS
    print("\nTest 4: No Tower/ODS After Wet...")
    violations = test_wet_before_tower_ods(schedule, troops)
    if violations:
        print(f"  [WARN] {len(violations)} violations:")
        for v in violations:
            print(f"    - {v}")
        all_violations.extend(violations)
    else:
        print("  [OK] PASSED")
    
    # Test 5: Delta before Super Troop
    print("\nTest 5: Delta Before Super Troop...")
    violations = test_delta_before_super_troop(schedule, troops)
    if violations:
        print(f"  [FAIL] {len(violations)} violations:")
        for v in violations:
            print(f"    - {v}")
        all_violations.extend(violations)
    else:
        print("  [OK] PASSED")
    
    return len(all_violations) == 0

if __name__ == "__main__":
    import glob
    
    week_files = glob.glob("../tc_week*.json") + glob.glob("../voyageur_week*.json")
    
    all_passed = True
    for week_file in sorted(week_files):
        passed = run_constraint_tests(week_file)
        if not passed:
            all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print("[OK] ALL CONSTRAINT TESTS PASSED")
    else:
        print("[FAIL] SOME TESTS FAILED")
    print("="*60)
