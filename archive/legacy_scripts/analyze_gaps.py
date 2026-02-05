#!/usr/bin/env python3
"""
Analyze gaps in the current schedule and measure baseline performance.
"""

from constrained_scheduler import ConstrainedScheduler
from io_handler import load_troops_from_json
from activities import get_all_activities
from pathlib import Path
import json

def analyze_schedule_gaps():
    """Analyze gaps and measure current performance."""
    print("=== SCHEDULE GAP ANALYSIS ===\n")
    
    # Load current schedule
    troops_file = Path("tc_week5_troops.json")
    troops = load_troops_from_json(troops_file)
    activities = get_all_activities()
    
    # Import Day early
    from models import Day
    
    scheduler = ConstrainedScheduler(troops, activities)
    schedule = scheduler.schedule_all()
    
    # FINAL: Force 0 gaps one more time after all scheduling is complete
    print("\n=== POST-SCHEDULING FINAL GAP FILL ===")
    scheduler._force_zero_gaps_absolute()
    print("=== POST-SCHEDULING COMPLETE ===\n")
    
    # Count gaps per troop using the same method as scheduler
    total_gaps = 0
    troop_gaps = {}
    
    # Use the same gap detection as the scheduler
    days_list = [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.THURSDAY, Day.FRIDAY]
    slots_per_day = {
        Day.MONDAY: 3, Day.TUESDAY: 3, Day.WEDNESDAY: 3,
        Day.THURSDAY: 2, Day.FRIDAY: 3
    }
    
    for troop in troops:
        troop_gaps_count = 0
        
        for day in days_list:
            for slot_num in range(1, slots_per_day[day] + 1):
                slot = next((s for s in scheduler.time_slots 
                            if s.day == day and s.slot_number == slot_num), None)
                if slot and schedule.is_troop_free(slot, troop):
                    troop_gaps_count += 1
        
        total_gaps += troop_gaps_count
        troop_gaps[troop.name] = troop_gaps_count
        
        if troop_gaps_count > 0:
            filled_slots = 15 - troop_gaps_count  # Total slots is always 15 (14+1 for Thursday)
            print(f"{troop.name}: {troop_gaps_count} gaps ({filled_slots}/15 slots filled)")
    
    print(f"\nTotal gaps across all troops: {total_gaps}")
    
    # Analyze gap patterns by day/slot
    day_slot_gaps = {}
    for day in Day:
        max_slots = 3
        if day == Day.THURSDAY:
            max_slots = 2  # Thursday only has 2 slots
            
        for slot_num in range(1, max_slots + 1):
            day_slot_gaps[(day.name, slot_num)] = 0
    
    for troop in troops:
        troop_entries = schedule.get_troop_schedule(troop)
        filled_day_slots = set()
        
        for entry in troop_entries:
            filled_day_slots.add((entry.time_slot.day.name, entry.time_slot.slot_number))
        
        # Count gaps for this troop
        for day in Day:
            max_slots = 3
            if day == Day.THURSDAY:
                max_slots = 2  # Thursday only has 2 slots
                
            for slot_num in range(1, max_slots + 1):
                if (day.name, slot_num) not in filled_day_slots:
                    day_slot_gaps[(day.name, slot_num)] += 1
    
    print("\n=== GAPS BY DAY/SLOT ===")
    for day in Day:
        print(f"\n{day.name}:")
        max_slots = 3
        if day == Day.THURSDAY:
            max_slots = 2  # Thursday only has 2 slots
            
        for slot_num in range(1, max_slots + 1):
            gaps = day_slot_gaps[(day.name, slot_num)]
            if gaps > 0:
                print(f"  Slot {slot_num}: {gaps} troops with gaps")
    
    # Calculate baseline metrics
    total_preferences = sum(len(troop.preferences) for troop in troops)
    satisfied_preferences = 0
    
    for troop in troops:
        troop_entries = schedule.get_troop_schedule(troop)
        scheduled_activities = {e.activity.name for e in troop_entries}
        for pref in troop.preferences:
            if pref in scheduled_activities:
                satisfied_preferences += 1
    
    satisfaction_rate = (satisfied_preferences / total_preferences) * 100 if total_preferences > 0 else 0
    
    # Staff balance
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
    
    print(f"\n=== BASELINE METRICS ===")
    print(f"Total scheduled entries: {len(schedule.entries)}")
    print(f"Total gaps: {total_gaps}")
    print(f"Preference satisfaction: {satisfaction_rate:.1f}% ({satisfied_preferences}/{total_preferences})")
    print(f"Average staff per slot: {avg_staff:.1f}")
    print(f"Slots with >14 staff: {high_loads}")
    print(f"Slots with <5 staff: {underused}")
    print(f"Staff variance: {staff_variance:.2f}")
    
    return {
        'total_gaps': total_gaps,
        'troop_gaps': troop_gaps,
        'day_slot_gaps': day_slot_gaps,
        'total_entries': len(schedule.entries),
        'satisfaction_rate': satisfaction_rate,
        'avg_staff': avg_staff,
        'high_loads': high_loads,
        'underused': underused,
        'staff_variance': staff_variance
    }

if __name__ == "__main__":
    baseline = analyze_schedule_gaps()
    
    # Save baseline for comparison
    baseline_serializable = {
        'total_gaps': baseline['total_gaps'],
        'troop_gaps': baseline['troop_gaps'],
        'day_slot_gaps': {f"{k[0]}-{k[1]}": v for k, v in baseline['day_slot_gaps'].items()},
        'total_entries': baseline['total_entries'],
        'satisfaction_rate': baseline['satisfaction_rate'],
        'avg_staff': baseline['avg_staff'],
        'high_loads': baseline['high_loads'],
        'underused': baseline['underused'],
        'staff_variance': baseline['staff_variance']
    }
    
    with open("baseline_metrics.json", "w") as f:
        json.dump(baseline_serializable, f, indent=2)
    
    print(f"\nBaseline saved to baseline_metrics.json")
