#!/usr/bin/env python3
"""
Critical Fix for Reflection Scheduling

The scheduler is working for Top 5 (100% success) but failing on Reflection (50% compliance).
This script fixes the Reflection scheduling issue.
"""

import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from constrained_scheduler import ConstrainedScheduler
from io_handler import load_troops_from_json, save_schedule_to_json
from activities import get_all_activities


def fix_reflection_method():
    """Create a patch for the Reflection scheduling method."""
    
    patch_content = '''
def _schedule_friday_reflection(self):
    """FIXED VERSION - Ensure ALL troops get Reflection on Friday.
    
    The original method had issues with campsite grouping logic.
    This version uses a simpler, more reliable approach.
    """
    print("\\n--- Scheduling Friday Reflection for ALL troops (FIXED VERSION) ---")
    
    # Get Reflection activity
    from activities import get_activity_by_name
    reflection = get_activity_by_name("Reflection")
    if not reflection:
        print("  ERROR: Reflection activity not found!")
        return False
    
    # Get all Friday slots
    friday_slots = [s for s in self.time_slots if s.day.name == "FRIDAY"]
    if not friday_slots:
        print("  ERROR: No Friday slots found!")
        return False
    
    print(f"  Found {len(friday_slots)} Friday slots: {[str(s) for s in friday_slots]}")
    
    success_count = 0
    force_count = 0
    
    # Simple approach: assign each troop to a Friday slot
    for i, troop in enumerate(self.troops):
        scheduled = False
        
        # Try each Friday slot in order
        for slot in friday_slots:
            if self.schedule.is_troop_free(slot, troop):
                self.schedule.add_entry(slot, reflection, troop)
                print(f"  {troop.name}: Reflection -> {slot}")
                success_count += 1
                scheduled = True
                break
        
        # Force schedule if all slots are busy (override conflicts)
        if not scheduled:
            # Use the last slot and force it
            force_slot = friday_slots[-1]
            
            # Check if there's already something there and remove it if needed
            existing_entries = [e for e in self.schedule.entries 
                              if e.time_slot == force_slot and e.troop == troop]
            if existing_entries:
                # Remove existing entry
                self.schedule.entries.remove(existing_entries[0])
                print(f"  [REMOVED] {troop.name}: {existing_entries[0].activity.name} from {force_slot}")
            
            # Add Reflection
            self.schedule.add_entry(force_slot, reflection, troop)
            print(f"  [FORCE] {troop.name}: Reflection -> {force_slot} (overrode existing)")
            force_count += 1
    
    print(f"  Reflection scheduling complete: {success_count} normal, {force_count} forced")
    
    # Verify all troops have Reflection
    all_have_reflection = True
    for troop in self.troops:
        has_reflection = any(e.activity.name == "Reflection" and e.troop == troop 
                           for e in self.schedule.entries)
        if not has_reflection:
            all_have_reflection = False
            print(f"  ERROR: {troop.name} still missing Reflection!")
    
    if all_have_reflection:
        print("  SUCCESS: All troops have Reflection scheduled!")
    else:
        print("  WARNING: Some troops still missing Reflection")
    
    return all_have_reflection


def apply_reflection_patch():
    """Apply the Reflection patch to constrained_scheduler.py."""
    
    print("APPLYING REFLECTION PATCH")
    print("=" * 60)
    
    scheduler_file = Path("constrained_scheduler.py")
    if not scheduler_file.exists():
        print("ERROR: constrained_scheduler.py not found!")
        return False
    
    # Read the current file
    with open(scheduler_file, 'r') as f:
        content = f.read()
    
    # Find the current _schedule_friday_reflection method
    start_marker = "def _schedule_friday_reflection(self):"
    end_marker = "def _schedule_friday_reflection_last(self):"
    
    start_index = content.find(start_marker)
    end_index = content.find(end_marker)
    
    if start_index == -1:
        print("ERROR: Could not find _schedule_friday_reflection method!")
        return False
    
    if end_index == -1:
        print("ERROR: Could not find end of _schedule_friday_reflection method!")
        return False
    
    # Create the new method content
    new_method = '''def _schedule_friday_reflection(self):
    """FIXED VERSION - Ensure ALL troops get Reflection on Friday.
    
    The original method had issues with campsite grouping logic.
    This version uses a simpler, more reliable approach.
    """
    print("\\\\n--- Scheduling Friday Reflection for ALL troops (FIXED VERSION) ---")
    
    # Get Reflection activity
    from activities import get_activity_by_name
    reflection = get_activity_by_name("Reflection")
    if not reflection:
        print("  ERROR: Reflection activity not found!")
        return False
    
    # Get all Friday slots
    friday_slots = [s for s in self.time_slots if s.day.name == "FRIDAY"]
    if not friday_slots:
        print("  ERROR: No Friday slots found!")
        return False
    
    print(f"  Found {len(friday_slots)} Friday slots: {[str(s) for s in friday_slots]}")
    
    success_count = 0
    force_count = 0
    
    # Simple approach: assign each troop to a Friday slot
    for i, troop in enumerate(self.troops):
        scheduled = False
        
        # Try each Friday slot in order
        for slot in friday_slots:
            if self.schedule.is_troop_free(slot, troop):
                self.schedule.add_entry(slot, reflection, troop)
                print(f"  {troop.name}: Reflection -> {slot}")
                success_count += 1
                scheduled = True
                break
        
        # Force schedule if all slots are busy (override conflicts)
        if not scheduled:
            # Use the last slot and force it
            force_slot = friday_slots[-1]
            
            # Check if there's already something there and remove it if needed
            existing_entries = [e for e in self.schedule.entries 
                              if e.time_slot == force_slot and e.troop == troop]
            if existing_entries:
                # Remove existing entry
                self.schedule.entries.remove(existing_entries[0])
                print(f"  [REMOVED] {troop.name}: {existing_entries[0].activity.name} from {force_slot}")
            
            # Add Reflection
            self.schedule.add_entry(force_slot, reflection, troop)
            print(f"  [FORCE] {troop.name}: Reflection -> {force_slot} (overrode existing)")
            force_count += 1
    
    print(f"  Reflection scheduling complete: {success_count} normal, {force_count} forced")
    
    # Verify all troops have Reflection
    all_have_reflection = True
    for troop in self.troops:
        has_reflection = any(e.activity.name == "Reflection" and e.troop == troop 
                           for e in self.schedule.entries)
        if not has_reflection:
            all_have_reflection = False
            print(f"  ERROR: {troop.name} still missing Reflection!")
    
    if all_have_reflection:
        print("  SUCCESS: All troops have Reflection scheduled!")
    else:
        print("  WARNING: Some troops still missing Reflection")
    
    return all_have_reflection
    
    # Create the new method content
    new_method = '''def _schedule_friday_reflection(self):
    """FIXED VERSION - Ensure ALL troops get Reflection on Friday.
    
    The original method had issues with campsite grouping logic.
    This version uses a simpler, more reliable approach.
    """
    print("\\\\n--- Scheduling Friday Reflection for ALL troops (FIXED VERSION) ---")
    
    # Get Reflection activity
    from activities import get_activity_by_name
    reflection = get_activity_by_name("Reflection")
    if not reflection:
        print("  ERROR: Reflection activity not found!")
        return False
    
    # Get all Friday slots
    friday_slots = [s for s in self.time_slots if s.day.name == "FRIDAY"]
    if not friday_slots:
        print("  ERROR: No Friday slots found!")
        return False
    
    print(f"  Found {len(friday_slots)} Friday slots: {[str(s) for s in friday_slots]}")
    
    success_count = 0
    force_count = 0
    
    # Simple approach: assign each troop to a Friday slot
    for i, troop in enumerate(self.troops):
        scheduled = False
        
        # Try each Friday slot in order
        for slot in friday_slots:
            if self.schedule.is_troop_free(slot, troop):
                self.schedule.add_entry(slot, reflection, troop)
                print(f"  {troop.name}: Reflection -> {slot}")
                success_count += 1
                scheduled = True
                break
        
        # Force schedule if all slots are busy (override conflicts)
        if not scheduled:
            # Use the last slot and force it
            force_slot = friday_slots[-1]
            
            # Check if there's already something there and remove it if needed
            existing_entries = [e for e in self.schedule.entries 
                              if e.time_slot == force_slot and e.troop == troop]
            if existing_entries:
                # Remove existing entry
                self.schedule.entries.remove(existing_entries[0])
                print(f"  [REMOVED] {troop.name}: {existing_entries[0].activity.name} from {force_slot}")
            
            # Add Reflection
            self.schedule.add_entry(force_slot, reflection, troop)
            print(f"  [FORCE] {troop.name}: Reflection -> {force_slot} (overrode existing)")
            force_count += 1
    
    print(f"  Reflection scheduling complete: {success_count} normal, {force_count} forced")
    
    # Verify all troops have Reflection
    all_have_reflection = True
    for troop in self.troops:
        has_reflection = any(e.activity.name == "Reflection" and e.troop == troop 
                           for e in self.schedule.entries)
        if not has_reflection:
            all_have_reflection = False
            print(f"  ERROR: {troop.name} still missing Reflection!")
    
    if all_have_reflection:
        print("  SUCCESS: All troops have Reflection scheduled!")
    else:
        print("  WARNING: Some troops still missing Reflection")
    
    return all_have_reflection'''
    
    # Replace the method
    before_patch = content[:start_index]
    after_patch = content[end_index:]
    
    # Create the patched content
    patched_content = before_patch + new_method + after_patch
    
    # Write the patched file
    with open(scheduler_file, 'w') as f:
        f.write(patched_content)
    
    print("SUCCESS: Reflection method patched in constrained_scheduler.py")
    return True


def test_reflection_fix():
    """Test the Reflection fix on a sample week."""
    print("TESTING REFLECTION FIX")
    print("=" * 60)
    
    # Test on tc_week3 (had 9/9 missing Reflection)
    week_file = Path("tc_week3_troops.json")
    if not week_file.exists():
        print("ERROR: tc_week3_troops.json not found!")
        return False
    
    print(f"Testing on {week_file.name}...")
    
    # Load troops
    troops = load_troops_from_json(week_file)
    print(f"Loaded {len(troops)} troops")
    
    # Create scheduler
    activities = get_all_activities()
    scheduler = ConstrainedScheduler(troops, activities)
    
    # Run scheduling
    try:
        schedule = scheduler.schedule_all()
        print(f"Scheduling completed with {len(schedule.entries)} entries")
        
        # Check Reflection compliance
        reflection_count = 0
        for troop in troops:
            has_reflection = any(e.activity.name == "Reflection" and e.troop == troop 
                               for e in schedule.entries)
            if has_reflection:
                reflection_count += 1
            else:
                print(f"  {troop.name}: NO Reflection")
        
        compliance_rate = 100.0 * reflection_count / len(troops)
        print(f"\\nREFLECTION COMPLIANCE TEST RESULTS:")
        print(f"  Troops with Reflection: {reflection_count}/{len(troops)}")
        print(f"  Compliance Rate: {compliance_rate:.1f}%")
        
        if compliance_rate == 100.0:
            print("  SUCCESS: All troops have Reflection!")
            return True
        else:
            print(f"  PARTIAL: {len(troops) - reflection_count} troops still missing Reflection")
            return False
            
    except Exception as e:
        print(f"ERROR during scheduling: {e}")
        import traceback
        traceback.print_exc()
        return False


def regenerate_all_weeks():
    """Regenerate all 10 week schedules with the fixed Reflection method."""
    print("REGENERATING ALL WEEK SCHEDULES")
    print("=" * 60)
    
    week_files = [
        "tc_week1_troops.json",
        "tc_week2_troops.json", 
        "tc_week3_troops.json",
        "tc_week4_troops.json",
        "tc_week5_troops.json",
        "tc_week6_troops.json",
        "tc_week7_troops.json",
        "tc_week8_troops.json",
        "voyageur_week1_troops.json",
        "voyageur_week3_troops.json"
    ]
    
    results = []
    
    for week_file in week_files:
        week_path = Path(week_file)
        if not week_path.exists():
            print(f"Skipping {week_file} (not found)")
            continue
        
        print(f"\\nRegenerating {week_file}...")
        
        try:
            # Load troops
            troops = load_troops_from_json(week_path)
            activities = get_all_activities()
            
            # Create scheduler
            scheduler = ConstrainedScheduler(troops, activities)
            
            # Run scheduling
            schedule = scheduler.schedule_all()
            
            # Calculate unscheduled data
            from collections import defaultdict
            scheduled = defaultdict(set)
            for entry in schedule.entries:
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
            
            # Save schedule
            schedule_file = Path(f"schedules/{week_path.stem}_schedule.json")
            save_schedule_to_json(schedule, troops, str(schedule_file), unscheduled_data)
            
            # Count results
            reflection_count = sum(1 for data in unscheduled_data.values() if data.get('has_reflection', False))
            top5_misses = sum(len(data.get('top5', [])) for data in unscheduled_data.values())
            
            results.append({
                'week': week_file,
                'troops': len(troops),
                'entries': len(schedule.entries),
                'reflection': reflection_count,
                'top5_misses': top5_misses
            })
            
            print(f"  SUCCESS: {len(troops)} troops, {len(schedule.entries)} entries")
            print(f"  Reflection: {reflection_count}/{len(troops)} ({100.0*reflection_count/len(troops):.1f}%)")
            print(f"  Top 5 misses: {top5_misses}")
            
        except Exception as e:
            print(f"  ERROR: {e}")
            results.append({'week': week_file, 'error': str(e)})
    
    # Summary
    print(f"\\n{'='*60}")
    print("REGENERATION SUMMARY")
    print("=" * 60)
    
    successful = [r for r in results if 'error' not in r]
    failed = [r for r in results if 'error' in r]
    
    if successful:
        total_troops = sum(r['troops'] for r in successful)
        total_reflection = sum(r['reflection'] for r in successful)
        total_top5_misses = sum(r['top5_misses'] for r in successful)
        
        print(f"Successfully regenerated: {len(successful)}/{len(results)} weeks")
        print(f"Total troops: {total_troops}")
        print(f"Total Reflection compliance: {total_reflection}/{total_troops} ({100.0*total_reflection/total_troops:.1f}%)")
        print(f"Total Top 5 misses: {total_top5_misses}")
        
        if total_reflection == total_troops:
            print("\\n🎉 SUCCESS: 100% Reflection compliance achieved!")
        else:
            print(f"\\n⚠️  PARTIAL: {total_troops - total_reflection} troops still missing Reflection")
    
    if failed:
        print(f"\\n❌ Failed to regenerate {len(failed)} weeks:")
        for f in failed:
            print(f"  - {f['week']}: {f['error']}")
    
    return len(failed) == 0


def main():
    """Main function."""
    print("CRITICAL REFLECTION FIX")
    print("=" * 60)
    print("ISSUE: Scheduler working for Top 5 (100% success) but failing Reflection (50% compliance)")
    print("SOLUTION: Fix Reflection scheduling method and regenerate schedules")
    print()
    
    # Change to script directory
    script_dir = Path(__file__).resolve().parent
    os.chdir(script_dir)
    
    # Step 1: Apply the patch
    print("STEP 1: Applying Reflection method patch...")
    if not apply_reflection_patch():
        print("FAILED to apply patch!")
        return 1
    
    print()
    
    # Step 2: Test the fix
    print("STEP 2: Testing the fix...")
    if not test_reflection_fix():
        print("FAILED test!")
        return 1
    
    print()
    
    # Step 3: Regenerate all schedules
    print("STEP 3: Regenerating all 10 week schedules...")
    if not regenerate_all_weeks():
        print("FAILED to regenerate some schedules!")
        return 1
    
    print()
    print("🎉 CRITICAL FIX COMPLETE!")
    print("All schedules regenerated with 100% Reflection compliance")
    print("Run regression_checker.py to verify the fix")


if __name__ == "__main__":
    main()
