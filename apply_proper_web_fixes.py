#!/usr/bin/env python3
"""
Apply Top 5 fixes to web schedules while maintaining proper format.
"""

import json
from pathlib import Path
from collections import defaultdict

def apply_proper_web_fixes():
    """
    Apply Top 5 fixes while maintaining the proper web interface format.
    """
    print("APPLYING PROPER WEB FIXES")
    print("=" * 30)
    
    # Get all troop files
    troop_files = list(Path(".").glob("*_troops.json"))
    
    fixed_count = 0
    
    for troops_file in sorted(troop_files):
        week_name = troops_file.stem.replace('_troops', '')
        schedule_file = Path(f"schedules/{week_name}_troops_schedule.json")
        fixed_file = Path(f"schedules/{week_name}_top5_fixed_schedule.json")
        
        if not schedule_file.exists():
            continue
        
        try:
            # Load original schedule (has proper format)
            with open(schedule_file) as f:
                original_data = json.load(f)
            
            # Load our fixed schedule (has the fixes)
            if fixed_file.exists():
                with open(fixed_file) as f:
                    fixed_data = json.load(f)
                
                # Merge: keep original format, but use fixed entries
                merged_data = {
                    'troops': original_data['troops'],
                    'entries': fixed_data['entries']
                }
                
                # Backup original
                backup_file = schedule_file.with_suffix('.json.backup2')
                with open(backup_file, 'w') as f:
                    json.dump(original_data, f, indent=2)
                
                # Write merged data
                with open(schedule_file, 'w') as f:
                    json.dump(merged_data, f, indent=2)
                
                print(f"  {week_name}: Applied fixes with proper format")
                fixed_count += 1
            else:
                print(f"  {week_name}: No fixed file found")
        
        except Exception as e:
            print(f"  {week_name}: ERROR - {e}")
    
    print(f"\nApplied fixes to {fixed_count} schedules")
    return fixed_count

def verify_web_format():
    """
    Verify the web interface format is correct.
    """
    print(f"\nVERIFYING WEB FORMAT")
    print("=" * 20)
    
    schedule_file = Path("schedules/tc_week4_troops_schedule.json")
    
    if schedule_file.exists():
        with open(schedule_file) as f:
            data = json.load(f)
        
        print(f"Has 'troops' section: {'troops' in data}")
        print(f"Has 'entries' section: {'entries' in data}")
        print(f"Troops count: {len(data.get('troops', []))}")
        print(f"Entries count: {len(data.get('entries', []))}")
        
        # Check a sample entry
        entries = data.get('entries', [])
        if entries:
            print(f"Sample entry: {entries[0]}")
        
        # Check a sample troop
        troops = data.get('troops', [])
        if troops:
            troop = troops[0]
            print(f"Sample troop: {troop['name']} (Top 5: {troop['preferences'][:5]})")
    
    print("\nWeb interface should now work properly!")

if __name__ == "__main__":
    fixed = apply_proper_web_fixes()
    if fixed > 0:
        verify_web_format()
