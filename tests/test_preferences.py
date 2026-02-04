"""
Test suite for preference satisfaction and staff distribution validation.
Validates that troops get their preferred activities and staff workload is balanced.
"""
import sys
sys.path.insert(0, '..')

from constrained_scheduler import ConstrainedScheduler
from activities import get_all_activities
from io_handler import load_troops_from_json
from collections import defaultdict

def test_preference_satisfaction(schedule, troops):
    """Test preference satisfaction rates for all troops."""
    stats = {
        'top5_achieved': 0,
        'top5_total': 0,
        'top10_achieved': 0,
        'top10_total': 0,
        'top15_achieved': 0,
        'top15_total': 0
    }
    
    troop_stats = []
    
    for troop in troops:
        troop_activities = set(e.activity.name for e in schedule.entries if e.troop == troop)
        
        top5 = set(troop.preferences[:5]) if len(troop.preferences) >= 5 else set(troop.preferences)
        top10 = set(troop.preferences[:10]) if len(troop.preferences) >= 10 else set(troop.preferences)
        top15 = set(troop.preferences[:15]) if len(troop.preferences) >= 15 else set(troop.preferences)
        
        top5_got = len(top5 & troop_activities)
        top10_got = len(top10 & troop_activities)
        top15_got = len(top15 & troop_activities)
        
        stats['top5_achieved'] += top5_got
        stats['top5_total'] += len(top5)
        stats['top10_achieved'] += top10_got
        stats['top10_total'] += len(top10)
        stats['top15_achieved'] += top15_got
        stats['top15_total'] += len(top15)
        
        troop_stats.append({
            'troop': troop.name,
            'top5': f"{top5_got}/{len(top5)}",
            'top10': f"{top10_got}/{len(top10)}",
            'top15': f"{top15_got}/{len(top15)}"
        })
    
    return stats, troop_stats

def test_staff_distribution(schedule, troops):
    """Test staff workload distribution across time slots - per USER REQUEST."""
    # Map activities to staff
    STAFF_ACTIVITIES = {
        'Beach Staff': ['Aqua Trampoline', 'Troop Canoe', 'Troop Kayak', 'Canoe Snorkel',
                       'Float for Floats', 'Greased Watermelon', 'Underwater Obstacle Course',
                       'Troop Swim', 'Water Polo'],
        'Boats Director': ['Sailing'],
        'Shooting Sports Director': ['Troop Rifle', 'Troop Shotgun'],
        'Tower Director': ['Climbing Tower'],
        'ODS Director': ['Knots and Lashings', 'Orienteering', 'GPS & Geocaching',
                        'Ultimate Survivor', "What's Cooking", 'Chopped!'],
        'Nature Director': ['Dr. DNA', 'Loon Lore', 'Nature Canoe', 'Ecosystem in a Jar',
                           'Nature Salad', 'Nature Bingo'],
        'Handicrafts Director': ['Tie Dye', 'Hemp Craft', 'Woggle Neckerchief Slide', "Monkey's Fist"],
        'Commissioner': ['Archery', 'Delta', 'Super Troop', 'Reflection']
    }
    
    # Count staff requirements per slot
    slot_staff = defaultdict(lambda: defaultdict(int))
    
    for entry in schedule.entries:
        key = (entry.time_slot.day.value, entry.time_slot.slot_number)
        
        for staff_name, activities in STAFF_ACTIVITIES.items():
            if entry.activity.name in activities:
                slot_staff[key][staff_name] += 1
           
    # Calculate statistics
    staff_stats = defaultdict(list)
    for slot, staff_counts in slot_staff.items():
        for staff, count in staff_counts.items():
            staff_stats[staff].append(count)
    
    # Compute averages and max
    staff_summary = {}
    for staff, counts in staff_stats.items():
        staff_summary[staff] = {
            'avg': sum(counts) / len(counts) if counts else 0,
            'max': max(counts) if counts else 0,
            'min': min(counts) if counts else 0,
            'total_slots': len(counts)
        }
    
    return staff_summary, slot_staff

def run_preference_tests(week_file):
    """Run all preference and staff distribution tests on a week file."""
    print(f"\n{'='*60}")
    print(f"Testing Preferences & Staff: {week_file}")
    print('='*60)
    
    troops = load_troops_from_json(week_file)
    scheduler = ConstrainedScheduler(troops, get_all_activities())
    schedule = scheduler.schedule_all()
    
    # Test 1: Preference satisfaction
    print("\nTest 1: Preference Satisfaction Rates...")
    stats, troop_stats = test_preference_satisfaction(schedule, troops)
    
    top5_pct = (stats['top5_achieved'] / stats['top5_total'] * 100) if stats['top5_total'] > 0 else 0
    top10_pct = (stats['top10_achieved'] / stats['top10_total'] * 100) if stats['top10_total'] > 0 else 0
    top15_pct = (stats['top15_achieved'] / stats['top15_total'] * 100) if stats['top15_total'] > 0 else 0
    
    print(f"  Top 5:  {top5_pct:.1f}% ({stats['top5_achieved']}/{stats['top5_total']}) - " + 
          ("[OK] GOOD" if top5_pct >= 90 else "[WARN] NEEDS IMPROVEMENT"))
    print(f"  Top 10: {top10_pct:.1f}% ({stats['top10_achieved']}/{stats['top10_total']}) - " +
          ("[OK] GOOD" if top10_pct >= 80 else "[WARN] NEEDS IMPROVEMENT"))
    print(f"  Top 15: {top15_pct:.1f}% ({stats['top15_achieved']}/{stats['top15_total']}) - " +
          ("[OK] GOOD" if top15_pct >= 70 else "[WARN] NEEDS IMPROVEMENT"))
    
    # Test 2: Staff distribution
    print("\nTest 2: Staff Workload Distribution...")
    staff_summary, slot_staff = test_staff_distribution(schedule, troops)
    
    for staff, summary in sorted(staff_summary.items()):
        balance = "[OK] BALANCED" if summary['max'] - summary['min'] <= 2 else "[WARN] UNBALANCED"
        print(f"  {staff}: avg={summary['avg']:.1f}, max={summary['max']}, min={summary['min']} ({summary['total_slots']} slots) - {balance}")
    
    return top5_pct >= 85  # Pass if top 5 is at least 85%

if __name__ == "__main__":
    import glob
    
    week_files = glob.glob("../tc_week*.json") + glob.glob("../voyageur_week*.json")
    
    all_passed = True
    for week_file in sorted(week_files):
        passed = run_preference_tests(week_file)
        if not passed:
            all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print("[OK] ALL PREFERENCE TESTS PASSED")
    else:
        print("[WARN] SOME WEEKS BELOW TARGET")
    print("="*60)
