#!/usr/bin/env python3
"""
Debug Scheduler Failure - Find why Top 5 is 0% and Reflection is 100% missing
"""

import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from constrained_scheduler import ConstrainedScheduler
from io_handler import load_troops_from_json, save_schedule_to_json
from activities import get_all_activities


def debug_single_week(week_file):
    """Debug a single week to see what's happening."""
    print(f"DEBUGGING {week_file.name}")
    print("=" * 60)
    
    # Load troops
    troops = load_troops_from_json(week_file)
    print(f"Loaded {len(troops)} troops")
    
    # Show troop preferences
    for i, troop in enumerate(troops[:3]):  # First 3 troops
        print(f"\nTroop {i+1}: {troop.name}")
        print(f"  Preferences: {troop.preferences[:5]}")  # Top 5
        print(f"  Scouts: {troop.scouts}, Adults: {troop.adults}")
    
    # Create scheduler
    activities = get_all_activities()
    scheduler = ConstrainedScheduler(troops, activities)
    
    print(f"\nStarting scheduler with {len(activities)} activities...")
    
    # Run scheduling
    try:
        schedule = scheduler.schedule_all()
        print(f"\nScheduling completed!")
        print(f"Total entries: {len(schedule.entries)}")
        
        # Analyze results
        from collections import defaultdict
        scheduled = defaultdict(set)
        for entry in schedule.entries:
            scheduled[entry.troop.name].add(entry.activity.name)
        
        print(f"\nSCHEDULING RESULTS:")
        print("=" * 40)
        
        total_top5 = 0
        satisfied_top5 = 0
        missing_reflection = 0
        
        for troop in troops:
            troop_name = troop.name
            preferences = troop.preferences[:5]  # Top 5
            troop_scheduled = scheduled.get(troop_name, set())
            
            # Check Reflection
            has_reflection = 'Reflection' in troop_scheduled
            if not has_reflection:
                missing_reflection += 1
            
            # Check Top 5
            troop_satisfied = 0
            for pref in preferences:
                if pref in troop_scheduled:
                    troop_satisfied += 1
                    satisfied_top5 += 1
                else:
                    print(f"  {troop_name} MISSED: {pref}")
            
            total_top5 += len(preferences)
            
            print(f"{troop_name}: {troop_satisfied}/{len(preferences)} Top 5, Reflection: {'YES' if has_reflection else 'NO'}")
        
        success_rate = 100.0 * satisfied_top5 / max(1, total_top5)
        print(f"\nSUMMARY:")
        print(f"Top 5 Success: {satisfied_top5}/{total_top5} ({success_rate:.1f}%)")
        print(f"Reflection Compliance: {len(troops) - missing_reflection}/{len(troops)} ({100.0*(len(troops)-missing_reflection)/len(troops):.1f}%)")
        
        # Check for specific issues
        if success_rate == 0:
            print(f"\n🚨 CRITICAL: 0% Top 5 success detected!")
            print("Possible causes:")
            print("1. Activities not found in activity definitions")
            print("2. Constraint validation too strict")
            print("3. Scheduler logic error")
            
            # Check if activities exist
            print(f"\nCHECKING ACTIVITY DEFINITIONS:")
            missing_activities = set()
            for troop in troops:
                for pref in troop.preferences[:5]:
                    found = False
                    for activity in activities:
                        if activity.name == pref:
                            found = True
                            break
                    if not found:
                        missing_activities.add(pref)
            
            if missing_activities:
                print(f"Missing activities: {missing_activities}")
            else:
                print("All Top 5 activities found in definitions")
        
        if missing_reflection == len(troops):
            print(f"\n🚨 CRITICAL: 100% Reflection failure detected!")
            print("Checking Reflection activity...")
            
            reflection_found = False
            for activity in activities:
                if activity.name == "Reflection":
                    reflection_found = True
                    print(f"Reflection activity found: {activity}")
                    break
            
            if not reflection_found:
                print("ERROR: Reflection activity not found in definitions!")
            else:
                print("Reflection activity exists - scheduling logic issue")
        
        return {
            'success_rate': success_rate,
            'reflection_compliance': len(troops) - missing_reflection,
            'total_troops': len(troops),
            'total_entries': len(schedule.entries),
            'missing_activities': missing_activities if 'missing_activities' in locals() else set()
        }
        
    except Exception as e:
        print(f"ERROR during scheduling: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Main debug function."""
    print("SCHEDULER FAILURE DEBUG")
    print("=" * 60)
    
    # Change to script directory
    script_dir = Path(__file__).resolve().parent
    os.chdir(script_dir)
    
    # Test a simple week first
    week_files = [
        Path("tc_week1_troops.json"),
        Path("tc_week2_troops.json"),
        Path("tc_week3_troops.json")
    ]
    
    results = []
    
    for week_file in week_files:
        if week_file.exists():
            print(f"\n{'='*80}\n")
            result = debug_single_week(week_file)
            if result:
                results.append(result)
        else:
            print(f"File not found: {week_file}")
    
    # Summary
    if results:
        print(f"\n{'='*80}\n")
        print("DEBUG SUMMARY:")
        print("=" * 60)
        
        for result in results:
            print(f"Week: Success={result['success_rate']:.1f}%, Reflection={result['reflection_compliance']}/{result['total_troops']}")
            
        avg_success = sum(r['success_rate'] for r in results) / len(results)
        avg_reflection = sum(r['reflection_compliance'] for r in results) / sum(r['total_troops'] for r in results) * 100
        
        print(f"\nAVERAGE:")
        print(f"Top 5 Success: {avg_success:.1f}%")
        print(f"Reflection Compliance: {avg_reflection:.1f}%")
        
        if avg_success < 10:
            print(f"\n🚨 CONFIRMED: Critical scheduler failure detected!")
            print("Immediate action required.")


if __name__ == "__main__":
    main()
