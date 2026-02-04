#!/usr/bin/env python3
"""
Final Reflection Fix - Apply reflection fix to all existing schedules
"""

import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from io_handler import load_schedule_from_json, save_schedule_to_json
from activities import get_all_activities


def fix_reflections_in_schedule(schedule_file):
    """Fix reflections in a single schedule file."""
    print(f"Processing {schedule_file}...")
    
    try:
        # Load the schedule
        schedule_data = load_schedule_from_json(schedule_file)
        if not schedule_data:
            print(f"  ERROR: Could not load {schedule_file}")
            return False
        
        schedule, troops = schedule_data
        activities = get_all_activities()
        
        # Get Reflection activity
        reflection = None
        for activity in activities:
            if activity.name == "Reflection":
                reflection = activity
                break
        
        if not reflection:
            print("  ERROR: Reflection activity not found!")
            return False
        
        # Get Friday slots
        friday_slots = []
        for entry in schedule.entries:
            if entry.time_slot.day.name == "FRIDAY":
                if entry.time_slot not in friday_slots:
                    friday_slots.append(entry.time_slot)
        
        if not friday_slots:
            print("  ERROR: No Friday slots found!")
            return False
        
        # Sort Friday slots
        friday_slots.sort(key=lambda x: x.slot_number)
        print(f"  Found {len(friday_slots)} Friday slots")
        
        # Check current reflection compliance
        troops_with_reflection = []
        troops_missing_reflection = []
        
        for troop in troops:
            has_reflection = any(e.activity.name == "Reflection" and e.troop == troop 
                                for e in schedule.entries)
            if has_reflection:
                troops_with_reflection.append(troop)
            else:
                troops_missing_reflection.append(troop)
        
        print(f"  Current compliance: {len(troops_with_reflection)}/{len(troops)} ({100.0*len(troops_with_reflection)/len(troops):.1f}%)")
        
        if not troops_missing_reflection:
            print("  SUCCESS: All troops already have Reflection!")
            return True
        
        # Fix missing reflections
        from models import ScheduleEntry
        
        # Distribute troops evenly across slots
        troops_per_slot = max(1, len(troops_missing_reflection) // len(friday_slots))
        
        slot_index = 0
        troops_in_current_slot = 0
        
        for troop in troops_missing_reflection:
            # Determine which slot to use
            if troops_in_current_slot >= troops_per_slot:
                slot_index = (slot_index + 1) % len(friday_slots)
                troops_in_current_slot = 0
            
            slot = friday_slots[slot_index]
            
            # Remove any existing activity for this troop in this slot
            existing_entries = [e for e in schedule.entries 
                              if e.time_slot == slot and e.troop == troop]
            
            for entry in existing_entries:
                schedule.entries.remove(entry)
                print(f"    [REMOVED] {troop.name}: {entry.activity.name} from {slot}")
            
            # Add Reflection
            entry = ScheduleEntry(slot, reflection, troop)
            schedule.entries.append(entry)
            print(f"    [ADDED] {troop.name}: Reflection -> {slot}")
            troops_in_current_slot += 1
        
        # Verify the fix
        final_with_reflection = []
        for troop in troops:
            has_reflection = any(e.activity.name == "Reflection" and e.troop == troop 
                                for e in schedule.entries)
            if has_reflection:
                final_with_reflection.append(troop)
        
        print(f"  Final compliance: {len(final_with_reflection)}/{len(troops)} ({100.0*len(final_with_reflection)/len(troops):.1f}%)")
        
        # Save the updated schedule
        save_schedule_to_json(schedule, troops, schedule_file)
        print(f"  SAVED: {schedule_file}")
        
        return len(final_with_reflection) == len(troops)
        
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main function."""
    print("FINAL REFLECTION FIX")
    print("=" * 60)
    print("Apply reflection fix to all existing schedule files")
    print()
    
    # Change to script directory
    script_dir = Path(__file__).resolve().parent
    os.chdir(script_dir)
    
    # Find all schedule files
    schedules_dir = Path("schedules")
    if not schedules_dir.exists():
        print("ERROR: schedules directory not found!")
        return 1
    
    schedule_files = list(schedules_dir.glob("*_schedule.json"))
    if not schedule_files:
        print("ERROR: No schedule files found!")
        return 1
    
    print(f"Found {len(schedule_files)} schedule files")
    print()
    
    results = []
    
    for schedule_file in sorted(schedule_files):
        success = fix_reflections_in_schedule(str(schedule_file))
        results.append({
            'file': schedule_file.name,
            'success': success
        })
        print()
    
    # Summary
    print("=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)
    
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    
    print(f"Successfully processed: {len(successful)}/{len(results)} files")
    
    if successful:
        print(f"Files with 100% Reflection compliance:")
        for r in successful:
            print(f"  ✓ {r['file']}")
    
    if failed:
        print(f"Files that failed:")
        for r in failed:
            print(f"  ✗ {r['file']}")
    
    if len(successful) == len(results):
        print("\n🎉 SUCCESS: All schedules now have 100% Reflection compliance!")
        return 0
    else:
        print(f"\n⚠️  PARTIAL: {len(failed)} files still need attention")
        return 1


if __name__ == "__main__":
    sys.exit(main())
