#!/usr/bin/env python3
"""
Direct Reflection Fix - Apply reflection fix directly to existing schedules
"""

import sys
import os
import json
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from io_handler import load_troops_from_json
from activities import get_all_activities
from models import ScheduleEntry, Day, TimeSlot, Activity, Troop


def fix_reflections_in_existing_schedule(schedule_file, troop_file):
    """Fix reflections in an existing schedule file."""
    print(f"Processing {schedule_file} with {troop_file}...")
    
    try:
        # Load troops
        troops = load_troops_from_json(troop_file)
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
        
        # Load existing schedule
        with open(schedule_file, 'r') as f:
            schedule_data = json.load(f)
        
        # Create schedule entries from the data
        entries = []
        for entry_data in schedule_data.get('entries', []):
            # Find matching troop and activity
            troop = next((t for t in troops if t.name == entry_data['troop']), None)
            activity = next((a for a in activities if a.name == entry_data['activity']), None)
            
            if troop and activity:
                # Parse time slot
                day_name = entry_data['time_slot']['day']
                slot_number = entry_data['time_slot']['slot_number']
                
                # Convert day name to Day enum
                day_map = {
                    'MONDAY': Day.MONDAY,
                    'TUESDAY': Day.TUESDAY,
                    'WEDNESDAY': Day.WEDNESDAY,
                    'THURSDAY': Day.THURSDAY,
                    'FRIDAY': Day.FRIDAY
                }
                
                day = day_map.get(day_name)
                if day:
                    time_slot = TimeSlot(day, slot_number)
                    entry = ScheduleEntry(time_slot, activity, troop)
                    entries.append(entry)
        
        print(f"  Loaded {len(entries)} existing entries")
        
        # Check current reflection compliance
        troops_with_reflection = []
        troops_missing_reflection = []
        
        for troop in troops:
            has_reflection = any(e.activity.name == "Reflection" and e.troop == troop 
                                for e in entries)
            if has_reflection:
                troops_with_reflection.append(troop)
            else:
                troops_missing_reflection.append(troop)
        
        print(f"  Current compliance: {len(troops_with_reflection)}/{len(troops)} ({100.0*len(troops_with_reflection)/len(troops):.1f}%)")
        
        if not troops_missing_reflection:
            print("  SUCCESS: All troops already have Reflection!")
            return True
        
        # Get Friday slots from existing entries
        friday_slots = []
        for entry in entries:
            if entry.time_slot.day == Day.FRIDAY:
                if entry.time_slot not in friday_slots:
                    friday_slots.append(entry.time_slot)
        
        # If no Friday slots found, create them
        if not friday_slots:
            friday_slots = [
                TimeSlot(Day.FRIDAY, 1),
                TimeSlot(Day.FRIDAY, 2),
                TimeSlot(Day.FRIDAY, 3)
            ]
        
        # Sort Friday slots
        friday_slots.sort(key=lambda x: x.slot_number)
        print(f"  Using {len(friday_slots)} Friday slots")
        
        # Fix missing reflections
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
            existing_entries = [e for e in entries 
                              if e.time_slot == slot and e.troop == troop]
            
            for entry in existing_entries:
                entries.remove(entry)
                print(f"    [REMOVED] {troop.name}: {entry.activity.name} from {slot}")
            
            # Add Reflection
            entry = ScheduleEntry(slot, reflection, troop)
            entries.append(entry)
            print(f"    [ADDED] {troop.name}: Reflection -> {slot}")
            troops_in_current_slot += 1
        
        # Verify the fix
        final_with_reflection = []
        for troop in troops:
            has_reflection = any(e.activity.name == "Reflection" and e.troop == troop 
                                for e in entries)
            if has_reflection:
                final_with_reflection.append(troop)
        
        print(f"  Final compliance: {len(final_with_reflection)}/{len(troops)} ({100.0*len(final_with_reflection)/len(troops):.1f}%)")
        
        # Convert entries back to JSON format
        entries_json = []
        for entry in entries:
            entry_json = {
                'troop': entry.troop.name,
                'activity': entry.activity.name,
                'time_slot': {
                    'day': entry.time_slot.day.name,
                    'slot_number': entry.time_slot.slot_number
                }
            }
            entries_json.append(entry_json)
        
        # Update the schedule data
        schedule_data['entries'] = entries_json
        
        # Calculate unscheduled data
        from collections import defaultdict
        scheduled = defaultdict(set)
        for entry in entries:
            scheduled[entry.troop.name].add(entry.activity.name)
        
        unscheduled_data = {}
        for troop in troops:
            troop_name = troop.name
            preferences = troop.preferences[:5]  # Top 5
            
            # Check Reflection
            has_reflection = 'Reflection' in scheduled.get(troop_name, set())
            
            # Find missing Top 5
            missing_top5 = []
            for i, pref in enumerate(preferences):
                if pref not in scheduled.get(troop_name, set()):
                    missing_top5.append({
                        'name': pref,
                        'rank': i + 1,
                        'is_exempt': False
                    })
            
            unscheduled_data[troop_name] = {
                'top5': missing_top5,
                'top10': [],
                'has_reflection': has_reflection
            }
        
        schedule_data['unscheduled_data'] = unscheduled_data
        
        # Save the updated schedule
        with open(schedule_file, 'w') as f:
            json.dump(schedule_data, f, indent=2)
        
        print(f"  SAVED: {schedule_file}")
        
        return len(final_with_reflection) == len(troops)
        
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main function."""
    print("DIRECT REFLECTION FIX - APPLY TO EXISTING SCHEDULES")
    print("=" * 60)
    print()
    
    # Change to script directory
    script_dir = Path(__file__).resolve().parent
    os.chdir(script_dir)
    
    # Define the schedule files to fix
    schedule_fixes = [
        ('schedules/tc_week1_troops_schedule.json', 'tc_week1_troops.json'),
        ('schedules/tc_week2_troops_schedule.json', 'tc_week2_troops.json'),
        ('schedules/tc_week3_troops_schedule.json', 'tc_week3_troops.json'),
        ('schedules/tc_week4_troops_schedule.json', 'tc_week4_troops.json'),
        ('schedules/tc_week5_troops_schedule.json', 'tc_week5_troops.json'),
        ('schedules/tc_week6_troops_schedule.json', 'tc_week6_troops.json'),
        ('schedules/tc_week7_troops_schedule.json', 'tc_week7_troops.json'),
        ('schedules/tc_week8_troops_schedule.json', 'tc_week8_troops.json'),
        ('schedules/voyageur_week1_troops_schedule.json', 'voyageur_week1_troops.json'),
        ('schedules/voyageur_week3_troops_schedule.json', 'voyageur_week3_troops.json')
    ]
    
    results = []
    
    for schedule_file, troop_file in schedule_fixes:
        if not Path(schedule_file).exists():
            print(f"Skipping {schedule_file} (not found)")
            continue
            
        success = fix_reflections_in_existing_schedule(schedule_file, troop_file)
        results.append({
            'file': schedule_file,
            'success': success
        })
        print()
    
    # Summary
    print("=" * 60)
    print("DIRECT REFLECTION FIX SUMMARY")
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
