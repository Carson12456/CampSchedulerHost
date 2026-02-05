#!/usr/bin/env python3
"""
Test script to run the optimized scheduler and measure improvements.
"""

import constrained_scheduler
from models import generate_time_slots
from io_handler import load_troops_from_json
from activities import get_all_activities
import time
from pathlib import Path

def test_optimized_scheduler():
    """Test the optimized scheduler and measure key metrics."""
    print("=== TESTING OPTIMIZED SCHEDULER ===\n")
    
    # Load test data
    troops_file = Path("tc_week5_troops.json")
    if not troops_file.exists():
        print(f"Error: {troops_file} not found. Please ensure troop data file exists.")
        return None
    
    troops = load_troops_from_json(troops_file)
    activities = get_all_activities()
    time_slots = generate_time_slots()
    
    print(f"Loaded {len(troops)} troops and {len(activities)} activities")
    print(f"Generated {len(time_slots)} time slots")
    
    # Create and run scheduler
    start_time = time.time()
    scheduler = constrained_scheduler.ConstrainedScheduler(troops, activities)
    schedule = scheduler.schedule_all()
    end_time = time.time()
    
    print(f"\nSchedule completed in {end_time - start_time:.2f} seconds")
    
    # Calculate metrics
    total_entries = len(schedule.entries)
    loads = scheduler._calculate_staff_load_by_slot()
    avg_staff = sum(loads.values()) / len(loads)
    high_loads = sum(1 for load in loads.values() if load > 14)
    underused = sum(1 for load in loads.values() if load < 5)
    
    # Calculate staff variance manually
    slot_totals = list(loads.values())
    if slot_totals:
        mean = sum(slot_totals) / len(slot_totals)
        variance = sum((x - mean) ** 2 for x in slot_totals) / len(slot_totals)
        staff_variance = variance ** 0.5
    else:
        staff_variance = 0.0
    
    # Check clustering
    activity_days = {}
    for entry in schedule.entries:
        activity = entry.activity.name
        if activity not in activity_days:
            activity_days[activity] = set()
        activity_days[activity].add(entry.time_slot.day.name)
    
    excess_activities = sum(1 for days in activity_days.values() if len(days) > 3)
    
    # Check preference satisfaction
    total_preferences = sum(len(troop.preferences) for troop in troops)
    satisfied_preferences = 0
    for troop in troops:
        for entry in schedule.entries:
            if entry.troop == troop:
                for i, pref in enumerate(troop.preferences):
                    if entry.activity.name == pref:
                        satisfied_preferences += 1
                        break
    
    satisfaction_rate = (satisfied_preferences / total_preferences) * 100 if total_preferences > 0 else 0
    
    print("\n=== OPTIMIZATION RESULTS ===")
    print(f"Total scheduled entries: {total_entries}")
    print(f"Average staff per slot: {avg_staff:.1f}")
    print(f"Slots with >14 staff: {high_loads}")
    print(f"Slots with <5 staff: {underused}")
    print(f"Staff variance: {staff_variance:.2f}")
    print(f"Activities using >3 days: {excess_activities}")
    print(f"Preference satisfaction: {satisfaction_rate:.1f}% ({satisfied_preferences}/{total_preferences})")
    
    # Detailed staff breakdown
    print("\n=== STAFF DISTRIBUTION ===")
    # Sort by day then slot number
    from models import Day
    day_order = [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.THURSDAY, Day.FRIDAY]
    sorted_slots = sorted(loads.items(), key=lambda x: (day_order.index(x[0].day), x[0].slot_number))
    for slot, load in sorted_slots:
        status = "HIGH" if load > 14 else "LOW" if load < 5 else "OK"
        print(f"{slot.day.name} Slot {slot.slot_number}: {load} staff [{status}]")
    
    # Clustering analysis
    print("\n=== CLUSTERING ANALYSIS ===")
    clustered_activities = 0
    for activity, days in activity_days.items():
        if len(days) <= 3:
            clustered_activities += 1
        else:
            print(f"  {activity}: {len(days)} days ({', '.join(sorted(days))})")
    
    print(f"Well-clustered activities (<=3 days): {clustered_activities}/{len(activity_days)}")
    
    return {
        'total_entries': total_entries,
        'avg_staff': avg_staff,
        'high_loads': high_loads,
        'underused': underused,
        'staff_variance': staff_variance,
        'excess_activities': excess_activities,
        'satisfaction_rate': satisfaction_rate,
        'runtime': end_time - start_time
    }

if __name__ == "__main__":
    results = test_optimized_scheduler()
    if results:
        print(f"\n=== SUMMARY ===")
        print(f"Optimization completed successfully!")
        print(f"Key improvements: Staff variance {results['staff_variance']:.2f}, High loads {results['high_loads']}, Underused {results['underused']}")
    else:
        print("Optimization test failed.")
