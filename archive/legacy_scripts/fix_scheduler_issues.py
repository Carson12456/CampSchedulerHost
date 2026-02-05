#!/usr/bin/env python3
"""
Fix Scheduler Issues

1. Fix unscheduled data not being populated in JSON files
2. Ensure all troops have Reflection scheduled
3. Update existing schedule files with proper unscheduled data
"""

import json
import os
from pathlib import Path
from collections import defaultdict
from core.services.unscheduled_analyzer import UnscheduledAnalyzer


def calculate_unscheduled_data(troops, entries):
    """Calculate unscheduled activities from troops and entries."""
    unscheduled_data = {}
    
    # Build scheduled activities lookup
    scheduled = defaultdict(set)
    for entry in entries:
        troop = entry.get('troop_name', '')
        activity = entry.get('activity_name', '')
        if troop and activity:
            scheduled[troop].add(activity)
    
    # HC/DG exemption logic
    tuesday_hc_dg_slots = set()
    for entry in entries:
        if entry.get('day') == 'TUESDAY' and entry.get('activity_name') in ['History Center', 'Disc Golf']:
            tuesday_hc_dg_slots.add(entry.get('slot'))
    
    hc_dg_full = len(tuesday_hc_dg_slots) >= 3  # All 3 Tuesday slots are HC/DG
    
    for troop in troops:
        troop_name = troop.get('name', '')
        preferences = troop.get('preferences', [])
        troop_scheduled = scheduled.get(troop_name, set())
        
        # Check for Reflection
        has_reflection = 'Reflection' in troop_scheduled
        
        # Find missing Top 5
        missing_top5 = []
        for i, pref in enumerate(preferences[:5]):  # Top 5
            if pref not in troop_scheduled:
                # Check exemption logic
                is_exempt = False
                
                # 3-hour activity exemption
                three_hour_activities = {"Tamarac Wildlife Refuge", "Itasca State Park", "Back of the Moon"}
                if pref in three_hour_activities:
                    # Check if troop already has a 3-hour activity
                    has_three_hour = bool(troop_scheduled & three_hour_activities)
                    if has_three_hour:
                        is_exempt = True
                
                # HC/DG exemption
                elif pref in ['History Center', 'Disc Golf'] and hc_dg_full:
                    is_exempt = True
                
                missing_top5.append({
                    'name': pref,
                    'rank': i + 1,
                    'is_exempt': is_exempt
                })
        
        # Find missing Top 10
        missing_top10 = []
        for i, pref in enumerate(preferences[5:10], 6):  # Top 6-10
            if pref not in troop_scheduled:
                missing_top10.append({
                    'name': pref,
                    'rank': i,
                    'is_exempt': False
                })
        
        # Only add to unscheduled if there are missing activities
        if missing_top5 or missing_top10:
            unscheduled_data[troop_name] = {
                'top5': missing_top5,
                'top10': missing_top10,
                'has_reflection': has_reflection
            }
        else:
            unscheduled_data[troop_name] = {
                'top5': [],
                'top10': [],
                'has_reflection': has_reflection
            }
    
    return unscheduled_data


def check_reflection_compliance(troops, entries):
    """Check if all troops have Reflection scheduled."""
    scheduled = defaultdict(set)
    for entry in entries:
        troop = entry.get('troop_name', '')
        activity = entry.get('activity_name', '')
        if troop and activity:
            scheduled[troop].add(activity)
    
    missing_reflection = []
    for troop in troops:
        troop_name = troop.get('name', '')
        if 'Reflection' not in scheduled.get(troop_name, set()):
            missing_reflection.append(troop_name)
    
    return missing_reflection


def fix_schedule_file(schedule_path):
    """Fix a single schedule file with proper unscheduled data."""
    print(f"Fixing {schedule_path.name}...")
    
    with open(schedule_path, 'r') as f:
        data = json.load(f)
    
    troops = data.get('troops', [])
    entries = data.get('entries', [])
    
    # Check Reflection compliance
    missing_reflection = check_reflection_compliance(troops, entries)
    if missing_reflection:
        print(f"  WARNING: {len(missing_reflection)} troops missing Reflection: {missing_reflection}")
    
    # Calculate proper unscheduled data
    unscheduled_data = calculate_unscheduled_data(troops, entries)
    
    # Update the data
    data['unscheduled'] = unscheduled_data
    
    # Save back
    with open(schedule_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    # Report results
    total_top5_missed = sum(len(troop_data.get('top5', [])) for troop_data in unscheduled_data.values())
    troops_with_misses = len([t for t in unscheduled_data.values() if t.get('top5')])
    
    print(f"  Total troops: {len(troops)}")
    print(f"  Total entries: {len(entries)}")
    print(f"  Troops missing Reflection: {len(missing_reflection)}")
    print(f"  Troops with Top 5 misses: {troops_with_misses}")
    print(f"  Total Top 5 misses: {total_top5_missed}")
    
    return {
        'file_name': schedule_path.name,
        'troops': len(troops),
        'entries': len(entries),
        'missing_reflection': len(missing_reflection),
        'top5_misses': total_top5_missed,
        'troops_with_misses': troops_with_misses
    }


def fix_all_schedule_files():
    """Fix all schedule files in the schedules directory."""
    schedules_dir = Path("schedules")
    if not schedules_dir.exists():
        print("No schedules directory found!")
        return
    
    schedule_files = list(schedules_dir.glob("*_schedule.json"))
    
    print(f"Found {len(schedule_files)} schedule files to fix...")
    print("=" * 60)
    
    total_stats = {
        'files_processed': 0,
        'total_troops': 0,
        'total_entries': 0,
        'total_missing_reflection': 0,
        'total_top5_misses': 0,
        'total_troops_with_misses': 0
    }
    
    for schedule_file in schedule_files:
        try:
            stats = fix_schedule_file(schedule_file)
            total_stats['files_processed'] += 1
            total_stats['total_troops'] += stats['troops']
            total_stats['total_entries'] += stats['entries']
            total_stats['total_missing_reflection'] += stats['missing_reflection']
            total_stats['total_top5_misses'] += stats['top5_misses']
            total_stats['total_troops_with_misses'] += stats['troops_with_misses']
            print()
        except Exception as e:
            print(f"  ERROR processing {schedule_file.name}: {e}")
            print()
    
    # Summary
    print("=" * 60)
    print("FIX SUMMARY")
    print("=" * 60)
    print(f"Files processed: {total_stats['files_processed']}")
    print(f"Total troops: {total_stats['total_troops']}")
    print(f"Total entries: {total_stats['total_entries']}")
    print(f"Total troops missing Reflection: {total_stats['total_missing_reflection']}")
    print(f"Total Top 5 misses: {total_stats['total_top5_misses']}")
    print(f"Total troops with Top 5 misses: {total_stats['total_troops_with_misses']}")
    
    if total_stats['total_top5_misses'] > 0:
        success_rate = 100.0 * (total_stats['total_troops'] * 5 - total_stats['total_top5_misses']) / (total_stats['total_troops'] * 5)
        print(f"Overall Top 5 success rate: {success_rate:.1f}%")
    
    print()
    
    # Recommendations
    if total_stats['total_missing_reflection'] > 0:
        print("RECOMMENDATIONS:")
        print("1. Some troops are missing Reflection - check scheduler logic")
        print("2. Reflection should be scheduled in Phase A.0 (first priority)")
        print("3. Review _schedule_friday_reflection() method")
    
    if total_stats['total_top5_misses'] > 0:
        print("4. Top 5 misses detected - regression checker will now work properly")
        print("5. Run regression_checker.py to establish baseline")
    
    return total_stats


def create_reflection_fix_patch():
    """Create a patch for the Reflection scheduling issue."""
    patch_content = '''
# PATCH: Improve Friday Reflection Scheduling
# Add to constrained_scheduler.py in _schedule_friday_reflection method

def _schedule_friday_reflection(self):
    """Ensure ALL troops get Reflection on Friday with enhanced error handling."""
    print("\\n--- Scheduling Friday Reflection for ALL troops (ENHANCED) ---")
    reflection = get_activity_by_name("Reflection")
    if not reflection:
        print("  ERROR: Reflection activity not found!")
        return False
    
    friday_slots = [s for s in self.time_slots if s.day == Day.FRIDAY]
    if not friday_slots:
        print("  ERROR: No Friday slots found!")
        return False
    
    success_count = 0
    force_count = 0
    
    for troop in self.troops:
        scheduled = False
        
        # Try each Friday slot in order
        for slot in friday_slots:
            if self.schedule.is_troop_free(slot, troop):
                self.schedule.add_entry(slot, reflection, troop)
                print(f"  {troop.name}: Reflection -> {slot}")
                success_count += 1
                scheduled = True
                break
        
        # Force schedule if all slots are busy
        if not scheduled:
            force_slot = friday_slots[-1]  # Use last slot
            self.schedule.add_entry(force_slot, reflection, troop)
            print(f"  [FORCE] {troop.name}: Reflection -> {force_slot} (Overbooked)")
            force_count += 1
    
    print(f"Reflection scheduling complete: {success_count} normal, {force_count} forced")
    return True
'''
    
    with open("reflection_fix_patch.py", 'w') as f:
        f.write(patch_content)
    
    print("Created reflection_fix_patch.py with enhanced Reflection scheduling")


def main():
    """Main function to fix all scheduler issues."""
    print("SCHEDULER ISSUES FIX")
    print("=" * 60)
    print("This script will:")
    print("1. Fix unscheduled data not being populated in JSON files")
    print("2. Check Reflection compliance for all troops")
    print("3. Update all schedule files with proper unscheduled data")
    print()
    
    # Change to script directory
    script_dir = Path(__file__).resolve().parent
    os.chdir(script_dir)
    
    # Fix all schedule files
    stats = fix_all_schedule_files()
    
    # Create reflection fix patch if needed
    if stats['total_missing_reflection'] > 0:
        print()
        print("Creating Reflection fix patch...")
        create_reflection_fix_patch()
    
    print()
    print("NEXT STEPS:")
    print("1. Test the updated schedule files with regression_checker.py")
    print("2. Run: python regression_checker.py --detailed")
    print("3. If Reflection issues persist, apply the reflection_fix_patch.py")
    print("4. Investigate Week 2's 0% Top 5 satisfaction separately")


if __name__ == "__main__":
    main()
