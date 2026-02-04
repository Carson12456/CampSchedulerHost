#!/usr/bin/env python3
"""
Generate schedules with guaranteed 100% reflection compliance
"""

import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from constrained_scheduler import ConstrainedScheduler
from io_handler import load_troops_from_json, save_schedule_to_json
from activities import get_all_activities


def generate_schedule_with_reflection_fix(week_file):
    """Generate a schedule with guaranteed reflection compliance."""
    print(f"Processing {week_file}...")
    
    try:
        # Load troops
        troops = load_troops_from_json(week_file)
        activities = get_all_activities()
        
        # Create scheduler
        scheduler = ConstrainedScheduler(troops, activities)
        
        # Run scheduling (this will use our fixed reflection method)
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
        schedule_file = Path(f"schedules/{Path(week_file).stem}_reflection_fixed_schedule.json")
        save_schedule_to_json(schedule, troops, str(schedule_file), unscheduled_data)
        
        # Count results
        reflection_count = sum(1 for data in unscheduled_data.values() if data.get('has_reflection', False))
        top5_misses = sum(len(data.get('top5', [])) for data in unscheduled_data.values())
        
        print(f"  SUCCESS: {len(troops)} troops, {len(schedule.entries)} entries")
        print(f"  Reflection: {reflection_count}/{len(troops)} ({100.0*reflection_count/len(troops):.1f}%)")
        print(f"  Top 5 misses: {top5_misses}")
        print(f"  Saved to: {schedule_file}")
        
        return {
            'week': week_file,
            'troops': len(troops),
            'entries': len(schedule.entries),
            'reflection': reflection_count,
            'top5_misses': top5_misses,
            'success': True
        }
        
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
        return {
            'week': week_file,
            'error': str(e),
            'success': False
        }


def main():
    """Main function."""
    print("GENERATING SCHEDULES WITH GUARANTEED REFLECTION COMPLIANCE")
    print("=" * 70)
    print()
    
    # Change to script directory
    script_dir = Path(__file__).resolve().parent
    os.chdir(script_dir)
    
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
        
        result = generate_schedule_with_reflection_fix(week_file)
        results.append(result)
        print()
    
    # Summary
    print("=" * 70)
    print("GENERATION SUMMARY")
    print("=" * 70)
    
    successful = [r for r in results if r.get('success', False)]
    failed = [r for r in results if not r.get('success', False)]
    
    if successful:
        total_troops = sum(r['troops'] for r in successful)
        total_reflection = sum(r['reflection'] for r in successful)
        total_top5_misses = sum(r['top5_misses'] for r in successful)
        
        print(f"Successfully generated: {len(successful)}/{len(results)} schedules")
        print(f"Total troops: {total_troops}")
        print(f"Total Reflection compliance: {total_reflection}/{total_troops} ({100.0*total_reflection/total_troops:.1f}%)")
        print(f"Total Top 5 misses: {total_top5_misses}")
        
        if total_reflection == total_troops:
            print("\n🎉 SUCCESS: 100% Reflection compliance achieved!")
        else:
            print(f"\n⚠️  PARTIAL: {total_troops - total_reflection} troops still missing Reflection")
    
    if failed:
        print(f"\n❌ Failed to generate {len(failed)} schedules:")
        for f in failed:
            print(f"  - {f['week']}: {f.get('error', 'Unknown error')}")
    
    return len(failed) == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
