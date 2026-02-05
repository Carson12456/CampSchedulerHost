#!/usr/bin/env python3
"""
Targeted fix for beach slot constraints blocking Aqua Trampoline placement.
"""

import json
from pathlib import Path
from io_handler import load_troops_from_json
from activities import get_all_activities
from constrained_scheduler import ConstrainedScheduler
from models import ScheduleEntry, TimeSlot, Day

def apply_targeted_beach_fix():
    """
    Apply targeted fix to relax beach slot constraints for Top 5 preferences.
    """
    print("TARGETED BEACH CONSTRAINT FIX")
    print("=" * 40)
    
    # Focus on week with most AT issues
    week = "tc_week4"
    troops_file = Path(f"{week}_troops.json")
    
    if not troops_file.exists():
        print(f"File not found: {troops_file}")
        return
    
    # Load and generate schedule
    troops = load_troops_from_json(troops_file)
    activities = get_all_activities()
    scheduler = ConstrainedScheduler(troops, activities)
    schedule = scheduler.schedule_all()
    
    # Identify AT misses
    at_misses = identify_at_misses(schedule, troops)
    print(f"Found {len(at_misses)} Aqua Trampoline misses:")
    for miss in at_misses:
        print(f"  {miss['troop'].name} (Rank #{miss['rank']})")
    
    # Apply targeted fix
    fixes = apply_at_constraint_relaxation(schedule, at_misses)
    print(f"\nApplied {len(fixes)} fixes:")
    for fix in fixes:
        print(f"  {fix['troop']}: {fix['action']}")
    
    # Re-check results
    remaining_misses = identify_at_misses(schedule, troops)
    print(f"\nRemaining Aqua Trampoline misses: {len(remaining_misses)}")
    
    # Save fixed schedule
    save_fixed_schedule(schedule, week)
    
    return len(at_misses) - len(remaining_misses)

def identify_at_misses(schedule, troops):
    """Identify troops missing Aqua Trampoline in Top 5."""
    misses = []
    
    for troop in troops:
        # Get troop's current activities
        troop_activities = set()
        for entry in schedule.entries:
            if entry.troop == troop:
                troop_activities.add(entry.activity.name)
        
        # Check Top 5 for Aqua Trampoline
        top5_prefs = troop.preferences[:5] if len(troop.preferences) >= 5 else troop.preferences
        
        if "Aqua Trampoline" in top5_prefs and "Aqua Trampoline" not in troop_activities:
            rank = top5_prefs.index("Aqua Trampoline") + 1
            misses.append({
                'troop': troop,
                'rank': rank,
                'available_slots': find_available_slots(schedule, troop)
            })
    
    return misses

def find_available_slots(schedule, troop):
    """Find available slots for a troop."""
    occupied_slots = set()
    for entry in schedule.entries:
        if entry.troop == troop:
            occupied_slots.add(entry.time_slot)
    
    # All possible slots
    all_slots = []
    for day in [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.THURSDAY, Day.FRIDAY]:
        for slot_num in [1, 2, 3]:
            slot = TimeSlot(day, slot_num)
            if slot not in occupied_slots:
                all_slots.append(slot)
    
    return all_slots

def apply_at_constraint_relaxation(schedule, at_misses):
    """Apply constraint relaxation for Aqua Trampoline."""
    fixes = []
    
    from activities import get_activity_by_name
    at_activity = get_activity_by_name("Aqua Trampoline")
    
    for miss in at_misses:
        troop = miss['troop']
        rank = miss['rank']
        
        # Priority 1: Rank #1 gets slot 2 relaxation
        if rank == 1:
            # Try slot 2 first (normally forbidden)
            for slot in miss['available_slots']:
                if slot.slot_number == 2:
                    # Check if we can place AT here (relaxing beach constraint)
                    if can_place_at_with_relaxation(schedule, troop, at_activity, slot):
                        # Create new entry
                        new_entry = ScheduleEntry(troop, at_activity, slot)
                        schedule.entries.append(new_entry)
                        
                        fixes.append({
                            'troop': troop.name,
                            'action': f'Placed AT in {slot.day.value}-{slot.slot_number} (constraint relaxed)',
                            'rank': rank
                        })
                        break
        
        # Priority 2: Try other slots if rank 1 failed
        if not any(f['troop'] == troop.name for f in fixes):
            for slot in miss['available_slots']:
                if can_place_at_normal(schedule, troop, at_activity, slot):
                    new_entry = ScheduleEntry(troop, at_activity, slot)
                    schedule.entries.append(new_entry)
                    
                    fixes.append({
                        'troop': troop.name,
                        'action': f'Placed AT in {slot.day.value}-{slot.slot_number}',
                        'rank': rank
                    })
                    break
    
    return fixes

def can_place_at_with_relaxation(schedule, troop, activity, slot):
    """Check if activity can be placed with constraint relaxation."""
    # Relaxed beach constraint check for Rank #1 AT
    if activity.name == "Aqua Trampoline" and slot.slot_number == 2:
        # Allow slot 2 for Rank #1 AT (constraint relaxation)
        return True
    
    # Other normal checks
    return can_place_at_normal(schedule, troop, activity, slot)

def can_place_at_normal(schedule, troop, activity, slot):
    """Normal placement check."""
    # Check if slot is already occupied by this troop
    for entry in schedule.entries:
        if entry.troop == troop and entry.time_slot == slot:
            return False
    
    # Check exclusive activity conflicts
    if activity.name in ["Aqua Trampoline", "Sailing", "Climbing Tower"]:
        for entry in schedule.entries:
            if entry.time_slot == slot and entry.activity.name == activity.name:
                return False
    
    return True

def save_fixed_schedule(schedule, week):
    """Save the fixed schedule."""
    output_file = Path(f"schedules/{week}_beach_fixed_schedule.json")
    
    # Convert to dict format
    schedule_dict = {
        'entries': [
            {
                'troop': entry.troop.name,
                'activity': entry.activity.name,
                'day': entry.time_slot.day.value,
                'slot': entry.time_slot.slot_number
            }
            for entry in schedule.entries
        ]
    }
    
    with open(output_file, 'w') as f:
        json.dump(schedule_dict, f, indent=2)
    
    print(f"Fixed schedule saved to: {output_file}")

if __name__ == "__main__":
    improvement = apply_targeted_beach_fix()
    print(f"\nTotal improvement: {improvement} Aqua Trampoline placements")
