"""
Test suite for capacity limits validation.
Ensures activity capacities are not exceeded and staff limits are respected.
"""
import sys
sys.path.insert(0, '..')

from constrained_scheduler import ConstrainedScheduler
from activities import get_all_activities
from io_handler import load_troops_from_json
from collections import defaultdict

def test_canoe_capacity(schedule, troops):
    """Test: Max 26 people in canoe activities per slot (13 canoes)."""
    violations = []
    CANOE_ACTIVITIES = ['Nature Canoe', 'Canoe Snorkel', 'Float for Floats', 'Troop Canoe']
    
    # Group by time slot
    slot_participants = defaultdict(int)
    
    for entry in schedule.entries:
        if entry.activity.name in CANOE_ACTIVITIES:
            key = (entry.time_slot.day, entry.time_slot.slot_number)
            #  Count scouts + adults
            slot_participants[key] += (entry.troop.scouts + entry.troop.adults)
    
    for slot, count in slot_participants.items():
        if count > 26:
            violations.append(f"{slot[0].value} Slot {slot[1]}: {count} people in canoes (max 26)")
    
    return violations

def test_aqua_trampoline_sharing(schedule, troops):
    """Test: Aqua Trampoline sharing rules (max 2 small troops or 1 large)."""
    violations = []
    
    # Group by time slot
    slot_troops = defaultdict(list)
    
    for entry in schedule.entries:
        if entry.activity.name == "Aqua Trampoline":
            key = (entry.time_slot.day, entry.time_slot.slot_number)
            if entry.troop not in slot_troops[key]:  # Avoid counting continuations
                slot_troops[key].append(entry.troop)
    
    for slot, troop_list in slot_troops.items():
        if len(troop_list) > 2:
            violations.append(f"{slot[0].value} Slot {slot[1]}: {len(troop_list)} troops sharing Aqua Trampoline (max 2)")
       
        elif len(troop_list) == 2:
            # Both must be <=16 scouts+adults
            for troop in troop_list:
                troop_size = troop.scouts + troop.adults
                if troop_size > 16:
                    violations.append(f"{slot[0].value} Slot {slot[1]}: {troop.name} ({troop_size} scouts+adults) sharing Aqua Trampoline (must be <=16)")
    
    return violations

def test_beach_staff_limit(schedule, troops):
    """Test: Max 12 beach staff per slot."""
    violations = []
    BEACH_STAFFED = [
        'Aqua Trampoline', 'Troop Canoe', 'Troop Kayak', 'Canoe Snorkel',
        'Float for Floats', 'Greased Watermelon', 'Underwater Obstacle Course',
        'Troop Swim', 'Water Polo'
    ]
    
    # Group by time slot, count unique activities (each needs 2 staff)
    slot_staff = defaultdict(set)
    
    for entry in schedule.entries:
        if entry.activity.name in BEACH_STAFFED:
            key = (entry.time_slot.day, entry.time_slot.slot_number)
            slot_staff[key].add((entry.activity.name, entry.troop.name))
    
    for slot, activity_troops in slot_staff.items():
        # Each activity-troop pair needs 2 staff (except shared Aqua Trampoline)
        staff_needed = len(activity_troops) * 2
        
        # Check for shared Aqua Trampoline
        aqua_troops = [t for a, t in activity_troops if a == "Aqua Trampoline"]
        if len(aqua_troops) == 2:
            staff_needed -= 2  # Save 2 staff if shared
        
        if staff_needed > 12:
            violations.append(f"{slot[0].value} Slot {slot[1]}: {staff_needed} beach staff needed (max 12)")
   
    return violations

def test_exclusive_areas(schedule, troops):
    """Test: Only one troop per slot in exclusive areas (Tower, Rifle, ODS, etc)."""
    violations = []
    EXCLUSIVE_AREAS = {
        "Tower": ["Climbing Tower"],
        "Rifle Range": ["Troop Rifle", "Troop Shotgun"],
        "Outdoor Skills": ["Knots and Lashings", "Orienteering", "GPS & Geocaching",
                          "Ultimate Survivor", "What's Cooking", "Chopped!"],
        "Sailing": ["Sailing"],
        "Delta": ["Delta"],
        "Super Troop": ["Super Troop"],
        "Handicrafts": ["Tie Dye", "Hemp Craft", "Woggle Neckerchief Slide", "Monkey's Fist"],
        "Nature Center": ["Dr. DNA", "Loon Lore"]
    }
    
    for area_name, activity_names in EXCLUSIVE_AREAS.items():
        # Group by slot
        slot_troops = defaultdict(set)
        
        for entry in schedule.entries:
            if entry.activity.name in activity_names:
                key = (entry.time_slot.day, entry.time_slot.slot_number)
                slot_troops[key].add(entry.troop.name)
        
        for slot, troop_set in slot_troops.items():
            if len(troop_set) > 1:
                violations.append(
                    f"{slot[0].value} Slot {slot[1]}: {len(troop_set)} troops in {area_name} (exclusive area): {', '.join(troop_set)}"
                )
    
    return violations

def run_capacity_tests(week_file):
    """Run all capacity tests on a week file."""
    print(f"\n{'='*60}")
    print(f"Testing Capacities: {week_file}")
    print('='*60)
    
    troops = load_troops_from_json(week_file)
    scheduler = ConstrainedScheduler(troops, get_all_activities())
    schedule = scheduler.schedule_all()
    
    all_violations = []
    
    # Test 1: Canoe capacity
    print("\nTest 1: Canoe Capacity (26 people max)...")
    violations = test_canoe_capacity(schedule, troops)
    if violations:
        print(f"  [FAIL] {len(violations)} violations:")
        for v in violations:
            print(f"    - {v}")
        all_violations.extend(violations)
    else:
        print("  [OK] PASSED")
    
    # Test 2: Aqua Trampoline sharing
    print("\nTest 2: Aqua Trampoline Sharing...")
    violations = test_aqua_trampoline_sharing(schedule, troops)
    if violations:
        print(f"  [FAIL] {len(violations)} violations:")
        for v in violations:
            print(f"    - {v}")
        all_violations.extend(violations)
    else:
        print("  [OK] PASSED")
    
    # Test 3: Beach staff limit
    print("\nTest 3: Beach Staff Limit (12 max)...")
    violations = test_beach_staff_limit(schedule, troops)
    if violations:
        print(f"  [FAIL] {len(violations)} violations:")
        for v in violations:
            print(f"    - {v}")
        all_violations.extend(violations)
    else:
        print("  [OK] PASSED")
    
    # Test 4: Exclusive areas
    print("\nTest 4: Exclusive Area Enforcement...")
    violations = test_exclusive_areas(schedule, troops)
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
        passed = run_capacity_tests(week_file)
        if not passed:
            all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print("[OK] ALL CAPACITY TESTS PASSED")
    else:
        print("[FAIL] SOME TESTS FAILED")
    print("="*60)
