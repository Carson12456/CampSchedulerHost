#!/usr/bin/env python3
"""
Update the web interface schedules with our Top 5 fixes.
Copy the fixed schedules to overwrite the original files that the web interface uses.
"""

import json
from pathlib import Path

def update_web_schedules():
    """
    Copy our Top 5 fixed schedules to overwrite the original web interface files.
    """
    print("UPDATING WEB INTERFACE SCHEDULES WITH TOP 5 FIXES")
    print("=" * 55)
    
    # Map of our fixed files to the web interface files
    schedule_mapping = {
        'tc_week1_top5_fixed_schedule.json': 'tc_week1_troops_schedule.json',
        'tc_week2_top5_fixed_schedule.json': 'tc_week2_troops_schedule.json', 
        'tc_week3_top5_fixed_schedule.json': 'tc_week3_troops_schedule.json',
        'tc_week4_top5_fixed_schedule.json': 'tc_week4_troops_schedule.json',
        'tc_week5_top5_fixed_schedule.json': 'tc_week5_troops_schedule.json',
        'tc_week6_top5_fixed_schedule.json': 'tc_week6_troops_schedule.json',
        'tc_week7_top5_fixed_schedule.json': 'tc_week7_troops_schedule.json',
        'tc_week8_top5_fixed_schedule.json': 'tc_week8_troops_schedule.json',
        'voyageur_week1_top5_fixed_schedule.json': 'voyageur_week1_troops_schedule.json',
        'voyageur_week3_top5_fixed_schedule.json': 'voyageur_week3_troops_schedule.json'
    }
    
    schedules_dir = Path("schedules")
    updated_count = 0
    
    for fixed_file, web_file in schedule_mapping.items():
        fixed_path = schedules_dir / fixed_file
        web_path = schedules_dir / web_file
        
        if fixed_path.exists():
            print(f"\nUpdating {web_file}...")
            
            # Load the fixed schedule
            with open(fixed_path) as f:
                fixed_data = json.load(f)
            
            # Backup the original web file
            if web_path.exists():
                backup_path = web_path.with_suffix('.json.backup')
                with open(web_path) as f:
                    original_data = json.load(f)
                with open(backup_path, 'w') as f:
                    json.dump(original_data, f, indent=2)
                print(f"  Backed up original to {backup_path.name}")
            
            # Copy the fixed data to the web file
            with open(web_path, 'w') as f:
                json.dump(fixed_data, f, indent=2)
            
            print(f"  Updated {web_file} with Top 5 fixes")
            updated_count += 1
        else:
            print(f"\nWARNING: {fixed_file} not found - skipping")
    
    print(f"\n" + "=" * 55)
    print(f"UPDATE COMPLETE: {updated_count} schedules updated")
    print("=" * 55)
    
    # Verify the updates
    print("\nVERIFYING UPDATES:")
    for fixed_file, web_file in schedule_mapping.items():
        web_path = schedules_dir / web_file
        if web_path.exists():
            with open(web_path) as f:
                data = json.load(f)
            
            # Count entries
            entries_count = len(data.get('entries', []))
            print(f"  {web_file}: {entries_count} entries")
    
    return updated_count

def analyze_web_schedule_improvements():
    """
    Analyze the improvements in the web schedules after update.
    """
    print(f"\n" + "=" * 55)
    print("ANALYZING WEB SCHEDULE IMPROVEMENTS")
    print("=" * 55)
    
    # Load troop data to check Top 5 satisfaction
    troop_files = list(Path(".").glob("*_troops.json"))
    
    total_before = 0
    total_after = 0
    total_at_before = 0
    total_at_after = 0
    
    for troops_file in sorted(troop_files):
        week_name = troops_file.stem.replace('_troops', '')
        schedule_file = Path(f"schedules/{week_name}_troops_schedule.json")
        
        if not schedule_file.exists():
            continue
        
        try:
            # Load troop data
            with open(troops_file) as f:
                troops_data = json.load(f)['troops']
            
            # Load updated schedule
            with open(schedule_file) as f:
                schedule_data = json.load(f)
            
            # Analyze Top 5 satisfaction
            troop_activities = {}
            for entry in schedule_data.get('entries', []):
                troop_activities[entry['troop']] = troop_activities.get(entry['troop'], []) + [entry['activity']]
            
            week_before = 0
            week_after = 0
            week_at_before = 0
            week_at_after = 0
            
            for troop in troops_data:
                troop_name = troop['name']
                activities = troop_activities.get(troop_name, [])
                
                # Check Top 5 preferences
                top5 = troop['preferences'][:5] if len(troop['preferences']) >= 5 else troop['preferences']
                
                for pref in top5:
                    if pref == "Aqua Trampoline":
                        week_at_before += 1
                        if pref in activities:
                            week_at_after += 1
                    else:
                        week_before += 1
                        if pref in activities:
                            week_after += 1
            
            total_before += week_before
            total_after += week_after
            total_at_before += week_at_before
            total_at_after += week_at_after
            
            improvement = week_before - week_after
            at_improvement = week_at_before - week_at_after
            
            if improvement > 0 or at_improvement > 0:
                print(f"  {week_name}: {improvement} total improvements, {at_improvement} AT improvements")
        
        except Exception as e:
            print(f"  {week_name}: ERROR - {e}")
    
    overall_improvement = total_before - total_after
    at_improvement = total_at_before - total_at_after
    
    print(f"\nOVERALL IMPROVEMENTS:")
    print(f"  Total Top 5 improvements: {overall_improvement}")
    print(f"  Aqua Trampoline improvements: {at_improvement}")
    
    if total_before > 0:
        improvement_rate = (overall_improvement / total_before) * 100
        print(f"  Improvement rate: {improvement_rate:.1f}%")
    
    return overall_improvement, at_improvement

if __name__ == "__main__":
    updated_count = update_web_schedules()
    if updated_count > 0:
        analyze_web_schedule_improvements()
    else:
        print("No schedules were updated. Please run apply_fixes_all_weeks.py first.")
